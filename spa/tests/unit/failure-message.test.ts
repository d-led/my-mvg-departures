import { describe, it, expect } from "vitest";
import {
  createDeparture,
  createStopFetchFailure,
} from "../../src/domain/models/index.js";
import {
  describeStopFailureDetails,
  describeStopFailures,
  shouldShowFailureNotice,
} from "../../src/utils/failure-message.js";

function groupWithDepartures(stopName: string) {
  return {
    directionName: "<<Other>>",
    stopName,
    stationId: "de:09162:1110",
    departures: [
      createDeparture({
        time: new Date(),
        plannedTime: new Date(),
        line: "U6",
        destination: "Garching-Forschungszentrum",
        transportType: "U-Bahn",
      }),
    ],
  };
}

function emptyGroup(stopName: string) {
  return {
    directionName: stopName,
    stopName,
    stationId: "de:09162:1200",
    departures: [],
  };
}

describe("failure messages", () => {
  const giesing = createStopFetchFailure(
    { stationId: "de:09162:1110", stationName: "Giesing" },
    new Error("MVG API error: 503 Service Unavailable"),
  );
  const sendlingerTor = createStopFetchFailure(
    { stationId: "de:09162:1200", stationName: "Sendlinger Tor" },
    new Error("Failed to fetch"),
  );

  it("says nothing when nothing failed", () => {
    expect(describeStopFailures([])).toBe("");
  });

  it("names the single stop that failed", () => {
    expect(describeStopFailures([giesing])).toBe("No data from Giesing");
  });

  it("counts and names all stops that failed", () => {
    expect(describeStopFailures([giesing, sendlingerTor])).toBe(
      "No data from 2 stops: Giesing, Sendlinger Tor",
    );
  });

  it("keeps the reason for every failed stop", () => {
    expect(describeStopFailureDetails([giesing, sendlingerTor])).toBe(
      "Giesing: MVG API error: 503 Service Unavailable\n" +
        "Sendlinger Tor: Failed to fetch",
    );
  });

  describe("failure notice visibility", () => {
    it("stays quiet when departures are already on screen", () => {
      expect(
        shouldShowFailureNotice(
          [sendlingerTor],
          [groupWithDepartures("Giesing"), emptyGroup("Sendlinger Tor")],
        ),
      ).toBe(false);
    });

    it("speaks up when the screen would otherwise be empty", () => {
      expect(
        shouldShowFailureNotice(
          [sendlingerTor],
          [emptyGroup("Sendlinger Tor")],
        ),
      ).toBe(true);
    });

    it("says nothing when no stop failed", () => {
      expect(
        shouldShowFailureNotice([], [groupWithDepartures("Giesing")]),
      ).toBe(false);
    });
  });
});
