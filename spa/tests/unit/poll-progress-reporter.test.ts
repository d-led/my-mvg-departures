import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PollProgressReporter } from "../../src/application/services/poll-progress-reporter.js";
import type { PollProgress } from "../../src/domain/models/poll-progress.js";

function createReporter() {
  const events: PollProgress[] = [];
  return {
    events,
    reporter: new PollProgressReporter((progress) => events.push(progress)),
  };
}

describe("PollProgressReporter", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("counts the stops that are settled while the cycle runs", () => {
    const { events, reporter } = createReporter();

    reporter.begin(2);
    reporter.settle(true);
    reporter.settle(false);

    expect(events.map((event) => event.stopsCompleted)).toEqual([0, 1, 2]);
    expect(events.at(-1)).toEqual({
      stopsTotal: 2,
      stopsCompleted: 2,
      stopsOk: 1,
      stopsFailed: 1,
      retryWait: null,
      awaiting: null,
    });
    expect(reporter.stopsOk).toBe(1);
  });

  it("says which call is in flight and for how long", async () => {
    const { events, reporter } = createReporter();
    let finishCall: (() => void) | undefined;

    reporter.begin(1);
    const call = reporter.whileAwaiting(
      "Balanstr.",
      () =>
        new Promise<void>((resolve) => {
          finishCall = resolve;
        }),
    );

    await vi.advanceTimersByTimeAsync(2_000);

    expect(
      events
        .map((event) => event.awaiting)
        .filter((awaiting) => awaiting !== null),
    ).toEqual([
      { stationName: "Balanstr.", elapsedSeconds: 0 },
      { stationName: "Balanstr.", elapsedSeconds: 1 },
      { stationName: "Balanstr.", elapsedSeconds: 2 },
    ]);

    finishCall?.();
    await call;

    expect(events.at(-1)?.awaiting).toBeNull();
  });

  it("stops the clock when the call fails", async () => {
    const { events, reporter } = createReporter();

    await expect(
      reporter.whileAwaiting("Balanstr.", async () => {
        throw new Error("Request timed out after 15 s without an answer");
      }),
    ).rejects.toThrow("Request timed out after 15 s without an answer");

    expect(events.at(-1)?.awaiting).toBeNull();
  });
});
