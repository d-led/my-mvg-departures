export interface NearbyStation {
  id: string;
  name: string;
  place: string;
  latitude: number;
  longitude: number;
  distanceMeters?: number;
}

export interface StationLocation {
  id: string;
  name: string;
  place: string;
  latitude: number;
  longitude: number;
}

const V3_BASE = "https://www.mvg.de/api/bgw-pt/v3";

export class MvgStationRepository {
  private readonly baseUrl = `${V3_BASE}/stations/nearby`;
  private readonly stationsUrl = `${V3_BASE}/stations`;

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
          typeof location.distanceInMeters === "number"
            ? location.distanceInMeters
            : typeof location.distance === "number"
              ? location.distance
              : undefined,
      }))
      .filter(
        (location) =>
          location.id &&
          location.name &&
          typeof location.latitude === "number" &&
          typeof location.longitude === "number",
      );
  }

  /**
   * Look up station by name or id. Uses MVG v3 stations API.
   * When matchStationId is provided (e.g. stop point de:09162:1108:2:2), returns the station
   * with the longest globalId that is a prefix of matchStationId (e.g. de:09162:1108 = Chiemgaustraße),
   * so we never match a shorter prefix like de:09162:1 (Stachus). Sub-stations share the parent's coordinates;
   * the v3 API does not expose per-stop-point GPS.
   */
  async getStationByQuery(
    query: string,
    matchStationId?: string,
  ): Promise<StationLocation | null> {
    const url = `${this.stationsUrl}?query=${encodeURIComponent(query)}`;
    try {
      const response = await fetch(url, {
        headers: {
          accept: "application/json",
          "user-agent": "Mozilla/5.0",
        },
      });
      if (!response.ok) return null;
      const data = await response.json();
      const list: Array<{
        globalId?: string;
        name?: string;
        place?: string;
        latitude?: number;
        longitude?: number;
      }> = Array.isArray(data?.stations) ? data.stations : [];
      const withCoords = list.filter(
        (s) =>
          typeof s.latitude === "number" &&
          typeof s.longitude === "number" &&
          s.globalId,
      );
      if (matchStationId) {
        const exact = withCoords.find((s) => s.globalId === matchStationId);
        if (exact) return this.toStationLocation(exact);
        const prefixMatches = withCoords.filter(
          (s) => s.globalId && matchStationId.startsWith(s.globalId),
        );
        const longestPrefix = prefixMatches.length
          ? prefixMatches.reduce((a, b) =>
              (a.globalId?.length ?? 0) >= (b.globalId?.length ?? 0) ? a : b,
            )
          : null;
        if (longestPrefix) return this.toStationLocation(longestPrefix);
        return null;
      }
      const byName = withCoords.find(
        (s) =>
          s.name &&
          query.trim().toLowerCase().split(",")[0] &&
          s.name
            .toLowerCase()
            .includes(query.trim().toLowerCase().split(",")[0]),
      );
      return byName
        ? this.toStationLocation(byName)
        : withCoords[0]
          ? this.toStationLocation(withCoords[0])
          : null;
    } catch {
      return null;
    }
  }

  private toStationLocation(s: {
    globalId?: string;
    name?: string;
    place?: string;
    latitude?: number;
    longitude?: number;
  }): StationLocation {
    return {
      id: (s.globalId ?? "") as string,
      name: (s.name ?? "") as string,
      place: (s.place ?? "München") as string,
      latitude: Number(s.latitude),
      longitude: Number(s.longitude),
    };
  }
}
