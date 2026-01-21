import type { Departure } from "./departure.js";

export interface GroupedDepartures {
  directionName: string;
  stopName: string; // Station/stop name (e.g., "Chiemgaustr", "Ungsteiner Str.")
  stationId: string; // Station ID (e.g., "de:09162:1108:2:2") - needed to match stop config when multiple stops have same name
  departures: Departure[];
  headerColor?: string; // Generated header color for non-first headers (matches Python)
  // Color settings from stop config (matches Python's DirectionGroupWithMetadata)
  // These are stored when the group is created, so each group knows its own settings
  // even when multiple stops share the same stationId
  randomHeaderColors?: boolean | null; // null means inherit from route display config
  headerBackgroundBrightness?: number | null; // null means inherit from route display config
  randomColorSalt?: number | null; // null means inherit from route display config
}
