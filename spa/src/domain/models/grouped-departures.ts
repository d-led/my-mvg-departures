import type { Departure } from "./departure.js";

export interface GroupedDepartures {
  directionName: string;
  departures: Departure[];
}
