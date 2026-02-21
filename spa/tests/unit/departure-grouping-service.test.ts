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

  describe("platform_filter_routes", () => {
    const baseDepartures = (now: Date) => [
      createDeparture({
        time: new Date(now.getTime() + 300000),
        plannedTime: new Date(now.getTime() + 300000),
        line: "54",
        destination: "Ostbahnhof",
        transportType: "Bus",
      }),
      createDeparture({
        time: new Date(now.getTime() + 600000),
        plannedTime: new Date(now.getTime() + 600000),
        line: "N44",
        destination: "Giesing",
        transportType: "Bus",
      }),
      createDeparture({
        time: new Date(now.getTime() + 900000),
        plannedTime: new Date(now.getTime() + 900000),
        line: "134",
        destination: "Marienplatz",
        transportType: "Bus",
      }),
    ];

    it("whitelists by line when platform_filter is not set", () => {
      const now = new Date();
      const stopConfig = createStopConfiguration({
        stationId: "de:09162:1129",
        stationName: "Am Harras",
        platformFilterRoutes: ["134", "54"],
        showUngrouped: true,
      });

      const groups = service.groupDepartures(baseDepartures(now), stopConfig);

      const allDepartures = groups.flatMap((g) => g.departures);
      expect(allDepartures.map((d) => d.line)).toEqual(["54", "134"]);
      expect(allDepartures.find((d) => d.line === "N44")).toBeUndefined();
    });

    it("uses exact line match: N44 is separate from 44", () => {
      const now = new Date();
      const departures = [
        ...baseDepartures(now),
        createDeparture({
          time: new Date(now.getTime() + 1200000),
          plannedTime: new Date(now.getTime() + 1200000),
          line: "44",
          destination: "Hauptbahnhof",
          transportType: "Bus",
        }),
      ];
      const stopConfig = createStopConfiguration({
        stationId: "de:09162:1129",
        stationName: "Am Harras",
        platformFilterRoutes: ["44"],
        showUngrouped: true,
      });

      const groups = service.groupDepartures(departures, stopConfig);

      const allDepartures = groups.flatMap((g) => g.departures);
      expect(allDepartures.map((d) => d.line)).toEqual(["44"]);
      expect(allDepartures.find((d) => d.line === "N44")).toBeUndefined();
    });

    it("shows all departures when platform_filter_routes is empty", () => {
      const now = new Date();
      const stopConfig = createStopConfiguration({
        stationId: "de:09162:1129",
        stationName: "Am Harras",
        platformFilterRoutes: [],
        showUngrouped: true,
      });

      const groups = service.groupDepartures(baseDepartures(now), stopConfig);

      const allDepartures = groups.flatMap((g) => g.departures);
      expect(allDepartures.map((d) => d.line)).toEqual(["54", "N44", "134"]);
    });

    it("shows no departures when none match the whitelist", () => {
      const now = new Date();
      const stopConfig = createStopConfiguration({
        stationId: "de:09162:1129",
        stationName: "Am Harras",
        platformFilterRoutes: ["U6", "S1"],
        showUngrouped: true,
      });

      const groups = service.groupDepartures(baseDepartures(now), stopConfig);

      const allDepartures = groups.flatMap((g) => g.departures);
      expect(allDepartures).toHaveLength(0);
    });

    it("with platform_filter set: routes not in platform_filter_routes bypass platform check", () => {
      const now = new Date();
      const departures = [
        createDeparture({
          time: new Date(now.getTime() + 300000),
          plannedTime: new Date(now.getTime() + 300000),
          line: "54",
          destination: "Ostbahnhof",
          transportType: "Bus",
          platform: "7",
        }),
        createDeparture({
          time: new Date(now.getTime() + 600000),
          plannedTime: new Date(now.getTime() + 600000),
          line: "N44",
          destination: "Giesing",
          transportType: "Bus",
          platform: "8",
        }),
      ];
      const stopConfig = createStopConfiguration({
        stationId: "de:09162:1129",
        stationName: "Am Harras",
        platformFilter: 7,
        platformFilterRoutes: ["54"],
        showUngrouped: true,
      });

      const groups = service.groupDepartures(departures, stopConfig);

      const allDepartures = groups.flatMap((g) => g.departures);
      expect(allDepartures.map((d) => d.line)).toEqual(["54", "N44"]);
      expect(allDepartures.find((d) => d.line === "54")?.platform).toBe("7");
      expect(allDepartures.find((d) => d.line === "N44")?.platform).toBe("8");
    });
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
