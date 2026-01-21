import type { DepartureRepository } from "../../domain/ports/departure-repository.js";
import type { StopConfiguration } from "../../domain/models/stop-configuration.js";
import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";
import type { Departure } from "../../domain/models/departure.js";

export class DepartureGroupingService {
  constructor(private readonly departureRepository: DepartureRepository) {}

  async getGroupedDepartures(
    stopConfig: StopConfiguration,
  ): Promise<GroupedDepartures[]> {
    const fetchLimit = stopConfig.maxDeparturesFetch ?? 50;
    const durationMinutes = stopConfig.fetchMaxMinutesInAdvance ?? 120;
    const offsetMinutes = stopConfig.departureLeewayMinutes ?? 0;

    const departures = await this.departureRepository.getDepartures(
      stopConfig.stationId,
      {
        limit: fetchLimit,
        offsetMinutes,
        durationMinutes,
      },
    );

    const fetchTime = new Date();
    return this.groupDepartures(departures, stopConfig, fetchTime);
  }

  groupDepartures(
    departures: Departure[],
    stopConfig: StopConfiguration,
    referenceTime: Date = new Date(),
  ): GroupedDepartures[] {
    // Filter blacklisted
    let filtered = this.filterBlacklisted(departures, stopConfig);

    // Filter by stop point
    filtered = this.filterByStopPoint(filtered, stopConfig);

    // Group by direction
    const { directionGroups, ungrouped } = this.groupByDirection(
      filtered,
      stopConfig,
    );

    // Process direction groups
    const processedGroups = this.processDirectionGroups(
      directionGroups,
      stopConfig,
      referenceTime,
    );

    // Process ungrouped
    let processedUngrouped = ungrouped;
    if (processedUngrouped.length > 0) {
      processedUngrouped.sort((a, b) => a.time.getTime() - b.time.getTime());
      processedUngrouped = this.filterAndLimit(
        processedUngrouped,
        stopConfig,
        referenceTime,
      );
    }

    // Build result
    const result: GroupedDepartures[] = [];

    // Add direction groups in order
    for (const directionName of Object.keys(
      stopConfig.directionMappings ?? {},
    )) {
      const groupDepartures = processedGroups[directionName];
      if (groupDepartures && groupDepartures.length > 0) {
        result.push({ 
          directionName, 
          stopName: stopConfig.stationName,
          departures: groupDepartures 
        });
      }
    }

    // Add ungrouped if enabled
    if (stopConfig.showUngrouped && processedUngrouped.length > 0) {
      const ungroupedTitle = stopConfig.ungroupedTitle ?? "Other";
      result.push({
        directionName: ungroupedTitle,
        stopName: stopConfig.stationName,
        departures: processedUngrouped,
      });
    }

    return result;
  }

  private filterBlacklisted(
    departures: Departure[],
    stopConfig: StopConfiguration,
  ): Departure[] {
    if (
      !stopConfig.excludeDestinations ||
      stopConfig.excludeDestinations.length === 0
    ) {
      return departures;
    }

    return departures.filter(
      (d) => !this.matchesDeparture(d, stopConfig.excludeDestinations!),
    );
  }

  private filterByStopPoint(
    departures: Departure[],
    stopConfig: StopConfiguration,
  ): Departure[] {
    const stationIdParts = stopConfig.stationId.split(":");
    if (
      stationIdParts.length < 5 ||
      stationIdParts[stationIdParts.length - 1] !==
        stationIdParts[stationIdParts.length - 2]
    ) {
      return departures;
    }

    const stopPointGlobalId = stopConfig.stationId;
    return departures.filter(
      (d) =>
        d.stopPointGlobalId !== null &&
        d.stopPointGlobalId === stopPointGlobalId,
    );
  }

  private groupByDirection(
    departures: Departure[],
    stopConfig: StopConfiguration,
  ): { directionGroups: Record<string, Departure[]>; ungrouped: Departure[] } {
    const directionGroups: Record<string, Departure[]> = {};
    const ungrouped: Departure[] = [];

    for (const departure of departures) {
      const directionName = this.findMatchingDirection(
        departure,
        stopConfig.directionMappings ?? {},
      );
      if (directionName) {
        if (!directionGroups[directionName]) {
          directionGroups[directionName] = [];
        }
        directionGroups[directionName].push(departure);
      } else {
        ungrouped.push(departure);
      }
    }

    return { directionGroups, ungrouped };
  }

  private findMatchingDirection(
    departure: Departure,
    directionMappings: Record<string, string[]>,
  ): string | null {
    for (const [directionName, patterns] of Object.entries(directionMappings)) {
      if (this.matchesDeparture(departure, patterns)) {
        return directionName;
      }
    }
    return null;
  }

  private matchesDeparture(departure: Departure, patterns: string[]): boolean {
    const searchText = this.normalizeUnicode(
      `${departure.transportType} ${departure.line} ${departure.destination}`,
    ).toLowerCase();

    for (const pattern of patterns) {
      const normalizedPattern = this.normalizeUnicode(
        pattern.trim(),
      ).toLowerCase();
      if (searchText.includes(normalizedPattern)) {
        return true;
      }
    }
    return false;
  }

  private normalizeUnicode(text: string): string {
    return text.normalize("NFC");
  }

  private processDirectionGroups(
    directionGroups: Record<string, Departure[]>,
    stopConfig: StopConfiguration,
    referenceTime: Date,
  ): Record<string, Departure[]> {
    const processed: Record<string, Departure[]> = {};

    for (const [directionName, departures] of Object.entries(directionGroups)) {
      const sorted = [...departures].sort(
        (a, b) => a.time.getTime() - b.time.getTime(),
      );
      processed[directionName] = this.filterAndLimit(
        sorted,
        stopConfig,
        referenceTime,
      );
    }

    return processed;
  }

  private filterAndLimit(
    departures: Departure[],
    stopConfig: StopConfiguration,
    referenceTime: Date,
  ): Departure[] {
    let filtered = this.filterByPlatform(departures, stopConfig);
    filtered = this.filterByLeeway(filtered, stopConfig, referenceTime);
    filtered = this.filterByMaxHours(filtered, stopConfig);
    filtered = this.limitByRoute(filtered, stopConfig);
    return this.limitByStop(filtered, stopConfig);
  }

  private filterByPlatform(
    departures: Departure[],
    stopConfig: StopConfiguration,
  ): Departure[] {
    if (stopConfig.platformFilter === undefined) {
      return departures;
    }

    const platformFilter = stopConfig.platformFilter;
    const platformFilterRoutes = stopConfig.platformFilterRoutes ?? [];

    return departures.filter((d) => {
      if (
        platformFilterRoutes.length > 0 &&
        !platformFilterRoutes.includes(d.line)
      ) {
        return true; // Don't filter if route not in filter list
      }

      if (d.platform === null) {
        return false;
      }

      const platformStr = String(d.platform);
      return (
        platformStr === String(platformFilter) ||
        platformStr.includes(String(platformFilter))
      );
    });
  }

  private filterByLeeway(
    departures: Departure[],
    stopConfig: StopConfiguration,
    referenceTime: Date,
  ): Departure[] {
    const leewayMinutes = Math.max(0, stopConfig.departureLeewayMinutes ?? 0);
    const cutoffTime = new Date(
      referenceTime.getTime() + leewayMinutes * 60 * 1000,
    );

    return departures.filter((d) => {
      const depTime = d.time;
      return depTime >= cutoffTime;
    });
  }

  private filterByMaxHours(
    departures: Departure[],
    stopConfig: StopConfiguration,
  ): Departure[] {
    if (
      stopConfig.maxHoursInAdvance === undefined ||
      stopConfig.maxHoursInAdvance < 1
    ) {
      return departures;
    }

    const maxTime = new Date(
      Date.now() + stopConfig.maxHoursInAdvance * 60 * 60 * 1000,
    );
    return departures.filter((d) => d.time <= maxTime);
  }

  private limitByRoute(
    departures: Departure[],
    stopConfig: StopConfiguration,
  ): Departure[] {
    const maxPerRoute = stopConfig.maxDeparturesPerRoute ?? 2;
    const routeCounts: Record<string, number> = {};
    const limited: Departure[] = [];

    for (const departure of departures) {
      const routeKey = departure.line;
      const count = routeCounts[routeKey] ?? 0;
      if (count < maxPerRoute) {
        limited.push(departure);
        routeCounts[routeKey] = count + 1;
      }
    }

    return limited;
  }

  private limitByStop(
    departures: Departure[],
    stopConfig: StopConfiguration,
  ): Departure[] {
    const maxPerStop = stopConfig.maxDeparturesPerStop ?? 20;
    return departures.slice(0, maxPerStop);
  }
}
