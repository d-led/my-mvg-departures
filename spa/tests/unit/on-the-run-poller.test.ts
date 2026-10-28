import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { OnTheRunPoller } from "../../src/application/services/on-the-run-poller.js";
import type { NearbySource } from "../../src/adapters/on-the-run-nearby-source.js";
import type { NearbyStation } from "../../src/domain/ports/nearby-station-repository.js";
import type { DepartureCache } from "../../src/domain/ports/departure-cache.js";
import type { PollProgress } from "../../src/domain/models/poll-progress.js";
import type { PollCycleResult } from "../../src/domain/models/index.js";

const CHIEMGAUSTRASSE = "de:09162:1108";
const GIESING = "de:09162:1110";

const NEARBY_STATIONS: NearbyStation[] = [
  {
    id: CHIEMGAUSTRASSE,
    name: "Chiemgaustr.",
    latitude: 48.106_7,
    longitude: 11.596_3,
    distanceMeters: 20,
  },
  {
    id: GIESING,
    name: "Giesing",
    latitude: 48.110_4,
    longitude: 11.596_1,
    distanceMeters: 40,
  },
];

function emptyCache(): DepartureCache {
  return { get: async () => null, set: async () => {}, clear: async () => {} };
}

function nearbySourceForStations(
  stations: NearbyStation[],
  adapter = "mvg",
): NearbySource {
  return {
    adapter,
    repository: { getNearbyStations: async () => stations },
  };
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
      nearbySourceForStations(NEARBY_STATIONS),
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
      awaiting: null,
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
      awaiting: null,
    });
    expect(updates).toHaveLength(1);
    expect(updates[0].failures).toEqual([]);
  });

  it("says which nearby stop it is waiting for", async () => {
    let answer: (() => void) | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (!new URL(url).searchParams.get("globalId")) {
          return Promise.resolve(jsonResponse([]));
        }
        return new Promise<Response>((resolve) => {
          answer = () => resolve(jsonResponse(departuresFor(CHIEMGAUSTRASSE)));
        });
      }),
    );
    const progressEvents: PollProgress[] = [];

    const poller = new OnTheRunPoller(
      nearbySourceForStations([NEARBY_STATIONS[0]]),
      emptyCache(),
      { radiusMeters: 100, useAdapters: ["mvg"] },
      {
        onUpdate: () => {},
        onError: () => {},
        onProgress: (p) => progressEvents.push(p),
      },
      undefined,
      [],
      { attempts: 1, delayMs: 0 },
    );

    const started = poller.start();
    await vi.waitFor(() =>
      expect(progressEvents.some((event) => event.awaiting !== null)).toBe(
        true,
      ),
    );
    const awaiting = progressEvents.find((event) => event.awaiting !== null);
    answer?.();
    await started;
    poller.stop();

    expect(awaiting?.awaiting?.stationName).toBe("Chiemgaustr. (20 m)");
  });

  it("explains a location failure instead of showing the last status", async () => {
    vi.stubGlobal("navigator", {
      geolocation: {
        getCurrentPosition: (
          _success: PositionCallback,
          failure: PositionErrorCallback,
        ) =>
          failure({
            code: 1,
            message: "User denied Geolocation",
          } as GeolocationPositionError),
      },
    });
    const statusUpdates: string[][] = [];
    const errors: Error[] = [];

    const poller = new OnTheRunPoller(
      nearbySourceForStations(NEARBY_STATIONS),
      emptyCache(),
      { radiusMeters: 100, useAdapters: ["mvg"] },
      {
        onUpdate: () => {},
        onError: (error) => errors.push(error),
        onStatusUpdate: (messages) => statusUpdates.push(messages),
      },
    );

    await poller.start();
    poller.stop();

    expect(errors.map((error) => error.message)).toEqual([
      "User denied Geolocation",
    ]);
    expect(statusUpdates.at(-1)).toEqual([
      "Could not get your location: User denied Geolocation",
    ]);
  });

  it("explains a nearby-stops failure instead of showing the last status", async () => {
    const statusUpdates: string[][] = [];
    const errors: Error[] = [];
    const failingNearbySource: NearbySource = {
      adapter: "mvg",
      repository: {
        getNearbyStations: async () => {
          throw new Error("Request timed out after 15 s without an answer");
        },
      },
    };

    const poller = new OnTheRunPoller(
      failingNearbySource,
      emptyCache(),
      { radiusMeters: 100, useAdapters: ["mvg"] },
      {
        onUpdate: () => {},
        onError: (error) => errors.push(error),
        onStatusUpdate: (messages) => statusUpdates.push(messages),
      },
    );

    await poller.start();
    poller.stop();

    expect(errors.map((error) => error.message)).toEqual([
      "Request timed out after 15 s without an answer",
    ]);
    expect(statusUpdates.at(-1)).toEqual([
      "Could not look up nearby stops: Request timed out after 15 s without an answer",
    ]);
  });

  it("asks the adapter that found the stops for their departures", async () => {
    const fetchMock = vi.fn<(url: string) => Promise<Response>>(async () =>
      jsonResponse({ departures: [vbbDeparture()] }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const updates: PollCycleResult[] = [];
    const berlinStop: NearbyStation = {
      id: "900100014",
      name: "U Märkisches Museum (Berlin)",
      latitude: 52.512_007,
      longitude: 13.408_768,
      distanceMeters: 25,
    };

    const poller = new OnTheRunPoller(
      nearbySourceForStations([berlinStop], "vbb"),
      emptyCache(),
      { radiusMeters: 100 },
      { onUpdate: (result) => updates.push(result), onError: () => {} },
      undefined,
      [],
      { attempts: 1, delayMs: 0 },
    );

    await poller.start();
    poller.stop();

    expect(fetchMock.mock.calls[0]?.[0]).toContain(
      "https://v6.bvg.transport.rest/stops/900100014/departures",
    );
    expect(
      updates[0]?.groups.flatMap((group) => group.departures),
    ).toHaveLength(1);
  });

  it("keeps showing the departures of a nearby stop that stops answering", async () => {
    const answering = new Set([CHIEMGAUSTRASSE, GIESING]);
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string) => {
        const globalId = new URL(url).searchParams.get("globalId") ?? "";
        if (!answering.has(globalId)) {
          return jsonResponse("Service Unavailable", false, 503);
        }
        return jsonResponse(departuresFor(globalId));
      }),
    );
    const updates: PollCycleResult[] = [];

    const poller = new OnTheRunPoller(
      nearbySourceForStations(NEARBY_STATIONS),
      emptyCache(),
      { radiusMeters: 100, useAdapters: ["mvg"] },
      { onUpdate: (result) => updates.push(result), onError: () => {} },
      undefined,
      [],
      { attempts: 1, delayMs: 0 },
    );

    await poller.start();
    answering.delete(GIESING);
    await poller.refreshNow();
    poller.stop();

    const secondCycle = updates[1];
    expect(secondCycle.failures.map((failure) => failure.stationName)).toEqual([
      "Giesing (40 m)",
    ]);
    expect(groupsOf(secondCycle, GIESING)).toEqual([
      expect.objectContaining({ refreshFailed: true }),
    ]);
    expect(
      groupsOf(secondCycle, GIESING).flatMap((group) => group.departures),
    ).toHaveLength(1);
    // The nearby stop that answered is left alone by its neighbour's failure.
    expect(
      groupsOf(secondCycle, CHIEMGAUSTRASSE).some(
        (group) => group.refreshFailed,
      ),
    ).toBe(false);
  });
});

/** What one cycle rendered for a stop. */
function groupsOf(result: PollCycleResult, stationId: string) {
  return result.groups.filter((group) => group.stationId === stationId);
}

/** A departure as the VBB API answers it, so the VBB adapter is the one used. */
function vbbDeparture() {
  const time = new Date(Date.now() + 5 * 60_000).toISOString();
  return {
    when: time,
    plannedWhen: time,
    direction: "Hermannstr.",
    platform: "2",
    cancelled: false,
    realtime: true,
    line: { name: "U8", product: "subway" },
  };
}
