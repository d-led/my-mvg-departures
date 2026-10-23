/** A stop close to a coordinate, as an adapter's nearby lookup reports it. */
export interface NearbyStation {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  /** Straight-line distance from the searched coordinate, when the API says. */
  distanceMeters?: number;
}

/**
 * Finding the stops around a position, so "Next to me" can then ask that same
 * API for their departures.
 */
export interface NearbyStationRepository {
  getNearbyStations(
    latitude: number,
    longitude: number,
  ): Promise<NearbyStation[]>;
}
