import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { OnTheRunPoller } from "../../src/application/services/on-the-run-poller.js";
import type {
  MvgStationRepository,
  NearbyStation,
} from "../../src/adapters/mvg/mvg-station-repository.js";
import type { DepartureCache } from "../../src/domain/ports/departure-cache.js";
import type { PollProgress } from "../../src/domain/models/poll-progress.js";
import type { PollCycleResult } from "../../src/domain/models/index.js";

const CHIEMGAUSTRASSE = "de:09162:1108";
const GIESING = "de:09162:1110";

const NEARBY_STATIONS: NearbyStation[] = [
  {
    id: CHIEMGAUSTRASSE,
    name: "Chiemgaustr.",
    place: "München",
    latitude: 48.106_7,
    longitude: 11.596_3,
    distanceMeters: 20,
  },
  {
    id: GIESING,
    name: "Giesing",
    place: "München",
    latitude: 48.110_4,
    longitude: 11.596_1,
    distanceMeters: 40,
  },
];

function emptyCache(): DepartureCache {
  return { get: async () => null, set: async () => {}, clear: async () => {} };
}

function nearbyStationsRepository(
  stations: NearbyStation[],
): MvgStationRepository {
  return {
    getNearbyStations: async () => stations,
    getStationByQuery: async () => null,
  } as unknown as MvgStationRepository;
}

function departuresFor(globalId: string) {
  const time = Date.now() + 5 * 60_000;
  return [
    {
      realtimeDepartureTime: time,
      plannedDepartureTime: time,
      delayInMinutes: 0,
      platform: 1,
      realtime: true,
      label: "139",
      destination: "Trudering Bf.",
      transportType: "BUS",
      cancelled: false,
      messages: [],
      stopPointGlobalId: `${globalId}:3:3`,
    },
  ];
}

function jsonResponse(body: unknown, ok = true, status = 200): Response {
  return {
    ok,
    status,
    statusText: ok ? "OK" : "Service Unavailable",
    json: async () => body,
  } as unknown as Response;
}

/** Answers departures for every nearby stop; the first call for `failingStop` fails. */
function stubDepartures(failingStop: string) {
  const attempts = new Map<string, number>();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const globalId = new URL(url).searchParams.get("globalId") ?? "";
      const attempt = (attempts.get(globalId) ?? 0) + 1;
      attempts.set(globalId, attempt);

      if (globalId === failingStop && attempt === 1) {
        return jsonResponse("Service Unavailable", false, 503);
      }
      return jsonResponse(departuresFor(globalId));
    }),
  );
}

function stubGeolocation() {
  vi.stubGlobal("navigator", {
    geolocation: {
      getCurrentPosition: (success: PositionCallback) =>
        success({
          coords: { latitude: 48.106_7, longitude: 11.596_3 },
        } as GeolocationPosition),
    },
  });
}

describe("OnTheRunPoller progress", () => {
  beforeEach(() => {
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
    stubGeolocation();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("counts the nearby stops it is fetching, and the wait before a retry", async () => {
    stubDepartures(GIESING);
    const progressEvents: PollProgress[] = [];
    const updates: PollCycleResult[] = [];
    const errors: Error[] = [];

    const poller = new OnTheRunPoller(
      nearbyStationsRepository(NEARBY_STATIONS),
      emptyCache(),
      { radiusMeters: 100, useAdapters: ["mvg"] },
      {
        onUpdate: (result) => updates.push(result),
        onError: (error) => errors.push(error),
        onProgress: (progress) => progressEvents.push(progress),
      },
      undefined,
      [],
      { attempts: 2, delayMs: 0 },
    );

    await poller.start();
    poller.stop();

    expect(errors).toEqual([]);
    expect(progressEvents[0]).toEqual({
      stopsTotal: 2,
      stopsCompleted: 0,
      stopsOk: 0,
      stopsFailed: 0,
      retryWait: null,
    });
    expect(progressEvents).toContainEqual(
      expect.objectContaining({
        stopsCompleted: 1,
        retryWait: {
          stationName: "Giesing (40 m)",
          nextAttempt: 2,
          attempts: 2,
          remainingMs: 0,
        },
      }),
    );
    expect(progressEvents.at(-1)).toEqual({
      stopsTotal: 2,
      stopsCompleted: 2,
      stopsOk: 2,
      stopsFailed: 0,
      retryWait: null,
    });
    expect(updates).toHaveLength(1);
    expect(updates[0].failures).toEqual([]);
  });
});
