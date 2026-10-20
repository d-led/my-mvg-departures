import { describe, it, expect, vi, afterEach } from "vitest";
import { fetchWithTimeout } from "../../src/utils/http.js";

describe("fetchWithTimeout", () => {
  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("gives up on a connection that never answers", async () => {
    vi.useFakeTimers();
    vi.stubGlobal(
      "fetch",
      vi.fn(
        (_url: string, init: RequestInit) =>
          new Promise<Response>((_resolve, reject) => {
            init.signal?.addEventListener("abort", () =>
              reject(
                new DOMException("The operation was aborted.", "AbortError"),
              ),
            );
          }),
      ),
    );

    const request = fetchWithTimeout(
      "https://example.test/departures",
      {},
      2000,
    );
    const outcome = expect(request).rejects.toThrow(
      "Request timed out after 2 s without an answer",
    );

    await vi.advanceTimersByTimeAsync(2000);
    await outcome;
  });

  it("passes an answer through and leaves no timer behind", async () => {
    vi.useFakeTimers();
    const response = { ok: true } as Response;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => response),
    );

    await expect(fetchWithTimeout("https://example.test")).resolves.toBe(
      response,
    );
    expect(vi.getTimerCount()).toBe(0);
  });

  it("keeps a network error as it is", async () => {
    const networkError = new TypeError("Failed to fetch");
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw networkError;
      }),
    );

    await expect(fetchWithTimeout("https://example.test")).rejects.toBe(
      networkError,
    );
  });
});
