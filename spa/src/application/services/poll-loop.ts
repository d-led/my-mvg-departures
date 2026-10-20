/**
 * Runs refresh cycles back to back: the next cycle starts only once the
 * previous one is over, then the configured pause follows.
 *
 * The alternative - a `setInterval` that fires regardless of what is in flight -
 * hides the first result when a cycle takes longer than the interval, and piles
 * up parallel cycles against an API that is already slow. Here a slow API only
 * postpones the next cycle.
 */
export class PollLoop {
  private timerId: ReturnType<typeof setTimeout> | null = null;
  private cycle: Promise<void> | null = null;
  private running = false;

  /**
   * @param runCycle One full refresh cycle; `fresh` asks it to bypass caches.
   * @param intervalMs Pause between the end of one cycle and the next one.
   * @param onCycleError Reports a cycle that failed as a whole.
   */
  constructor(
    private readonly runCycle: (fresh: boolean) => Promise<void>,
    private readonly intervalMs: () => number,
    private readonly onCycleError: (error: Error) => void,
  ) {}

  get isRunning(): boolean {
    return this.running;
  }

  /** Runs the first cycle right away, then keeps refreshing. */
  async start(): Promise<void> {
    if (this.running) {
      return;
    }

    this.running = true;
    await this.startCycle(true);
  }

  stop(): void {
    this.running = false;
    this.cancelScheduledCycle();
  }

  /**
   * Refreshes right away, bypassing caches. Joins the cycle that is already in
   * flight instead of starting a second one; the pause restarts afterwards.
   */
  async refreshNow(): Promise<void> {
    if (!this.running) {
      console.warn("Poller not running, cannot refresh");
      return;
    }
    if (this.cycle) {
      return this.cycle;
    }

    this.cancelScheduledCycle();
    await this.startCycle(true);
  }

  private async startCycle(fresh: boolean): Promise<void> {
    this.timerId = null;
    await this.runOnce(fresh);
    this.scheduleNextCycle();
  }

  private scheduleNextCycle(): void {
    if (!this.running) {
      return;
    }

    this.cancelScheduledCycle();
    this.timerId = setTimeout(() => {
      void this.startCycle(false);
    }, this.intervalMs());
  }

  private cancelScheduledCycle(): void {
    if (this.timerId !== null) {
      clearTimeout(this.timerId);
      this.timerId = null;
    }
  }

  private runOnce(fresh: boolean): Promise<void> {
    this.cycle = this.executeCycle(fresh);
    return this.cycle;
  }

  private async executeCycle(fresh: boolean): Promise<void> {
    try {
      await this.runCycle(fresh);
    } catch (error) {
      this.onCycleError(
        error instanceof Error ? error : new Error(String(error)),
      );
    } finally {
      this.cycle = null;
    }
  }
}
