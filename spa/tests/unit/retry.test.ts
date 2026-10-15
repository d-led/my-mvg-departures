import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { withRetries, type FailedAttempt } from "../../src/utils/retry.js";

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
    const operation = vi.fn().mockRejectedValue(new Error("MVG API error: 500"));

    const retried = withRetries(operation, policy);
    const outcome = expect(retried).rejects.toThrow("MVG API error: 500");

    await vi.advanceTimersByTimeAsync(policy.delayMs * policy.attempts);
    await outcome;

    expect(operation).toHaveBeenCalledTimes(policy.attempts);
  });

  it("pauses between attempts and announces each retry", async () => {
    const operation = vi.fn().mockRejectedValue(new Error("network down"));
    const failedAttempts: FailedAttempt[] = [];

    const retried = withRetries(operation, policy, (failed) =>
      failedAttempts.push(failed),
    );
    const outcome = expect(retried).rejects.toThrow("network down");

    await vi.advanceTimersByTimeAsync(policy.delayMs * policy.attempts);
    await outcome;

    expect(failedAttempts.map((failed) => failed.attempt)).toEqual([1, 2]);
    expect(failedAttempts[0].error.message).toBe("network down");
  });
});
