export interface NearbyStation {
  id: string;
  name: string;
  place: string;
  latitude: number;
  longitude: number;
  distanceMeters?: number;
}

export class MvgStationRepository {
  private readonly baseUrl = "https://www.mvg.de/api/bgw-pt/v3/stations/nearby";

  async getNearbyStations(
    latitude: number,
    longitude: number,
  ): Promise<NearbyStation[]> {
    const url = new URL(this.baseUrl);
    url.searchParams.set("latitude", latitude.toString());
    url.searchParams.set("longitude", longitude.toString());

    console.log(`[MVG API] Fetching nearby stations: ${url.toString()}`);

    const response = await fetch(url.toString(), {
      headers: {
        accept: "application/json",
        "user-agent": "Mozilla/5.0",
      },
    });

    if (!response.ok) {
      throw new Error(
        `MVG API error: ${response.status} ${response.statusText}`,
      );
    }

    const results = await response.json();
    if (!Array.isArray(results)) {
      return [];
    }

    return results
      .map((location) => ({
        id: location.globalId as string,
        name: location.name as string,
        place: location.place as string,
        latitude: location.latitude as number,
        longitude: location.longitude as number,
        distanceMeters:
          typeof location.distance === "number" ? location.distance : undefined,
      }))
      .filter(
        (location) =>
          location.id &&
          location.name &&
          typeof location.latitude === "number" &&
          typeof location.longitude === "number",
      );
  }
}
