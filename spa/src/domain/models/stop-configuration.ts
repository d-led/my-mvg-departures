export interface StopConfiguration {
  stationId: string;
  stationName: string;
  maxDeparturesPerStop?: number;
  maxDeparturesPerRoute?: number;
  maxDeparturesFetch?: number;
  fetchMaxMinutesInAdvance?: number;
  departureLeewayMinutes?: number;
  maxHoursInAdvance?: number;
  showUngrouped?: boolean;
  ungroupedTitle?: string;
  excludeDestinations?: string[];
  directionMappings?: Record<string, string[]>;
  platformFilter?: number;
  platformFilterRoutes?: string[];
  apiProvider?: string;
  randomHeaderColors?: boolean;
  headerBackgroundBrightness?: number;
  randomColorSalt?: number;
}

export function createStopConfiguration(
  data: Partial<StopConfiguration> & { stationId: string; stationName: string },
): StopConfiguration {
  return {
    stationId: data.stationId,
    stationName: data.stationName,
    maxDeparturesPerStop: data.maxDeparturesPerStop ?? 20,
    maxDeparturesPerRoute: data.maxDeparturesPerRoute ?? 2,
    maxDeparturesFetch: data.maxDeparturesFetch ?? 50,
    fetchMaxMinutesInAdvance: data.fetchMaxMinutesInAdvance ?? 120,
    departureLeewayMinutes: data.departureLeewayMinutes ?? 0,
    maxHoursInAdvance: data.maxHoursInAdvance,
    showUngrouped: data.showUngrouped ?? false,
    ungroupedTitle: data.ungroupedTitle,
    excludeDestinations: data.excludeDestinations ?? [],
    directionMappings: data.directionMappings ?? {},
    platformFilter: data.platformFilter,
    platformFilterRoutes: data.platformFilterRoutes ?? [],
    apiProvider: data.apiProvider ?? "mvg",
    // Don't default randomHeaderColors to false - undefined means inherit from route display config
    // This matches Python: random_header_colors: bool | None = None
    randomHeaderColors: data.randomHeaderColors,
    headerBackgroundBrightness: data.headerBackgroundBrightness,
    // Don't default randomColorSalt to 0 - undefined means inherit from route display config
    // This matches Python: random_color_salt: int | None = None
    randomColorSalt: data.randomColorSalt,
  };
}
