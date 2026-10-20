/** Where the refresh countdown stands, measured against the wall clock. */
export interface CountdownPosition {
  /** 1 at the start of the pause, 0 when the next refresh is due. */
  remainingFraction: number;
  /** Whole seconds left, rounded up; 0 when the refresh is due. */
  remainingSeconds: number;
}

/**
 * A countdown has to follow the wall clock, not the number of timer callbacks.
 * Backgrounded pages - the embedded browser, a wall display whose tab lost
 * focus - throttle timers, and a tick-counting countdown then freezes or falls
 * behind while real time keeps running.
 */
export function countdownPosition(
  startedAtMs: number,
  nowMs: number,
  intervalMs: number,
): CountdownPosition {
  if (intervalMs <= 0) {
    return { remainingFraction: 0, remainingSeconds: 0 };
  }

  const elapsedMs = Math.max(0, nowMs - startedAtMs);
  const remainingMs = Math.max(0, intervalMs - elapsedMs);

  return {
    remainingFraction: remainingMs / intervalMs,
    remainingSeconds: Math.ceil(remainingMs / 1000),
  };
}

/**
 * `stroke-dashoffset` for a ring whose dash array is the circumference.
 * The ring starts empty and fills as the pause runs out - the direction the
 * deployed build draws it in, and the opposite of what a double inversion gives.
 */
export function ringDashOffset(
  remainingFraction: number,
  circumference: number,
): number {
  return circumference * remainingFraction;
}
