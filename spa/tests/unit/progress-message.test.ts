import { describe, it, expect } from "vitest";
import { createPollProgress } from "../../src/domain/models/poll-progress.js";
import {
  describeFetchProgress,
  describeRetryWait,
} from "../../src/utils/progress-message.js";

describe("what the empty timetable says while fetching", () => {
  it("names the single stop it is waiting for", () => {
    expect(describeFetchProgress(createPollProgress(1))).toBe(
      "Fetching departures…",
    );
  });

  it("names the number of calls a larger configuration makes", () => {
    expect(describeFetchProgress(createPollProgress(8))).toBe(
      "Fetching 8 stops…",
    );
  });

  it("counts the calls that are already answered", () => {
    const progress = {
      ...createPollProgress(8),
      stopsCompleted: 3,
      stopsOk: 3,
    };

    expect(describeFetchProgress(progress)).toBe(
      "Fetching departures… 3 of 8 stops ok",
    );
  });

  it("mentions the calls that failed", () => {
    const progress = {
      ...createPollProgress(8),
      stopsCompleted: 4,
      stopsOk: 3,
      stopsFailed: 1,
    };

    expect(describeFetchProgress(progress)).toBe(
      "Fetching departures… 3 of 8 stops ok, 1 failed",
    );
  });
});

describe("the countdown before a retry", () => {
  it("says how long the wait is", () => {
    expect(
      describeRetryWait({
        stationName: "Chiemgaustr.",
        nextAttempt: 2,
        attempts: 3,
        remainingMs: 1400,
      }),
    ).toBe("Retrying Chiemgaustr. in 2 s (attempt 2 of 3)");
  });

  it("says when the wait is over", () => {
    expect(
      describeRetryWait({
        stationName: "Chiemgaustr.",
        nextAttempt: 3,
        attempts: 3,
        remainingMs: 0,
      }),
    ).toBe("Retrying Chiemgaustr. now (attempt 3 of 3)");
  });
});
