import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  DEFAULT_RETRY_POLICY,
  retryPolicyFromDisplay,
  withRetries,
  type FailedAttempt,
  type RetryWait,
} from "../../src/utils/retry.js";

describe("retry policy from configuration", () => {
  it("uses the defaults when the config says nothing", () => {
    expect(retryPolicyFromDisplay(undefined)).toEqual(DEFAULT_RETRY_POLICY);
    expect(retryPolicyFromDisplay({})).toEqual(DEFAULT_RETRY_POLICY);
  });

  it("uses the configured attempts and pause", () => {
    expect(
      retryPolicyFromDisplay({
        fetchRetryAttempts: 5,
        fetchRetryDelayMs: 2000,
      }),
    ).toEqual({ attempts: 5, delayMs: 2000 });
  });

  it("keeps a single attempt meaning no retry", () => {
    expect(retryPolicyFromDisplay({ fetchRetryAttempts: 1 })).toEqual({
      attempts: 1,
      delayMs: DEFAULT_RETRY_POLICY.delayMs,
    });
  });

  it("corrects settings that would break the cycle", () => {
    expect(
      retryPolicyFromDisplay({
        fetchRetryAttempts: 0,
        fetchRetryDelayMs: -100,
      }),
    ).toEqual({ attempts: 1, delayMs: 0 });
  });
});

describe("withRetries", () => {
  const policy = { attempts: 3, delayMs: 1000 };

  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("returns the first result without waiting when the operation succeeds", async () => {
    const operation = vi.fn().mockResolvedValue("departures");

    await expect(withRetries(operation, policy)).resolves.toBe("departures");
    expect(operation).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("retries a transient failure until it succeeds", async () => {
    const operation = vi
      .fn()
      .mockRejectedValueOnce(new Error("API error: 503 Service Unavailable"))
      .mockResolvedValue("departures");

    const retried = withRetries(operation, policy);
    await vi.advanceTimersByTimeAsync(policy.delayMs);

    await expect(retried).resolves.toBe("departures");
    expect(operation).toHaveBeenCalledTimes(2);
  });

  it("gives up after the configured number of attempts and reports why", async () => {
    const operation = vi
      .fn()
      .mockRejectedValue(new Error("MVG API error: 500"));

    const retried = withRetries(operation, policy);
    const outcome = expect(retried).rejects.toThrow("MVG API error: 500");

    await vi.advanceTimersByTimeAsync(policy.delayMs * policy.attempts);
    await outcome;

    expect(operation).toHaveBeenCalledTimes(policy.attempts);
  });

  it("pauses between attempts and announces each retry", async () => {
    const operation = vi.fn().mockRejectedValue(new Error("network down"));
    const failedAttempts: FailedAttempt[] = [];

    const retried = withRetries(operation, policy, {
      onFailedAttempt: (failed) => failedAttempts.push(failed),
    });
    const outcome = expect(retried).rejects.toThrow("network down");

    await vi.advanceTimersByTimeAsync(policy.delayMs * policy.attempts);
    await outcome;

    expect(failedAttempts.map((failed) => failed.attempt)).toEqual([1, 2]);
    expect(failedAttempts[0].error.message).toBe("network down");
  });

  it("counts down the pause before each retry", async () => {
    const operation = vi.fn().mockRejectedValue(new Error("network down"));
    const waits: RetryWait[] = [];

    const retried = withRetries(
      operation,
      { attempts: 2, delayMs: 3000 },
      { onRetryWait: (wait) => waits.push(wait) },
    );
    const outcome = expect(retried).rejects.toThrow("network down");

    await vi.advanceTimersByTimeAsync(3000);
    await outcome;

    expect(waits).toEqual([
      { attempt: 1, attempts: 2, remainingMs: 3000 },
      { attempt: 1, attempts: 2, remainingMs: 2000 },
      { attempt: 1, attempts: 2, remainingMs: 1000 },
      { attempt: 1, attempts: 2, remainingMs: 0 },
    ]);
  });

  it("retries right away when the policy has no pause", async () => {
    const operation = vi
      .fn()
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValue("departures");
    const waits: RetryWait[] = [];

    await withRetries(
      operation,
      { attempts: 2, delayMs: 0 },
      { onRetryWait: (wait) => waits.push(wait) },
    );

    expect(waits).toEqual([{ attempt: 1, attempts: 2, remainingMs: 0 }]);
    expect(operation).toHaveBeenCalledTimes(2);
  });
});
