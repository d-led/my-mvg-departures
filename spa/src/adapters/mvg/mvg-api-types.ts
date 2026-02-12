// Types for MVG API responses
// Note: Departures API returns stationGlobalId and stopPointGlobalId but no coordinates
// for stop points, so we cannot compute distance-to-sub-stop; we use station distance only.
export interface MvgApiDeparture {
  realtimeDepartureTime?: number;
  plannedDepartureTime: number;
  delayInMinutes?: number;
  platform?: string;
  realtime?: boolean;
  label: string;
  destination: string;
  transportType: string;
  cancelled?: boolean;
  messages?: string[];
  stationGlobalId?: string;
  stopPointGlobalId?: string;
}
