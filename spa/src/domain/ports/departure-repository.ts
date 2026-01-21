import type { Departure } from "../models/departure.js";

export interface DepartureRepository {
  getDepartures(
    stationId: string,
    options?: {
      limit?: number;
      offsetMinutes?: number;
      transportTypes?: string[];
      durationMinutes?: number;
    },
  ): Promise<Departure[]>;
}
