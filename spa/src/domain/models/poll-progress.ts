/**
 * A failed stop that is waiting for its next attempt.
 * Emitted once when the pause starts and then once per second, so the screen
 * can count down instead of looking frozen.
 */
export interface RetryWaitProgress {
  stationName: string;
  /** The attempt that will run when the wait is over (1-based). */
  nextAttempt: number;
  attempts: number;
  /** Time left before the next attempt; 0 means it runs right away. */
  remainingMs: number;
}

/**
 * The call that is in flight right now. A request may legitimately take up to
 * its deadline, so the elapsed time has to be visible while it waits.
 */
export interface AwaitingStopProgress {
  stationName: string;
  elapsedSeconds: number;
}

/**
 * How far one refresh cycle has got. Only shown while the timetable is empty,
 * so a slow configuration says what it is doing instead of showing nothing.
 */
export interface PollProgress {
  /** Stops the cycle has to fetch, i.e. API calls to make. */
  stopsTotal: number;
  /** Stops already answered, whether the answer was data or an error. */
  stopsCompleted: number;
  /** Stops that answered. */
  stopsOk: number;
  /** Stops that failed, even after the in-cycle retries. */
  stopsFailed: number;
  /** Set while a failed stop waits for its next attempt. */
  retryWait: RetryWaitProgress | null;
  /** Set while a call is waiting for its answer. */
  awaiting: AwaitingStopProgress | null;
}

export function createPollProgress(stopsTotal: number): PollProgress {
  return {
    stopsTotal,
    stopsCompleted: 0,
    stopsOk: 0,
    stopsFailed: 0,
    retryWait: null,
    awaiting: null,
  };
}
