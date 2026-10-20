import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { MultiStopPoller } from "../../src/application/services/multi-stop-poller.js";
import { DepartureGroupingService } from "../../src/application/services/departure-grouping-service.js";
import { createDeparture } from "../../src/domain/models/departure.js";
import { createStopConfiguration } from "../../src/domain/models/stop-configuration.js";
import type { Departure } from "../../src/domain/models/departure.js";
import type { DepartureCache } from "../../src/domain/ports/departure-cache.js";
import type { DepartureRepository } from "../../src/domain/ports/departure-repository.js";
import type { PollProgress } from "../../src/domain/models/poll-progress.js";
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
  onProgress: (progress: PollProgress) => void = () => {},
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
      onProgress: (progress) => onProgress(progress),
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
    vi.useRealTimers();
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

    const result = await pollOnce([giesing, sendlingerTor], repository, {
      attempts: 3,
      delayMs: 0,
    });

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

  it("counts the answered calls while the cycle runs", async () => {
    const repository: DepartureRepository = {
      getDepartures: vi.fn(async (stationId: string) => {
        if (stationId === sendlingerTor.stationId) {
          throw new Error("MVG API error: 503 Service Unavailable");
        }
        return [departureIn(5)];
      }),
    };
    const progressEvents: PollProgress[] = [];

    await pollOnce(
      [giesing, sendlingerTor],
      repository,
      undefined,
      (progress) => progressEvents.push(progress),
    );

    // The retry ticks of the failing stop are covered by their own test.
    const settled = progressEvents.filter(
      (progress) => progress.retryWait === null,
    );
    expect(settled.map((progress) => progress.stopsCompleted)).toEqual([
      0, 1, 2,
    ]);
    expect(settled.at(-1)).toEqual({
      stopsTotal: 2,
      stopsCompleted: 2,
      stopsOk: 1,
      stopsFailed: 1,
      retryWait: null,
    });
  });

  it("counts the wait before a retry, then clears it", async () => {
    vi.useFakeTimers();
    const repository: DepartureRepository = {
      getDepartures: vi.fn(async () => {
        throw new Error("network down");
      }),
    };
    const progressEvents: PollProgress[] = [];
    const poller = new MultiStopPoller(
      repository,
      emptyCache(),
      new DepartureGroupingService(repository),
      [giesing],
      INTERVAL_SECONDS,
      {
        onUpdate: () => {},
        onError: () => {},
        onProgress: (progress) => progressEvents.push(progress),
      },
      undefined,
      { attempts: 2, delayMs: 3000 },
    );

    const started = poller.start();
    await vi.advanceTimersByTimeAsync(3000);
    await started;
    poller.stop();

    expect(
      progressEvents
        .map((progress) => progress.retryWait)
        .filter((wait) => wait !== null),
    ).toEqual([
      {
        stationName: "Giesing",
        nextAttempt: 2,
        attempts: 2,
        remainingMs: 3000,
      },
      {
        stationName: "Giesing",
        nextAttempt: 2,
        attempts: 2,
        remainingMs: 2000,
      },
      {
        stationName: "Giesing",
        nextAttempt: 2,
        attempts: 2,
        remainingMs: 1000,
      },
      { stationName: "Giesing", nextAttempt: 2, attempts: 2, remainingMs: 0 },
    ]);
    expect(progressEvents.at(-1)).toEqual(
      expect.objectContaining({ stopsFailed: 1, retryWait: null }),
    );
  });

  it("never fetches twice at once when a cycle outlasts the refresh interval", async () => {
    vi.useFakeTimers();
    let answerFirstFetch: ((departures: Departure[]) => void) | undefined;
    const getDepartures = vi.fn(() => {
      if (getDepartures.mock.calls.length === 1) {
        return new Promise<Departure[]>((resolve) => {
          answerFirstFetch = resolve;
        });
      }
      return Promise.resolve([departureIn(5)]);
    });
    const repository: DepartureRepository = { getDepartures };
    const poller = new MultiStopPoller(
      repository,
      emptyCache(),
      new DepartureGroupingService(repository),
      [giesing],
      5,
      { onUpdate: () => {}, onError: () => {}, onProgress: () => {} },
    );

    const started = poller.start();
    // Far beyond the 5 s interval: the fetch is still in flight.
    await vi.advanceTimersByTimeAsync(60_000);
    expect(getDepartures).toHaveBeenCalledTimes(1);

    answerFirstFetch?.([departureIn(5)]);
    await started;

    // The pause only starts once the first cycle is over.
    await vi.advanceTimersByTimeAsync(4_999);
    expect(getDepartures).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(getDepartures).toHaveBeenCalledTimes(2);

    poller.stop();
  });
});
