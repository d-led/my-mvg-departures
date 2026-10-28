import { describe, expect, it } from "vitest";
import { LastKnownGroups } from "../../src/application/services/last-known-groups.js";
import { createDeparture } from "../../src/domain/models/departure.js";
import type { Departure } from "../../src/domain/models/departure.js";
import type { GroupedDepartures } from "../../src/domain/models/grouped-departures.js";

const NOW = new Date("2026-10-28T09:00:00Z");

function departureIn(minutes: number): Departure {
  const time = new Date(NOW.getTime() + minutes * 60_000);
  return createDeparture({
    time,
    plannedTime: time,
    line: "U6",
    destination: "Garching-Forschungszentrum",
    transportType: "U-Bahn",
  });
}

function group(
  directionName: string,
  departures: Departure[],
): GroupedDepartures {
  return {
    directionName,
    stopName: "Giesing",
    stationId: "de:09162:1110",
    departures,
  };
}

describe("LastKnownGroups", () => {
  it("hands back the departures a stop last delivered", () => {
    const lastKnown = new LastKnownGroups();

    lastKnown.remember("de:09162:1110", [group("->Stadt", [departureIn(5)])]);

    expect(lastKnown.stale("de:09162:1110", NOW)).toEqual([
      expect.objectContaining({
        directionName: "->Stadt",
        refreshFailed: true,
        departures: [departureIn(5)],
      }),
    ]);
  });

  it("forgets a stop that answered with nothing", () => {
    const lastKnown = new LastKnownGroups();

    lastKnown.remember("de:09162:1110", [group("->Stadt", [departureIn(5)])]);
    lastKnown.remember("de:09162:1110", []);

    expect(lastKnown.stale("de:09162:1110", NOW)).toEqual([]);
  });

  it("has nothing for a stop that never answered", () => {
    const lastKnown = new LastKnownGroups();

    expect(lastKnown.stale("de:09162:1110", NOW)).toEqual([]);
  });

  it("drops the departures that have already left, and the groups they leave empty", () => {
    const lastKnown = new LastKnownGroups();
    lastKnown.remember("de:09162:1110", [
      group("->Stadt", [departureIn(-1), departureIn(5)]),
      group("->Neuperlach", [departureIn(-2)]),
    ]);

    expect(lastKnown.stale("de:09162:1110", NOW)).toEqual([
      expect.objectContaining({ directionName: "->Stadt" }),
    ]);
  });

  it("keeps only the most recent answer", () => {
    const lastKnown = new LastKnownGroups();

    lastKnown.remember("de:09162:1110", [group("->Stadt", [departureIn(5)])]);
    lastKnown.remember("de:09162:1110", [group("->Stadt", [departureIn(10)])]);

    expect(lastKnown.stale("de:09162:1110", NOW)).toEqual([
      expect.objectContaining({ departures: [departureIn(10)] }),
    ]);
  });
});
