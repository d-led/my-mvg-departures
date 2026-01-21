import type { Departure } from "./departure.js";

export interface GroupedDepartures {
  directionName: string;
  stopName: string; // Station/stop name (e.g., "Chiemgaustr", "Ungsteiner Str.")
  stationId: string; // Station ID (e.g., "de:09162:1108:2:2") - needed to match stop config when multiple stops have same name
  departures: Departure[];
  headerColor?: string; // Generated header color for non-first headers (matches Python)
}
