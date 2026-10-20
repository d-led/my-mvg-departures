import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PollLoop } from "../../src/application/services/poll-loop.js";

const INTERVAL_MS = 5_000;

function createLoop(runCycle: (fresh: boolean) => Promise<void>) {
  return new PollLoop(
    runCycle,
    () => INTERVAL_MS,
    () => {},
  );
}

describe("PollLoop", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("runs the first cycle right away, fresh", async () => {
    const freshCycles: boolean[] = [];
    const loop = createLoop(async (fresh) => {
      freshCycles.push(fresh);
    });

    await loop.start();

    expect(freshCycles).toEqual([true]);
    loop.stop();
  });

  it("waits for the running cycle before refreshing again", async () => {
    let finishFirstCycle: (() => void) | undefined;
    const cycles: boolean[] = [];
    const loop = createLoop(async () => {
      cycles.push(true);
      if (cycles.length === 1) {
        await new Promise<void>((resolve) => {
          finishFirstCycle = resolve;
        });
      }
    });

    const started = loop.start();
    // Well past the refresh interval: a timer-driven loop would have fired.
    await vi.advanceTimersByTimeAsync(INTERVAL_MS * 4);
    expect(cycles).toHaveLength(1);

    finishFirstCycle?.();
    await started;
    // The pause starts when the cycle is over, not when it started.
    await vi.advanceTimersByTimeAsync(INTERVAL_MS - 1);
    expect(cycles).toHaveLength(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(cycles).toHaveLength(2);

    loop.stop();
  });

  it("does not refresh again after stop()", async () => {
    const runCycle = vi.fn(async () => {});
    const loop = createLoop(runCycle);

    await loop.start();
    loop.stop();
    await vi.advanceTimersByTimeAsync(INTERVAL_MS * 3);

    expect(runCycle).toHaveBeenCalledTimes(1);
  });

  it("joins the cycle in flight instead of starting a second one", async () => {
    let finishCycle: (() => void) | undefined;
    const cycles: boolean[] = [];
    const loop = createLoop(async () => {
      cycles.push(true);
      if (cycles.length === 1) {
        await new Promise<void>((resolve) => {
          finishCycle = resolve;
        });
      }
    });

    const started = loop.start();
    const manualRefresh = loop.refreshNow();

    finishCycle?.();
    await Promise.all([started, manualRefresh]);
    expect(cycles).toHaveLength(1);

    loop.stop();
  });

  it("refreshes immediately and defers the scheduled cycle", async () => {
    const freshFlags: boolean[] = [];
    const loop = createLoop(async (fresh) => {
      freshFlags.push(fresh);
    });

    await loop.start();
    await vi.advanceTimersByTimeAsync(INTERVAL_MS / 2);

    await loop.refreshNow();
    expect(freshFlags).toEqual([true, true]);

    // The pause runs from the manual refresh, so the scheduled one is not due yet.
    await vi.advanceTimersByTimeAsync(INTERVAL_MS - 1);
    expect(freshFlags).toHaveLength(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(freshFlags).toEqual([true, true, false]);

    loop.stop();
  });

  it("reports a failed cycle instead of failing the loop", async () => {
    const errors: Error[] = [];
    const loop = new PollLoop(
      async () => {
        throw new Error("MVG API error: 500");
      },
      () => INTERVAL_MS,
      (error) => errors.push(error),
    );

    await loop.start();

    expect(errors.map((error) => error.message)).toEqual([
      "MVG API error: 500",
    ]);
    loop.stop();
  });
});
