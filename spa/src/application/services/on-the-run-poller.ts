import type { Departure } from "../../domain/models/departure.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import type { DisplayConfiguration } from "../../domain/models/route-configuration.js";
import type { OnTheRunConfiguration } from "../../domain/models/on-the-run-configuration.js";
import type { DepartureCache } from "../../domain/ports/departure-cache.js";
import {
  createStopFetchFailure,
  type StopFetchFailure,
} from "../../domain/models/stop-fetch-failure.js";
import type { PollCycleResult } from "../../domain/models/poll-cycle-result.js";
import type { PollProgress } from "../../domain/models/poll-progress.js";
import {
  DEFAULT_RETRY_POLICY,
  withRetries,
  type RetryPolicy,
} from "../../utils/retry.js";
import { rememberStationCoords } from "../../utils/station-coords.js";
import { createStopConfiguration } from "../../domain/models/stop-configuration.js";
import { CompositeDepartureRepository } from "../../adapters/composite-departure-repository.js";
import type { NearbySource } from "../../adapters/on-the-run-nearby-source.js";
import type { NearbyStation } from "../../domain/ports/nearby-station-repository.js";
import { DepartureGroupingService } from "./departure-grouping-service.js";
import { generateHeaderColors } from "./header-color-service.js";
import { LastKnownGroups } from "./last-known-groups.js";
import { PollLoop } from "./poll-loop.js";
import { PollProgressReporter } from "./poll-progress-reporter.js";

export interface OnTheRunPollerCallbacks {
  onUpdate: (result: PollCycleResult, pollerId: string) => void;
  onError: (error: Error, pollerId: string) => void;
  onUnsupportedProviders?: (providers: string[]) => void;
  onStatusUpdate?: (messages: string[], pollerId: string) => void;
  /** How far the running cycle has got, for the screen that has nothing to show yet. */
  onProgress?: (progress: PollProgress, pollerId: string) => void;
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
  private readonly pollerId: string;
  private readonly loop: PollLoop;
  private statusMessages: string[] = [];
  private lastLocation: { latitude: number; longitude: number } | null = null;
  private readonly progress: PollProgressReporter;
  private readonly lastKnown = new LastKnownGroups();

  constructor(
    private readonly nearby: NearbySource,
    private readonly cache: DepartureCache,
    private readonly config: OnTheRunConfiguration,
    private readonly callbacks: OnTheRunPollerCallbacks,
    private readonly routeDisplay?: DisplayConfiguration,
    private readonly configuredStops: StopConfiguration[] = [],
    private readonly retryPolicy: RetryPolicy = DEFAULT_RETRY_POLICY,
  ) {
    this.pollerId = `on-the-run-${Date.now()}-${Math.random().toString(36).substring(7)}`;
    this.progress = new PollProgressReporter((progress) =>
      this.callbacks.onProgress?.(progress, this.pollerId),
    );
    this.loop = new PollLoop(
      (fresh) => this.poll(fresh),
      () => this.getUpdateIntervalSeconds() * 1000,
      (error) => this.callbacks.onError(error, this.pollerId),
    );
    console.log(`[${this.pollerId}] Created OnTheRunPoller`);
  }

  async start(): Promise<void> {
    if (this.loop.isRunning) {
      console.warn(
        `[${this.pollerId}] Poller already running, ignoring start() call`,
      );
      return;
    }

    await this.loop.start();
  }

  stop(): void {
    console.log(`[${this.pollerId}] Stopping poller`);
    this.loop.stop();
  }

  async refreshNow(): Promise<void> {
    await this.loop.refreshNow();
  }

  private async poll(fresh: boolean): Promise<void> {
    const shouldUpdateLocation =
      fresh ||
      (this.config.updateLocationOnEveryPoll ?? true) ||
      !this.lastLocation;
    this.setStatus([
      shouldUpdateLocation ? "Fetching location..." : "Using last location...",
    ]);
    const location = shouldUpdateLocation
      ? await this.fetchLocationOrExplain()
      : this.lastLocation!;
    if (shouldUpdateLocation) {
      this.lastLocation = location;
    }
    const locationLabel = shouldUpdateLocation
      ? `Fetched location: ${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`
      : `Using last location: ${location.latitude.toFixed(5)}, ${location.longitude.toFixed(5)}`;
    this.setStatus([locationLabel, "Finding nearby stops..."]);
    const nearbyStations = await this.fetchNearbyStationsOrExplain(location);

    const stationsInRange = this.filterStationsByRadius(
      nearbyStations,
      location,
    );
    this.rememberStopPositions(stationsInRange);
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
      this.callbacks.onUpdate(
        { groups: [], successCount: 0, failures: [] },
        this.pollerId,
      );
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
    const failures: StopFetchFailure[] = [];

    this.progress.begin(stationsInRange.length);

    for (const station of stationsInRange) {
      const baseStopConfig = this.createBaseStopConfig(station);

      try {
        const departures = await this.loadDepartures(
          baseStopConfig,
          departureRepository,
          fresh,
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

        const stationGroups: GroupedDepartures[] = [];
        for (const stopConfig of stopConfigs) {
          const departuresForStop =
            stopConfig.stationId === baseStopConfig.stationId
              ? baseDepartures
              : departures;
          stationGroups.push(
            ...groupingService.groupDepartures(departuresForStop, stopConfig),
          );
        }
        this.lastKnown.remember(station.id, stationGroups);
        this.appendGroups(allGroups, stopsWithDepartures, stationGroups);

        this.progress.settle(true);
      } catch (error) {
        const failure = createStopFetchFailure(baseStopConfig, error);
        failures.push(failure);
        console.error(
          `[${this.pollerId}] API poll error for ${station.name}: ${failure.message}`,
        );
        // The station keeps what it last delivered, marked as not refreshed,
        // so a hiccup does not blank a stop that is already on the screen.
        this.appendGroups(
          allGroups,
          stopsWithDepartures,
          this.lastKnown.stale(station.id),
        );
        this.progress.settle(false);
      }
    }

    const failedStationIds = new Set(
      failures.map((failure) => failure.stationId),
    );
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
          refreshFailed: failedStationIds.has(stopConfig.stationId),
          randomHeaderColors: stopConfig.randomHeaderColors,
          headerBackgroundBrightness: stopConfig.headerBackgroundBrightness,
          randomColorSalt: stopConfig.randomColorSalt,
        });
      }
    }

    generateHeaderColors(allGroups, this.routeDisplay);

    if (!this.loop.isRunning) {
      console.log(
        `[${this.pollerId}] Poller was stopped during poll() - discarding results`,
      );
      return;
    }

    console.log(
      `[${this.pollerId}] Combined ${allGroups.length} direction group(s) from ${this.progress.stopsOk} stop(s), ${failures.length} error(s)`,
    );
    this.callbacks.onUpdate(
      {
        groups: [...allGroups],
        successCount: this.progress.stopsOk,
        failures,
      },
      this.pollerId,
    );
  }

  /** Adds groups to the board and records which stops now have departures. */
  private appendGroups(
    allGroups: GroupedDepartures[],
    stopsWithDepartures: Set<string>,
    groups: GroupedDepartures[],
  ): void {
    groups.forEach((group) => {
      allGroups.push({ ...group });
      stopsWithDepartures.add(group.stationId);
    });
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
    ).catch((error: unknown) => {
      throw new Error(describeGeolocationError(error), { cause: error });
    });

    return {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
    };
  }

  private getUpdateIntervalSeconds(): number {
    return this.config.updateLocationIntervalSeconds ?? 20;
  }

  /** One parenthetical: optional label + distance from last GPS (e.g. " (45 m)" or " (Platform 2, 45 m)"). */
  private formatLabelAndDistance(
    label: string | undefined,
    meters: number | undefined,
  ): string {
    const hasLabel = label != null && label.trim() !== "";
    const hasDistance = meters != null && Number.isFinite(meters);
    const distStr = hasDistance ? `${Math.round(meters)} m` : "";
    if (hasLabel && hasDistance) return ` (${label.trim()}, ${distStr})`;
    if (hasDistance) return ` (${distStr})`;
    if (hasLabel) return ` (${label.trim()})`;
    return "";
  }

  private createBaseStopConfig(station: NearbyStation): StopConfiguration {
    const suffix = this.formatLabelAndDistance(
      undefined,
      station.distanceMeters,
    );
    return createStopConfiguration({
      stationId: station.id,
      stationName: `${station.name}${suffix}`,
      maxDeparturesPerStop: this.config.maxDeparturesPerStop,
      maxDeparturesPerRoute: this.config.maxDeparturesPerRoute,
      showUngrouped: true,
      ungroupedTitle: "",
      apiProvider: this.nearby.adapter,
    });
  }

  private buildStopConfigsForStation(
    station: NearbyStation,
    baseStopConfig: StopConfiguration,
    subStops: SubStopInfo[],
    useSubStops: boolean,
  ): StopConfiguration[] {
    const stopConfigs: StopConfiguration[] = [];
    // MVG departures API returns stopPointGlobalId but no coordinates; use station distance only.
    const baseStopName = useSubStops
      ? `${station.name}${this.formatLabelAndDistance("rest", station.distanceMeters)}`
      : `${station.name}${this.formatLabelAndDistance(undefined, station.distanceMeters)}`;

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
      const configuredUngroupedTitle = this.resolveSubStopUngroupedTitle(
        subStop.stopPointId,
      );
      stopConfigs.push(
        createStopConfiguration({
          stationId: subStop.stopPointId,
          stationName: `${station.name}${this.formatLabelAndDistance(subStop.label, station.distanceMeters)}`,
          maxDeparturesPerStop: this.config.maxDeparturesPerStop,
          maxDeparturesPerRoute: this.config.maxDeparturesPerRoute,
          showUngrouped: true,
          ungroupedTitle: configuredUngroupedTitle ?? "",
          apiProvider: this.nearby.adapter,
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

  private resolveSubStopUngroupedTitle(stopPointId: string): string | null {
    if (this.configuredStops.length === 0) {
      return null;
    }
    const stopPointVariants = this.buildStopPointVariants(stopPointId);
    const match = this.configuredStops.find(
      (stop) =>
        this.hasConfiguredTitle(stop) &&
        this.stopPointIdsMatch(stop.stationId, stopPointVariants),
    );
    if (!match) {
      return null;
    }
    const title = this.getConfiguredTitle(match);
    if (!title) {
      return null;
    }
    const cleaned = this.stripParentheticalContent(title);
    return cleaned.length > 0 ? cleaned : null;
  }

  private hasConfiguredTitle(stop: StopConfiguration): boolean {
    return Boolean(this.getConfiguredTitle(stop));
  }

  private getConfiguredTitle(stop: StopConfiguration): string | null {
    if (stop.ungroupedTitle && stop.ungroupedTitle.trim().length > 0) {
      return stop.ungroupedTitle;
    }
    const directionKeys = Object.keys(stop.directionMappings ?? {});
    if (directionKeys.length > 0) {
      return directionKeys[0] ?? null;
    }
    return null;
  }

  private stopPointIdsMatch(
    configuredId: string,
    stopPointVariants: Set<string>,
  ): boolean {
    const configuredVariants = this.buildStopPointVariants(configuredId);
    for (const variant of stopPointVariants) {
      if (configuredVariants.has(variant)) {
        return true;
      }
    }
    return false;
  }

  private buildStopPointVariants(stationId: string): Set<string> {
    const variants = new Set<string>([stationId]);
    const parts = stationId.split(":");
    if (
      parts.length >= 5 &&
      parts[parts.length - 1] === parts[parts.length - 2]
    ) {
      const stopNumber = parts[parts.length - 1];
      const baseId = parts.slice(0, -2).join(":");
      variants.add(`${baseId}:${stopNumber}`);
      return variants;
    }
    if (parts.length === 4) {
      const stopNumber = parts[parts.length - 1];
      const baseId = parts.slice(0, -1).join(":");
      variants.add(`${baseId}:${stopNumber}:${stopNumber}`);
    }
    return variants;
  }

  private stripParentheticalContent(title: string): string {
    return title
      .replace(/\s*\([^)]*\)/g, " ")
      .replace(/\s+/g, " ")
      .trim();
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

  /** The map links ask for these stops later; this lookup already knows where they are. */
  private rememberStopPositions(stations: NearbyStation[]): void {
    for (const station of stations) {
      rememberStationCoords(station.id, station.latitude, station.longitude);
    }
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
    fresh: boolean,
  ): Promise<Departure[]> {
    if (!fresh) {
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

    const configuredLimit = stopConfig.maxDeparturesFetch ?? 50;
    const minLimitForDisplay =
      (stopConfig.maxHoursInAdvance ?? 0) >= 1
        ? Math.ceil(stopConfig.maxHoursInAdvance! * 30)
        : 0;
    const fetchLimit = Math.max(configuredLimit, minLimitForDisplay);

    const configuredDuration = stopConfig.fetchMaxMinutesInAdvance ?? 120;
    const minDurationForDisplay =
      (stopConfig.maxHoursInAdvance ?? 0) >= 1
        ? stopConfig.maxHoursInAdvance! * 60
        : 0;
    const durationMinutes = Math.max(configuredDuration, minDurationForDisplay);

    const departures = await withRetries(
      () =>
        this.progress.whileAwaiting(stopConfig.stationName, () =>
          departureRepository.getDepartures(stopConfig.stationId, {
            limit: fetchLimit,
            offsetMinutes: stopConfig.departureLeewayMinutes ?? 0,
            durationMinutes,
          }),
        ),
      this.retryPolicy,
      {
        onFailedAttempt: (failed) =>
          console.warn(
            `[${this.pollerId}] Retrying ${stopConfig.stationName} ` +
              `(attempt ${failed.attempt + 1}/${this.retryPolicy.attempts}): ${failed.error.message}`,
          ),
        onRetryWait: (wait) =>
          this.progress.retryWait(
            stopConfig.stationName,
            wait.attempt + 1,
            wait,
          ),
      },
    );

    if (departures.length > 0) {
      await this.cache.set(stopConfig.stationId, departures, 60);
    }

    return departures;
  }

  private setStatus(messages: string[]): void {
    this.statusMessages = messages;
    this.callbacks.onStatusUpdate?.([...messages], this.pollerId);
  }

  /** A location failure is not a stop failure, so it says so on the empty screen. */
  private async fetchLocationOrExplain(): Promise<{
    latitude: number;
    longitude: number;
  }> {
    try {
      return await this.getCurrentLocation();
    } catch (error) {
      this.setStatus([`Could not get your location: ${messageOf(error)}`]);
      throw error;
    }
  }

  /** Same for the nearby-stops lookup, which runs before any stop is fetched. */
  private async fetchNearbyStationsOrExplain(location: {
    latitude: number;
    longitude: number;
  }): Promise<NearbyStation[]> {
    try {
      return await this.nearby.repository.getNearbyStations(
        location.latitude,
        location.longitude,
      );
    } catch (error) {
      this.setStatus([`Could not look up nearby stops: ${messageOf(error)}`]);
      throw error;
    }
  }
}

function messageOf(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/**
 * The browser hands back a plain object with a code and a message, not an
 * Error, so its reason has to be dug out before it can be shown.
 */
function describeGeolocationError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  const message = (error as { message?: unknown } | null)?.message;
  if (typeof message === "string" && message.length > 0) {
    return message;
  }

  return "the browser did not give a reason";
}
