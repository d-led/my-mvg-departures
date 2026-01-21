import type { Departure } from "./departure.js";

export interface GroupedDepartures {
  directionName: string;
  stopName: string; // Station/stop name (e.g., "Chiemgaustr", "Ungsteiner Str.")
  departures: Departure[];
}
