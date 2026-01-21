import { describe, it, expect, vi } from "vitest";
import { DepartureGroupingService } from "../../src/application/services/departure-grouping-service.js";
import { createDeparture } from "../../src/domain/models/departure.js";
import { createStopConfiguration } from "../../src/domain/models/stop-configuration.js";
import type { DepartureRepository } from "../../src/domain/ports/departure-repository.js";

describe("DepartureGroupingService", () => {
  const mockRepository: DepartureRepository = {
    getDepartures: vi.fn(),
  };

  const service = new DepartureGroupingService(mockRepository);

  it("should group departures by direction", () => {
    const now = new Date();
    const departures = [
      createDeparture({
        time: new Date(now.getTime() + 300000),
        plannedTime: new Date(now.getTime() + 300000),
        line: "U6",
        destination: "Garching-Forschungszentrum",
        transportType: "U-Bahn",
      }),
      createDeparture({
        time: new Date(now.getTime() + 600000),
        plannedTime: new Date(now.getTime() + 600000),
        line: "U6",
        destination: "Garching-Forschungszentrum",
        transportType: "U-Bahn",
      }),
    ];

    const stopConfig = createStopConfiguration({
      stationId: "de:09162:1110",
      stationName: "Giesing",
      directionMappings: {
        "->Garching": ["U6 Garching-Forschungszentrum"],
      },
    });

    const groups = service.groupDepartures(departures, stopConfig);

    expect(groups).toHaveLength(1);
    expect(groups[0].directionName).toBe("->Garching");
    expect(groups[0].departures).toHaveLength(2);
  });

  it("should filter excluded destinations", () => {
    const now = new Date();
    const departures = [
      createDeparture({
        time: new Date(now.getTime() + 300000),
        plannedTime: new Date(now.getTime() + 300000),
        line: "54",
        destination: "Münchner Freiheit",
        transportType: "Tram",
      }),
      createDeparture({
        time: new Date(now.getTime() + 600000),
        plannedTime: new Date(now.getTime() + 600000),
        line: "U6",
        destination: "Garching-Forschungszentrum",
        transportType: "U-Bahn",
      }),
    ];

    const stopConfig = createStopConfiguration({
      stationId: "de:09162:1110",
      stationName: "Giesing",
      excludeDestinations: ["54"],
      showUngrouped: true,
    });

    const groups = service.groupDepartures(departures, stopConfig);

    // Should only have ungrouped U6 departure (54 is excluded)
    const allDepartures = groups.flatMap((g) => g.departures);
    expect(allDepartures.find((d) => d.line === "54")).toBeUndefined();
    // U6 should be in ungrouped if showUngrouped is true, or not present if false
    if (stopConfig.showUngrouped) {
      expect(allDepartures.find((d) => d.line === "U6")).toBeDefined();
    }
  });

  it("should limit departures per route", () => {
    const now = new Date();
    const departures = Array.from({ length: 5 }, (_, i) =>
      createDeparture({
        time: new Date(now.getTime() + (i + 1) * 300000),
        plannedTime: new Date(now.getTime() + (i + 1) * 300000),
        line: "U6",
        destination: "Garching-Forschungszentrum",
        transportType: "U-Bahn",
      }),
    );

    const stopConfig = createStopConfiguration({
      stationId: "de:09162:1110",
      stationName: "Giesing",
      maxDeparturesPerRoute: 2,
      directionMappings: {
        "->Garching": ["U6 Garching-Forschungszentrum"],
      },
    });

    const groups = service.groupDepartures(departures, stopConfig);

    expect(groups[0].departures).toHaveLength(2);
  });
});
