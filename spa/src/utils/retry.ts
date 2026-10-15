export interface RetryPolicy {
  /** Total number of attempts, including the first one. */
  attempts: number;
  /** Pause between attempts, in milliseconds. */
  delayMs: number;
}

/**
 * Short in-cycle retries: a transient API hiccup should not blank a stop until
 * the next refresh interval comes around.
 */
export const DEFAULT_RETRY_POLICY: RetryPolicy = {
  attempts: 3,
  delayMs: 500,
};

/** Retry settings as written in the TOML display configuration. */
export interface DisplayRetrySettings {
  /** `fetch_retry_attempts`: total tries per stop and cycle (1 = no retry). */
  fetchRetryAttempts?: number;
  /** `fetch_retry_delay_ms`: pause between those tries. */
  fetchRetryDelayMs?: number;
}

/**
 * The policy for one route. Unset or unusable values fall back to the defaults,
 * so a typo can neither disable a stop forever nor hammer the API.
 */
export function retryPolicyFromDisplay(
  display?: DisplayRetrySettings,
): RetryPolicy {
  return {
    attempts: Math.max(
      1,
      display?.fetchRetryAttempts ?? DEFAULT_RETRY_POLICY.attempts,
    ),
    delayMs: Math.max(
      0,
      display?.fetchRetryDelayMs ?? DEFAULT_RETRY_POLICY.delayMs,
    ),
  };
}

export interface FailedAttempt {
  /** Number of the attempt that failed (1-based). */
  attempt: number;
  error: Error;
}

/**
 * Runs the operation, repeating it after a pause when it fails.
 * Throws the last error once every attempt is used up.
 */
export async function withRetries<T>(
  operation: () => Promise<T>,
  policy: RetryPolicy = DEFAULT_RETRY_POLICY,
  onFailedAttempt?: (failed: FailedAttempt) => void,
): Promise<T> {
  const attempts = Math.max(1, policy.attempts);
  let lastError: Error | null = null;

  for (let attempt = 1; attempt <= attempts; attempt++) {
    try {
      return await operation();
    } catch (error) {
      lastError = toError(error);
      if (attempt === attempts) {
        break;
      }
      onFailedAttempt?.({ attempt, error: lastError });
      await pause(policy.delayMs);
    }
  }

  throw lastError;
}

function toError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

function pause(delayMs: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, delayMs));
}
