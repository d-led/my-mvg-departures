import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import { DepartureGroupingService } from "./departure-grouping-service.js";

export interface MultiStopPollerCallbacks {
  onUpdate: (groups: GroupedDepartures[]) => void;
  onError: (error: Error) => void;
}

export class MultiStopPoller {
  private intervalId: number | null = null;
  private isRunning = false;
  private allGroups: GroupedDepartures[] = [];
  private isInitialPoll = true;

  constructor(
    private readonly departureRepository: DepartureRepository,
    private readonly cache: DepartureCache,
    private readonly groupingService: DepartureGroupingService,
    private readonly stopConfigs: StopConfiguration[],
    private readonly refreshIntervalSeconds: number,
    private readonly callbacks: MultiStopPollerCallbacks,
  ) {}

  async start(): Promise<void> {
    if (this.isRunning) {
      console.warn("Poller already running, ignoring start() call");
      return;
    }

    console.log("MultiStopPoller.start() called - setting isInitialPoll = true");
    this.isRunning = true;
    this.isInitialPoll = true;

    // Do initial poll immediately (always fetch fresh, don't use cache)
    console.log("Starting initial poll (isInitialPoll =", this.isInitialPoll, ")");
    await this.poll();

    // Mark that initial poll is done
    this.isInitialPoll = false;

    // Then poll periodically (will use cache if available)
    this.intervalId = window.setInterval(() => {
      this.poll().catch((error) => {
        this.callbacks.onError(error);
      });
    }, this.refreshIntervalSeconds * 1000);
  }

  stop(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
    this.isInitialPoll = true; // Reset for next start
  }

  private async poll(): Promise<void> {
    const allGroups: GroupedDepartures[] = [];
    let successCount = 0;
    let errorCount = 0;

    // Poll all stops in parallel
    console.log(`Polling ${this.stopConfigs.length} stop(s) in parallel${this.isInitialPoll ? " (initial poll - fetching fresh)" : ""}`);
    const pollPromises = this.stopConfigs.map(async (stopConfig) => {
      console.log(`Polling stop: ${stopConfig.stationName} (${stopConfig.stationId})`);
      try {
        // On initial poll, always fetch fresh data (don't use cache)
        // On subsequent polls, check cache first
        if (!this.isInitialPoll) {
          const cached = await this.cache.get(stopConfig.stationId);
          if (cached && cached.length > 0) {
            console.log(`Using cached data for ${stopConfig.stationName} (${cached.length} departures)`);
            const groups = this.groupingService.groupDepartures(cached, stopConfig);
            return { groups, stopConfig, fromCache: true };
          }
        } else {
          console.log(`Initial poll: fetching fresh data for ${stopConfig.stationName} (skipping cache)`);
        }

        // Fetch fresh data
        console.log(`Fetching fresh data from API for ${stopConfig.stationName}...`);
        const departures = await this.departureRepository.getDepartures(
          stopConfig.stationId,
          {
            limit: stopConfig.maxDeparturesFetch ?? 50,
            offsetMinutes: stopConfig.departureLeewayMinutes ?? 0,
            durationMinutes: stopConfig.fetchMaxMinutesInAdvance ?? 120,
          },
        );

        if (departures.length > 0) {
          // Update cache
          await this.cache.set(stopConfig.stationId, departures, 60);

          // Group departures
          const groups = this.groupingService.groupDepartures(departures, stopConfig);
          return { groups, stopConfig, fromCache: false };
        }

        return { groups: [], stopConfig, fromCache: false };
      } catch (error) {
        errorCount++;
        const err = error instanceof Error ? error : new Error(String(error));
        console.error(`API poll error for ${stopConfig.stationName}:`, err);
        return { groups: [], stopConfig, error: err };
      }
    });

    const results = await Promise.all(pollPromises);

    // Combine groups from all stops
    // Keep groups separate per stop (don't merge by direction name)
    // This matches Python version where each stop creates its own groups with "StopName → DirectionName" headers
    results.forEach((result) => {
      if (result.groups.length > 0) {
        successCount++;
        // Add all groups from this stop (each group already has stopName set)
        result.groups.forEach((group) => {
          allGroups.push({ ...group });
        });
      } else if (result.error) {
        errorCount++;
      }
    });

    // Update state with combined groups
    this.allGroups = allGroups;
    console.log(`Combined ${allGroups.length} direction groups from ${successCount} successful stop(s), ${errorCount} error(s)`);
    this.callbacks.onUpdate([...allGroups]);
  }
}
