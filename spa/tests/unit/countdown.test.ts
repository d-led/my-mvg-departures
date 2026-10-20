import { describe, it, expect } from "vitest";
import {
  countdownPosition,
  ringDashOffset,
} from "../../src/utils/countdown.js";

const INTERVAL_MS = 20_000;
const STARTED_AT = 1_000_000;
const CIRCUMFERENCE = 2 * Math.PI * 5;

describe("refresh countdown", () => {
  it("starts with the whole pause ahead", () => {
    expect(countdownPosition(STARTED_AT, STARTED_AT, INTERVAL_MS)).toEqual({
      remainingFraction: 1,
      remainingSeconds: 20,
    });
  });

  it("half way through shows half a ring and ten seconds", () => {
    expect(
      countdownPosition(STARTED_AT, STARTED_AT + 10_000, INTERVAL_MS),
    ).toEqual({ remainingFraction: 0.5, remainingSeconds: 10 });
  });

  it("rounds the seconds up, so it never claims to be finished early", () => {
    expect(
      countdownPosition(STARTED_AT, STARTED_AT + 19_500, INTERVAL_MS),
    ).toEqual({ remainingFraction: 0.025, remainingSeconds: 1 });
  });

  it("is done once the pause has passed, even when no timer fired meanwhile", () => {
    // A throttled page can miss thousands of ticks; the ring must not lag behind.
    expect(
      countdownPosition(STARTED_AT, STARTED_AT + 45_000, INTERVAL_MS),
    ).toEqual({ remainingFraction: 0, remainingSeconds: 0 });
  });

  it("treats a clock that runs backwards as no time passed", () => {
    expect(
      countdownPosition(STARTED_AT, STARTED_AT - 5_000, INTERVAL_MS),
    ).toEqual({ remainingFraction: 1, remainingSeconds: 20 });
  });

  it("has nothing to count without a pause", () => {
    expect(countdownPosition(STARTED_AT, STARTED_AT, 0)).toEqual({
      remainingFraction: 0,
      remainingSeconds: 0,
    });
  });
});

describe("refresh countdown ring", () => {
  // The deployed build starts the ring empty and fills it as the refresh
  // approaches; drawing it the other way round is a visible regression.
  it("is empty when the pause starts and full when the refresh is due", () => {
    const atStart = countdownPosition(STARTED_AT, STARTED_AT, INTERVAL_MS);
    const whenDue = countdownPosition(
      STARTED_AT,
      STARTED_AT + INTERVAL_MS,
      INTERVAL_MS,
    );

    expect(
      ringDashOffset(atStart.remainingFraction, CIRCUMFERENCE),
    ).toBeCloseTo(CIRCUMFERENCE);
    expect(ringDashOffset(whenDue.remainingFraction, CIRCUMFERENCE)).toBe(0);
  });

  it("fills steadily as time passes", () => {
    const offsets = [0, 5_000, 10_000, 15_000].map(
      (elapsed) =>
        ringDashOffset(
          countdownPosition(STARTED_AT, STARTED_AT + elapsed, INTERVAL_MS)
            .remainingFraction,
          CIRCUMFERENCE,
        ) + 0,
    );

    expect(offsets).toEqual([
      CIRCUMFERENCE,
      CIRCUMFERENCE * 0.75,
      CIRCUMFERENCE * 0.5,
      CIRCUMFERENCE * 0.25,
    ]);
  });
});
