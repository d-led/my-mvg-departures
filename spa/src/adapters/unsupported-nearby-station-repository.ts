import type {
  NearbyStation,
  NearbyStationRepository,
} from "../domain/ports/nearby-station-repository.js";

/**
 * An adapter that only knows stops by id cannot answer "which stop is near me".
 * Saying so beats an empty screen that looks like a quiet neighbourhood.
 */
export class UnsupportedNearbyStationRepository implements NearbyStationRepository {
  constructor(
    private readonly configured: readonly string[],
    private readonly supported: readonly string[],
  ) {}

  async getNearbyStations(): Promise<NearbyStation[]> {
    const used =
      this.configured.length > 0 ? this.configured.join(", ") : "no adapter";
    throw new Error(
      `on_the_run cannot find nearby stops with ${used}; use one of ${this.supported.join(", ")}`,
    );
  }
}
