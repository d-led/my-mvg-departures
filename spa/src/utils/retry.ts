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

/** How often a wait between two attempts reports its remaining time. */
export const RETRY_WAIT_TICK_MS = 1000;

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

/** Time left before the next attempt; `remainingMs: 0` means it runs now. */
export interface RetryWait {
  /** The attempt that just failed (1-based). */
  attempt: number;
  /** Attempts the policy allows in total. */
  attempts: number;
  remainingMs: number;
}

export interface RetryHooks {
  /** Called after a failed attempt that still has attempts left. */
  onFailedAttempt?: (failed: FailedAttempt) => void;
  /**
   * Called when the pause before the next attempt starts, then once per second
   * until the attempt runs. Lets the screen count down instead of freezing.
   */
  onRetryWait?: (wait: RetryWait) => void;
}

/**
 * Runs the operation, repeating it after a pause when it fails.
 * Throws the last error once every attempt is used up.
 */
export async function withRetries<T>(
  operation: () => Promise<T>,
  policy: RetryPolicy = DEFAULT_RETRY_POLICY,
  hooks: RetryHooks = {},
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
      hooks.onFailedAttempt?.({ attempt, error: lastError });
      await waitForNextAttempt(policy.delayMs, attempt, attempts, hooks);
    }
  }

  throw lastError;
}

async function waitForNextAttempt(
  delayMs: number,
  attempt: number,
  attempts: number,
  hooks: RetryHooks,
): Promise<void> {
  const reportWait = hooks.onRetryWait;
  if (!reportWait) {
    await pause(delayMs);
    return;
  }

  let remainingMs = delayMs;
  reportWait({ attempt, attempts, remainingMs });
  while (remainingMs > 0) {
    const step = Math.min(RETRY_WAIT_TICK_MS, remainingMs);
    await pause(step);
    remainingMs -= step;
    reportWait({ attempt, attempts, remainingMs });
  }
}

function toError(error: unknown): Error {
  return error instanceof Error ? error : new Error(String(error));
}

function pause(delayMs: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, delayMs));
}
