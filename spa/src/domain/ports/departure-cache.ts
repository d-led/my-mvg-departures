import type { Departure } from "../models/departure.js";

export interface DepartureCache {
  get(stationId: string): Promise<Departure[] | null>;
  set(
    stationId: string,
    departures: Departure[],
    ttlSeconds?: number,
  ): Promise<void>;
  clear(): Promise<void>;
}
