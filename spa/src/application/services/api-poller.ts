import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import { DepartureGroupingService } from "./departure-grouping-service.js";

export interface ApiPollerCallbacks {
  onUpdate: (
    groups: GroupedDepartures[],
    stopConfig: StopConfiguration,
  ) => void;
  onError: (error: Error, stopConfig: StopConfiguration) => void;
}

export class ApiPoller {
  private intervalId: number | null = null;
  private isRunning = false;

  constructor(
    private readonly departureRepository: DepartureRepository,
    private readonly cache: DepartureCache,
    private readonly groupingService: DepartureGroupingService,
    private readonly stopConfig: StopConfiguration,
    private readonly refreshIntervalSeconds: number,
    private readonly callbacks: ApiPollerCallbacks,
  ) {}

  async start(): Promise<void> {
    if (this.isRunning) {
      return;
    }

    this.isRunning = true;

    // Do initial poll immediately
    await this.poll();

    // Then poll periodically
    this.intervalId = window.setInterval(() => {
      this.poll().catch((error) => {
        this.callbacks.onError(error, this.stopConfig);
      });
    }, this.refreshIntervalSeconds * 1000);
  }

  stop(): void {
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
  }

  private async poll(): Promise<void> {
    try {
      // Check cache first
      const cached = await this.cache.get(this.stopConfig.stationId);
      if (cached && cached.length > 0) {
        const groups = this.groupingService.groupDepartures(
          cached,
          this.stopConfig,
        );
        this.callbacks.onUpdate(groups, this.stopConfig);
      }

      // Fetch fresh data
      const departures = await this.departureRepository.getDepartures(
        this.stopConfig.stationId,
        {
          limit: this.stopConfig.maxDeparturesFetch ?? 50,
          offsetMinutes: this.stopConfig.departureLeewayMinutes ?? 0,
          durationMinutes: this.stopConfig.fetchMaxMinutesInAdvance ?? 120,
        },
      );

      if (departures.length > 0) {
        // Update cache
        await this.cache.set(this.stopConfig.stationId, departures, 60);

        // Group and notify
        const groups = this.groupingService.groupDepartures(
          departures,
          this.stopConfig,
        );
        this.callbacks.onUpdate(groups, this.stopConfig);
      }
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      this.callbacks.onError(err, this.stopConfig);
    }
  }
}
