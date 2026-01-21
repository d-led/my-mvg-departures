// Types for MVG API responses
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
  stopPointGlobalId?: string;
}
