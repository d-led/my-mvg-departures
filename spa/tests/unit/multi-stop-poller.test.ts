import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MultiStopPoller } from "../../src/application/services/multi-stop-poller.js";
import { DepartureGroupingService } from "../../src/application/services/departure-grouping-service.js";
import { createDeparture } from "../../src/domain/models/departure.js";
import { createStopConfiguration } from "../../src/domain/models/stop-configuration.js";
import type { DepartureCache } from "../../src/domain/ports/departure-cache.js";
import type { DepartureRepository } from "../../src/domain/ports/departure-repository.js";
import type { PollCycleResult } from "../../src/domain/models/index.js";
import type { RetryPolicy } from "../../src/utils/retry.js";

/** Short interval keeps the periodic polling out of the way of the assertions. */
const INTERVAL_SECONDS = 3600;
const RETRY_POLICY_WITHOUT_WAITING: RetryPolicy = { attempts: 3, delayMs: 0 };

function departureIn(minutes: number) {
  const time = new Date(Date.now() + minutes * 60_000);
  return createDeparture({
    time,
    plannedTime: time,
    line: "U6",
    destination: "Garching-Forschungszentrum",
    transportType: "U-Bahn",
  });
}

const giesing = createStopConfiguration({
  stationId: "de:09162:1110",
  stationName: "Giesing",
  showUngrouped: true,
});
const sendlingerTor = createStopConfiguration({
  stationId: "de:09162:1200",
  stationName: "Sendlinger Tor",
  showUngrouped: true,
});

function emptyCache(): DepartureCache {
  return {
    get: async () => null,
    set: async () => {},
    clear: async () => {},
  };
}

async function pollOnce(
  stops: (typeof giesing)[],
  repository: DepartureRepository,
  retryPolicy: RetryPolicy = RETRY_POLICY_WITHOUT_WAITING,
): Promise<PollCycleResult> {
  const updates: PollCycleResult[] = [];
  const poller = new MultiStopPoller(
    repository,
    emptyCache(),
    new DepartureGroupingService(repository),
    stops,
    INTERVAL_SECONDS,
    {
      onUpdate: (result) => updates.push(result),
      onError: (error) => {
        throw error;
      },
    },
    undefined,
    retryPolicy,
  );

  await poller.start();
  poller.stop();

  return updates[0];
}

describe("MultiStopPoller", () => {
  beforeEach(() => {
    vi.spyOn(console, "log").mockImplementation(() => {});
    vi.spyOn(console, "warn").mockImplementation(() => {});
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows the departures of the stops that answered and names the stop that failed", async () => {
    const repository: DepartureRepository = {
      getDepartures: vi.fn(async (stationId: string) => {
        if (stationId === sendlingerTor.stationId) {
          throw new Error("MVG API error: 503 Service Unavailable");
        }
        return [departureIn(5)];
      }),
    };

    const result = await pollOnce([giesing, sendlingerTor], repository);

    expect(result.successCount).toBe(1);
    expect(result.failures).toEqual([
      {
        stationId: sendlingerTor.stationId,
        stationName: "Sendlinger Tor",
        message: "MVG API error: 503 Service Unavailable",
      },
    ]);
    expect(
      result.groups
        .filter((group) => group.departures.length > 0)
        .map((group) => group.stopName),
    ).toEqual(["Giesing"]);
    expect(
      result.groups.find((group) => group.stationId === sendlingerTor.stationId)
        ?.refreshFailed,
    ).toBe(true);
  });

  it("retries a stop inside the same refresh cycle", async () => {
    let failedOnce = false;
    const repository: DepartureRepository = {
      getDepartures: vi.fn(async () => {
        if (!failedOnce) {
          failedOnce = true;
          throw new Error("MVG API error: 503 Service Unavailable");
        }
        return [departureIn(5)];
      }),
    };

    const result = await pollOnce([giesing], repository);

    expect(result.failures).toEqual([]);
    expect(result.successCount).toBe(1);
    expect(repository.getDepartures).toHaveBeenCalledTimes(2);
  });

  it("tries every attempt of the retry policy before reporting a stop as failed", async () => {
    const repository: DepartureRepository = {
      getDepartures: vi.fn(async () => {
        throw new Error("network down");
      }),
    };

    const result = await pollOnce(
      [giesing, sendlingerTor],
      repository,
      { attempts: 3, delayMs: 0 },
    );

    const attemptsFor = (stationId: string) =>
      vi
        .mocked(repository.getDepartures)
        .mock.calls.filter(([id]) => id === stationId).length;

    expect(attemptsFor(giesing.stationId)).toBe(3);
    expect(attemptsFor(sendlingerTor.stationId)).toBe(3);
    expect(result.successCount).toBe(0);
    expect(result.failures.map((failure) => failure.message)).toEqual([
      "network down",
      "network down",
    ]);
  });

  it("does not retry when the configured budget is a single attempt", async () => {
    const repository: DepartureRepository = {
      getDepartures: vi.fn(async () => {
        throw new Error("network down");
      }),
    };

    const result = await pollOnce([giesing], repository, {
      attempts: 1,
      delayMs: 0,
    });

    expect(repository.getDepartures).toHaveBeenCalledTimes(1);
    expect(result.failures).toHaveLength(1);
  });

  it("does not treat a stop without departures as a failure", async () => {
    const repository: DepartureRepository = {
      getDepartures: vi.fn(async () => []),
    };

    const result = await pollOnce([giesing], repository);

    expect(result.failures).toEqual([]);
    expect(result.successCount).toBe(1);
    expect(result.groups).toContainEqual(
      expect.objectContaining({
        stationId: giesing.stationId,
        departures: [],
        refreshFailed: false,
      }),
    );
  });
});
