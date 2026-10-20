import {
  createPollProgress,
  type PollProgress,
  type RetryWaitProgress,
} from "../../domain/models/poll-progress.js";
import type { RetryWait } from "../../utils/retry.js";

/** How often an in-flight call reports how long it has been waiting. */
export const WAITING_TICK_MS = 1000;

/**
 * Turns the facts of one refresh cycle - how many stops are settled, which call
 * is in flight, how long until a retry - into progress events. Both pollers use
 * it, so an ordinary route and the on-the-run route report the same things.
 */
export class PollProgressReporter {
  private progress: PollProgress = createPollProgress(0);

  constructor(private readonly emit: (progress: PollProgress) => void) {}

  get stopsOk(): number {
    return this.progress.stopsOk;
  }

  /** A cycle starts: every stop is still to come. */
  begin(stopsTotal: number): void {
    this.progress = createPollProgress(stopsTotal);
    this.publish();
  }

  /** One stop is settled, whether it answered or failed. */
  settle(answered: boolean): void {
    this.progress = {
      ...this.progress,
      stopsCompleted: this.progress.stopsCompleted + 1,
      stopsOk: this.progress.stopsOk + (answered ? 1 : 0),
      stopsFailed: this.progress.stopsFailed + (answered ? 0 : 1),
      retryWait: null,
    };
    this.publish();
  }

  /** A failed stop waits for its next attempt. */
  retryWait(stationName: string, nextAttempt: number, wait: RetryWait): void {
    const retryWait: RetryWaitProgress = {
      stationName,
      nextAttempt,
      attempts: wait.attempts,
      remainingMs: wait.remainingMs,
    };
    this.progress = { ...this.progress, retryWait };
    this.publish();
  }

  /**
   * Runs one call and publishes how long it has been waiting, once per second,
   * so a stalled call is visible before its deadline turns it into a failure.
   * The call being under way also means any pending retry is over.
   */
  async whileAwaiting<T>(
    stationName: string,
    call: () => Promise<T>,
  ): Promise<T> {
    const startedAt = Date.now();
    const publishElapsed = () => {
      this.progress = {
        ...this.progress,
        retryWait: null,
        awaiting: {
          stationName,
          elapsedSeconds: Math.floor((Date.now() - startedAt) / 1000),
        },
      };
      this.publish();
    };

    publishElapsed();
    const ticker = setInterval(publishElapsed, WAITING_TICK_MS);
    try {
      return await call();
    } finally {
      clearInterval(ticker);
      this.progress = { ...this.progress, awaiting: null };
      this.publish();
    }
  }

  private publish(): void {
    this.emit({ ...this.progress });
  }
}
