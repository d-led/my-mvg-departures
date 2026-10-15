import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import type { DisplayConfiguration } from "../../domain/models/route-configuration.js";
import {
  createStopFetchFailure,
  type StopFetchFailure,
} from "../../domain/models/stop-fetch-failure.js";
import type { PollCycleResult } from "../../domain/models/poll-cycle-result.js";
import { DEFAULT_RETRY_POLICY, withRetries, type RetryPolicy } from "../../utils/retry.js";
import { DepartureGroupingService } from "./departure-grouping-service.js";
import { generateHeaderColors } from "./header-color-service.js";

export interface MultiStopPollerCallbacks {
  onUpdate: (result: PollCycleResult, pollerId: string) => void;
  onError: (error: Error, pollerId: string) => void;
}

export class MultiStopPoller {
  private intervalId: number | null = null;
  private isRunning = false;
  private allGroups: GroupedDepartures[] = [];
  private isInitialPoll = true;
  private readonly pollerId: string;

  constructor(
    private readonly departureRepository: DepartureRepository,
    private readonly cache: DepartureCache,
    private readonly groupingService: DepartureGroupingService,
    private readonly stopConfigs: StopConfiguration[],
    private readonly refreshIntervalSeconds: number,
    private readonly callbacks: MultiStopPollerCallbacks,
    private readonly routeDisplay?: DisplayConfiguration, // Route display config for header color fallback
    private readonly retryPolicy: RetryPolicy = DEFAULT_RETRY_POLICY,
  ) {
    // Generate unique ID for this poller instance
    this.pollerId = `poller-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    console.log(
      `[${this.pollerId}] Created new MultiStopPoller for ${stopConfigs.length} stop(s)`,
    );
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      console.warn(
        `[${this.pollerId}] Poller already running, ignoring start() call`,
      );
      return;
    }

    console.log(
      `[${this.pollerId}] MultiStopPoller.start() called - setting isInitialPoll = true`,
    );
    this.isRunning = true;
    this.isInitialPoll = true;

    // Do initial poll immediately (always fetch fresh, don't use cache)
    console.log(
      `[${this.pollerId}] Starting initial poll (isInitialPoll = ${this.isInitialPoll})`,
    );
    await this.poll();

    // Mark that initial poll is done
    this.isInitialPoll = false;

    // Then poll periodically (will use cache if available)
    this.intervalId = window.setInterval(() => {
      this.poll().catch((error) => {
        this.callbacks.onError(error, this.pollerId);
      });
    }, this.refreshIntervalSeconds * 1000);
  }

  stop(): void {
    console.log(`[${this.pollerId}] Stopping poller`);
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
    this.isInitialPoll = true; // Reset for next start
  }

  /**
   * Force an immediate refresh (fetch fresh data now, bypassing cache)
   * Useful when page becomes visible after being hidden
   */
  async refreshNow(): Promise<void> {
    if (!this.isRunning) {
      console.warn("Poller not running, cannot refresh");
      return;
    }
    console.log("Forcing immediate refresh (page became visible)");
    // Temporarily set isInitialPoll to bypass cache
    const wasInitialPoll = this.isInitialPoll;
    this.isInitialPoll = true;
    try {
      await this.poll();
    } finally {
      this.isInitialPoll = wasInitialPoll;
    }
  }

  private async poll(): Promise<void> {
    const allGroups: GroupedDepartures[] = [];
    const stopsWithDepartures = new Set<string>(); // Track which stops have departures
    const failures: StopFetchFailure[] = [];
    let successCount = 0;

    // Process stops SEQUENTIALLY to preserve TOML order (matches Python: for stop_config in self.stop_configs)
    // This ensures stops appear in the same order as defined in the TOML configuration
    console.log(
      `Polling ${this.stopConfigs.length} stop(s)${this.isInitialPoll ? " (initial poll - fetching fresh)" : ""}`,
    );

    for (const stopConfig of this.stopConfigs) {
      try {
        const groups = await this.collectGroupsForStop(stopConfig);
        // Add groups from this stop in order (preserves direction order from TOML)
        groups.forEach((group) => {
          allGroups.push({ ...group });
        });
        if (groups.length > 0) {
          stopsWithDepartures.add(stopConfig.stationName);
        }
        successCount++;
      } catch (error) {
        const failure = createStopFetchFailure(stopConfig, error);
        failures.push(failure);
        console.error(
          `[${this.pollerId}] API poll error for ${stopConfig.stationName}: ${failure.message}`,
        );
      }
    }

    // Find stops without departures (matches Python: _find_stops_without_departures)
    const stopsWithoutDepartures = this.stopConfigs
      .filter((stop) => !stopsWithDepartures.has(stop.stationName))
      .map((stop) => stop.stationName)
      .sort(); // Sort alphabetically (matches Python: sorted(configured_stops - stops_with_departures))

    // Create empty groups for stops without departures (matches Python template lines 138-145)
    // Python template: header is just {{ stop_name }}, not "StopName → DirectionName"
    // A stop that failed to refresh is marked, so the UI can tell the two apart
    const failedStationIds = new Set(
      failures.map((failure) => failure.stationId),
    );
    for (const stopName of stopsWithoutDepartures) {
      const stopConfig = this.stopConfigs.find(
        (s) => s.stationName === stopName,
      );
      if (stopConfig) {
        allGroups.push({
          directionName: stopName, // For empty groups, directionName = stopName (header will be just stopName)
          stopName: stopConfig.stationName,
          stationId: stopConfig.stationId,
          departures: [], // Empty departures array (matches Python template line 142)
          refreshFailed: failedStationIds.has(stopConfig.stationId),
          // Store color settings from stop config
          randomHeaderColors: stopConfig.randomHeaderColors,
          headerBackgroundBrightness: stopConfig.headerBackgroundBrightness,
          randomColorSalt: stopConfig.randomColorSalt,
        });
      }
    }

    // Generate header colors for non-first headers (matches Python's _generate_header_colors)
    generateHeaderColors(allGroups, this.routeDisplay);

    // Check if poller is still running before updating
    // This prevents race conditions where a stopped poller's ongoing poll() completes
    // after a new poller has been started (e.g., during route switching)
    if (!this.isRunning) {
      console.log(
        `[${this.pollerId}] Poller was stopped during poll() - discarding results to prevent race condition`,
      );
      return;
    }

    // Update state with combined groups
    this.allGroups = allGroups;
    console.log(
      `[${this.pollerId}] Combined ${allGroups.length} direction groups from ${successCount} successful stop(s), ${failures.length} error(s), ${stopsWithoutDepartures.length} stop(s) without departures`,
    );
    this.callbacks.onUpdate(
      { groups: [...allGroups], successCount, failures },
      this.pollerId,
    );
  }

  /**
   * Departures for one stop, from cache when it is still fresh, otherwise from the API.
   * Throws when the stop cannot be refreshed, even after the in-cycle retries.
   */
  private async collectGroupsForStop(
    stopConfig: StopConfiguration,
  ): Promise<GroupedDepartures[]> {
    console.log(
      `Polling stop: ${stopConfig.stationName} (${stopConfig.stationId})`,
    );

    // On initial poll, always fetch fresh data (don't use cache)
    // On subsequent polls, check cache first
    if (!this.isInitialPoll) {
      const cached = await this.cache.get(stopConfig.stationId);
      if (cached && cached.length > 0) {
        console.log(
          `Using cached data for ${stopConfig.stationName} (${cached.length} departures)`,
        );
        return this.groupingService.groupDepartures(cached, stopConfig);
      }
    }

    console.log(
      `Fetching fresh data from API for ${stopConfig.stationName}...`,
    );
    const departures = await withRetries(
      () =>
        this.departureRepository.getDepartures(
          stopConfig.stationId,
          this.fetchOptionsFor(stopConfig),
        ),
      this.retryPolicy,
      (failed) =>
        console.warn(
          `[${this.pollerId}] Retrying ${stopConfig.stationName} ` +
            `(attempt ${failed.attempt + 1}/${this.retryPolicy.attempts}): ${failed.error.message}`,
        ),
    );

    if (departures.length === 0) {
      return [];
    }

    await this.cache.set(stopConfig.stationId, departures, 60);
    return this.groupingService.groupDepartures(departures, stopConfig);
  }

  private fetchOptionsFor(stopConfig: StopConfiguration): {
    limit: number;
    offsetMinutes: number;
    durationMinutes: number;
  } {
    const configuredLimit = stopConfig.maxDeparturesFetch ?? 50;
    const minLimitForDisplay =
      (stopConfig.maxHoursInAdvance ?? 0) >= 1
        ? Math.ceil(stopConfig.maxHoursInAdvance! * 30)
        : 0;

    const configuredDuration = stopConfig.fetchMaxMinutesInAdvance ?? 120;
    const minDurationForDisplay =
      (stopConfig.maxHoursInAdvance ?? 0) >= 1
        ? stopConfig.maxHoursInAdvance! * 60
        : 0;

    return {
      limit: Math.max(configuredLimit, minLimitForDisplay),
      offsetMinutes: stopConfig.departureLeewayMinutes ?? 0,
      durationMinutes: Math.max(configuredDuration, minDurationForDisplay),
    };
  }
}
