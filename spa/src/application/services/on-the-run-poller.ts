import type { Departure } from "../../domain/models/departure.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import type { DisplayConfiguration } from "../../domain/models/route-configuration.js";
import type { OnTheRunConfiguration } from "../../domain/models/on-the-run-configuration.js";
import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import { createStopConfiguration } from "../../domain/models/stop-configuration.js";
import { CompositeDepartureRepository } from "../../adapters/composite-departure-repository.js";
import { DepartureGroupingService } from "./departure-grouping-service.js";
import { generateHeaderColors } from "./header-color-service.js";
import {
  MvgStationRepository,
  type NearbyStation,
} from "../../adapters/mvg/mvg-station-repository.js";

export interface OnTheRunPollerCallbacks {
  onUpdate: (groups: GroupedDepartures[], pollerId: string) => void;
  onError: (error: Error, pollerId: string) => void;
  onUnsupportedProviders?: (providers: string[]) => void;
  onStatusUpdate?: (messages: string[], pollerId: string) => void;
}

interface SubStopInfo {
  stopPointId: string;
  label: string;
}

interface GeoPosition {
  coords: {
    latitude: number;
    longitude: number;
  };
}

interface GeoPositionOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
}

export class OnTheRunPoller {
  private intervalId: number | null = null;
  private isRunning = false;
  private isInitialPoll = true;
  private readonly pollerId: string;
  private hasWarnedIgnoredAdapters = false;
  private statusMessages: string[] = [];
  private lastLocation: { latitude: number; longitude: number } | null = null;

  constructor(
    private readonly stationRepository: MvgStationRepository,
    private readonly cache: DepartureCache,
    private readonly config: OnTheRunConfiguration,
    private readonly callbacks: OnTheRunPollerCallbacks,
    private readonly routeDisplay?: DisplayConfiguration,
  ) {
    this.pollerId = `on-the-run-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    console.log(`[${this.pollerId}] Created OnTheRunPoller`);
  }

  async start(): Promise<void> {
    if (this.isRunning) {
      console.warn(
        `[${this.pollerId}] Poller already running, ignoring start() call`,
      );
      return;
    }

    this.isRunning = true;
    this.isInitialPoll = true;

    try {
      await this.poll();
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      this.callbacks.onError(err, this.pollerId);
    }
    this.isInitialPoll = false;

    const intervalSeconds = this.getUpdateIntervalSeconds();
    this.intervalId = window.setInterval(() => {
      this.poll().catch((error) => {
        this.callbacks.onError(error, this.pollerId);
      });
    }, intervalSeconds * 1000);
  }

  stop(): void {
    console.log(`[${this.pollerId}] Stopping poller`);
    if (this.intervalId !== null) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
    this.isRunning = false;
    this.isInitialPoll = true;
  }

  async refreshNow(): Promise<void> {
    if (!this.isRunning) {
      console.warn("Poller not running, cannot refresh");
      return;
    }

    const wasInitialPoll = this.isInitialPoll;
    this.isInitialPoll = true;
    try {
      await this.poll();
    } catch (error) {
      const err = error instanceof Error ? error : new Error(String(error));
      this.callbacks.onError(err, this.pollerId);
    } finally {
      this.isInitialPoll = wasInitialPoll;
    }
  }

  private async poll(): Promise<void> {
    if (!this.ensureAdapterSupport()) {
      return;
    }

    const shouldUpdateLocation =
      this.isInitialPoll ||
      (this.config.updateLocationOnEveryPoll ?? true) ||
      !this.lastLocation;
    this.setStatus([
      shouldUpdateLocation ? "Fetching location..." : "Using last location...",
    ]);
    const location = shouldUpdateLocation
      ? await this.getCurrentLocation()
      : this.lastLocation!;
    if (shouldUpdateLocation) {
      this.lastLocation = location;
    }
    const locationLabel = shouldUpdateLocation
      ? `Fetched location: ${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`
      : `Using last location: ${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
    this.setStatus([locationLabel, "Finding nearby stops..."]);
    const nearbyStations = await this.stationRepository.getNearbyStations(
      location.latitude,
      location.longitude,
    );

    const stationsInRange = this.filterStationsByRadius(
      nearbyStations,
      location,
    );
    const radius = this.config.radiusMeters ?? 50;
    const stopLabel = stationsInRange.length === 1 ? "stop" : "stops";
    if (stationsInRange.length === 0) {
      this.setStatus([
        locationLabel,
        `Found 0 stops in vicinity of ${radius}m`,
        "Check location settings or increase the radius configuration",
      ]);
    } else {
      this.setStatus([
        locationLabel,
        `Found ${stationsInRange.length} ${stopLabel} in vicinity of ${radius}m`,
        "Preparing route config",
      ]);
    }

    if (stationsInRange.length === 0) {
      console.warn(`[${this.pollerId}] No nearby stations found within radius`);
      this.callbacks.onUpdate([], this.pollerId);
      return;
    }

    const baseStopConfigs = stationsInRange.map((station) =>
      this.createBaseStopConfig(station),
    );
    const departureRepository = new CompositeDepartureRepository(
      baseStopConfigs,
    );
    this.callbacks.onUnsupportedProviders?.(
      departureRepository.getUnsupportedProviders(),
    );
    const groupingService = new DepartureGroupingService(departureRepository);

    const allGroups: GroupedDepartures[] = [];
    const stopsWithDepartures = new Set<string>();
    const suppressEmptyStopHeaders = new Set<string>();
    const orderedStopConfigs: StopConfiguration[] = [];
    let successCount = 0;
    let errorCount = 0;

    for (const station of stationsInRange) {
      const baseStopConfig = this.createBaseStopConfig(station);

      try {
        const departures = await this.loadDepartures(
          baseStopConfig,
          departureRepository,
        );

        const subStops = this.config.smartSubStops
          ? this.deriveSubStops(departures)
          : [];

        const useSubStops = subStops.length > 1;
        const stopConfigs = this.buildStopConfigsForStation(
          station,
          baseStopConfig,
          subStops,
          useSubStops,
        );
        orderedStopConfigs.push(...stopConfigs);

        const excludedStopPoints = useSubStops
          ? new Set(subStops.map((subStop) => subStop.stopPointId))
          : new Set<string>();
        const baseDepartures = useSubStops
          ? departures.filter(
              (departure) =>
                !excludedStopPoints.has(departure.stopPointGlobalId ?? ""),
            )
          : departures;
        if (useSubStops && baseDepartures.length === 0) {
          suppressEmptyStopHeaders.add(baseStopConfig.stationId);
        }

        let stationHasGroups = false;
        for (const stopConfig of stopConfigs) {
          const departuresForStop =
            stopConfig.stationId === baseStopConfig.stationId
              ? baseDepartures
              : departures;
          const groups = groupingService.groupDepartures(
            departuresForStop,
            stopConfig,
          );
          groups.forEach((group) => {
            allGroups.push({ ...group });
          });
          if (groups.length > 0) {
            stopsWithDepartures.add(stopConfig.stationId);
            stationHasGroups = true;
          }
        }

        if (stationHasGroups) {
          successCount++;
        }
      } catch (error) {
        errorCount++;
        const err = error instanceof Error ? error : new Error(String(error));
        console.error(
          `[${this.pollerId}] API poll error for ${station.name}:`,
          err,
        );
      }
    }

    for (const stopConfig of orderedStopConfigs) {
      if (!stopsWithDepartures.has(stopConfig.stationId)) {
        if (suppressEmptyStopHeaders.has(stopConfig.stationId)) {
          continue;
        }
        allGroups.push({
          directionName: stopConfig.stationName,
          stopName: stopConfig.stationName,
          stationId: stopConfig.stationId,
          departures: [],
          randomHeaderColors: stopConfig.randomHeaderColors,
          headerBackgroundBrightness: stopConfig.headerBackgroundBrightness,
          randomColorSalt: stopConfig.randomColorSalt,
        });
      }
    }

    generateHeaderColors(allGroups, this.routeDisplay);

    if (!this.isRunning) {
      console.log(
        `[${this.pollerId}] Poller was stopped during poll() - discarding results`,
      );
      return;
    }

    console.log(
      `[${this.pollerId}] Combined ${allGroups.length} direction group(s) from ${successCount} stop(s), ${errorCount} error(s)`,
    );
    this.callbacks.onUpdate([...allGroups], this.pollerId);
  }

  private async getCurrentLocation(): Promise<{
    latitude: number;
    longitude: number;
  }> {
    const geolocation = globalThis.navigator?.geolocation;
    if (!geolocation) {
      throw new Error("Geolocation is not supported by this browser");
    }

    const options: GeoPositionOptions = {
      enableHighAccuracy: this.config.usePreciseLocation ?? true,
      timeout: 15000,
      maximumAge: this.getUpdateIntervalSeconds() * 1000,
    };

    const position = await new Promise<GeoPosition>((resolve, reject) =>
      geolocation.getCurrentPosition(resolve, reject, options),
    );

    return {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    };
  }

  private getUpdateIntervalSeconds(): number {
    return this.config.updateLocationIntervalSeconds ?? 20;
  }

  private createBaseStopConfig(station: NearbyStation): StopConfiguration {
    return createStopConfiguration({
      stationId: station.id,
      stationName: station.name,
      maxDeparturesPerStop: this.config.maxDeparturesPerStop,
      maxDeparturesPerRoute: this.config.maxDeparturesPerRoute,
      showUngrouped: true,
      ungroupedTitle: "",
      apiProvider: "mvg",
    });
  }

  private buildStopConfigsForStation(
    station: NearbyStation,
    baseStopConfig: StopConfiguration,
    subStops: SubStopInfo[],
    useSubStops: boolean,
  ): StopConfiguration[] {
    const stopConfigs: StopConfiguration[] = [];

    const baseStopName = useSubStops ? `${station.name} (rest)` : station.name;

    stopConfigs.push(
      createStopConfiguration({
        ...baseStopConfig,
        stationName: baseStopName,
      }),
    );

    if (!useSubStops) {
      return stopConfigs;
    }

    const sortedSubStops = [...subStops].sort((a, b) =>
      this.compareSubStopLabels(a.label, b.label),
    );

    for (const subStop of sortedSubStops) {
      stopConfigs.push(
        createStopConfiguration({
          stationId: subStop.stopPointId,
          stationName: `${station.name} (${subStop.label})`,
          maxDeparturesPerStop: this.config.maxDeparturesPerStop,
          maxDeparturesPerRoute: this.config.maxDeparturesPerRoute,
          showUngrouped: true,
          ungroupedTitle: "",
          apiProvider: "mvg",
        }),
      );
    }

    return stopConfigs;
  }

  private compareSubStopLabels(a: string, b: string): number {
    const aNumber = Number(a);
    const bNumber = Number(b);
    const bothNumeric = Number.isFinite(aNumber) && Number.isFinite(bNumber);
    if (bothNumeric) {
      return aNumber - bNumber;
    }
    return a.localeCompare(b);
  }

  private deriveSubStops(departures: Departure[]): SubStopInfo[] {
    const subStops = new Map<string, Set<string>>();

    for (const departure of departures) {
      const stopPointId = departure.stopPointGlobalId;
      if (!stopPointId || !this.isStopPointId(stopPointId)) {
        continue;
      }
      if (!subStops.has(stopPointId)) {
        subStops.set(stopPointId, new Set());
      }
      if (departure.platform) {
        subStops.get(stopPointId)!.add(departure.platform);
      }
    }

    return Array.from(subStops.entries()).map(([stopPointId, platforms]) => {
      const platformLabel =
        platforms.size === 1 ? Array.from(platforms)[0] : null;
      const label = platformLabel ?? this.extractStopNumber(stopPointId);
      return { stopPointId, label };
    });
  }

  private isStopPointId(stationId: string): boolean {
    const parts = stationId.split(":");
    return (
      parts.length >= 5 && parts[parts.length - 1] === parts[parts.length - 2]
    );
  }

  private extractStopNumber(stopPointId: string): string {
    return stopPointId.split(":").slice(-1)[0] ?? stopPointId;
  }

  private filterStationsByRadius(
    stations: NearbyStation[],
    location: { latitude: number; longitude: number },
  ): NearbyStation[] {
    const radius = this.config.radiusMeters ?? 50;
    if (radius <= 0) {
      return stations;
    }

    const deduped = new Map<string, NearbyStation>();
    for (const station of stations) {
      if (!deduped.has(station.id)) {
        deduped.set(station.id, station);
      }
    }

    return Array.from(deduped.values())
      .map((station) => ({
        ...station,
        distanceMeters:
          station.distanceMeters ??
          this.calculateDistanceMeters(
            location.latitude,
            location.longitude,
            station.latitude,
            station.longitude,
          ),
      }))
      .filter((station) => (station.distanceMeters ?? 0) <= radius)
      .sort((a, b) => (a.distanceMeters ?? 0) - (b.distanceMeters ?? 0));
  }

  private calculateDistanceMeters(
    latitude: number,
    longitude: number,
    stationLatitude: number,
    stationLongitude: number,
  ): number {
    const toRadians = (value: number) => (value * Math.PI) / 180;
    const earthRadiusMeters = 6371000;
    const deltaLat = toRadians(stationLatitude - latitude);
    const deltaLon = toRadians(stationLongitude - longitude);
    const lat1 = toRadians(latitude);
    const lat2 = toRadians(stationLatitude);

    const a =
      Math.sin(deltaLat / 2) * Math.sin(deltaLat / 2) +
      Math.sin(deltaLon / 2) *
        Math.sin(deltaLon / 2) *
        Math.cos(lat1) *
        Math.cos(lat2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return earthRadiusMeters * c;
  }

  private async loadDepartures(
    stopConfig: StopConfiguration,
    departureRepository: CompositeDepartureRepository,
  ): Promise<Departure[]> {
    if (!this.isInitialPoll) {
      const cached = await this.cache.get(stopConfig.stationId);
      if (cached && cached.length > 0) {
        console.log(
          `[${this.pollerId}] Using cached data for ${stopConfig.stationName} (${cached.length} departures)`,
        );
        return cached;
      }
    }

    console.log(
      `[${this.pollerId}] Fetching departures for ${stopConfig.stationName} (${stopConfig.stationId})`,
    );

    const departures = await departureRepository.getDepartures(
      stopConfig.stationId,
      {
        limit: stopConfig.maxDeparturesFetch ?? 50,
        offsetMinutes: stopConfig.departureLeewayMinutes ?? 0,
        durationMinutes: stopConfig.fetchMaxMinutesInAdvance ?? 120,
      },
    );

    if (departures.length > 0) {
      await this.cache.set(stopConfig.stationId, departures, 60);
    }

    return departures;
  }

  private ensureAdapterSupport(): boolean {
    const adapters = (this.config.useAdapters ?? ["mvg"]).map((adapter) =>
      adapter.toLowerCase(),
    );
    if (!adapters.includes("mvg")) {
      this.callbacks.onError(
        new Error(
          "on_the_run requires the mvg adapter to fetch nearby stations",
        ),
        this.pollerId,
      );
      return false;
    }
    const ignoredAdapters = adapters.filter((adapter) => adapter !== "mvg");
    if (ignoredAdapters.length > 0 && !this.hasWarnedIgnoredAdapters) {
      console.warn(
        `[${this.pollerId}] Ignoring unsupported on_the_run adapters: ${ignoredAdapters.join(", ")}`,
      );
      this.hasWarnedIgnoredAdapters = true;
    }
    return true;
  }

  private setStatus(messages: string[]): void {
    this.statusMessages = messages;
    this.callbacks.onStatusUpdate?.([...messages], this.pollerId);
  }
}
