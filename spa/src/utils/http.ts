/**
 * A connection that never answers must not keep a refresh cycle alive forever:
 * without a deadline the cycle can neither report progress nor ever retry.
 */
export const DEFAULT_FETCH_TIMEOUT_MS = 15_000;

/**
 * `fetch` with a deadline. A timed-out request fails with a readable error, so
 * a stalled API shows up as a normal stop failure instead of a silent pause.
 */
export async function fetchWithTimeout(
  url: string,
  init: RequestInit = {},
  timeoutMs: number = DEFAULT_FETCH_TIMEOUT_MS,
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error(
        `Request timed out after ${formatSeconds(timeoutMs)} without an answer`,
        { cause: error },
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function formatSeconds(milliseconds: number): string {
  const seconds = milliseconds / 1000;
  return `${Number.isInteger(seconds) ? seconds : seconds.toFixed(1)} s`;
}
