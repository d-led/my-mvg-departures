import type {
  NearbyStation,
  NearbyStationRepository,
} from "../../domain/ports/nearby-station-repository.js";
import { fetchWithTimeout } from "../../utils/http.js";

export interface StationLocation {
  id: string;
  name: string;
  place: string;
  latitude: number;
  longitude: number;
}

const V3_BASE = "https://www.mvg.de/api/bgw-pt/v3";

export class MvgStationRepository implements NearbyStationRepository {
  private readonly baseUrl = `${V3_BASE}/stations/nearby`;
  private readonly stationsUrl = `${V3_BASE}/stations`;
  private readonly locationsUrl = `${V3_BASE}/locations`;

  async getNearbyStations(
    latitude: number,
    longitude: number,
  ): Promise<NearbyStation[]> {
    const url = new URL(this.baseUrl);
    url.searchParams.set("latitude", latitude.toString());
    url.searchParams.set("longitude", longitude.toString());

    console.log(`[MVG API] Fetching nearby stations: ${url.toString()}`);

    const response = await fetchWithTimeout(url.toString(), {
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
   * Coordinates of a station, by id when we have one and by name otherwise.
   *
   * `GET /stations?query=` ignores its query and returns the whole catalogue
   * (44k stations, ~11 MB), so it is not used: a known id is answered by
   * `GET /stations/{id}` (~300 bytes) and a bare name by the location search,
   * which returns a handful of matches.
   */
  async getStationByQuery(
    query: string,
    matchStationId?: string,
  ): Promise<StationLocation | null> {
    if (matchStationId) {
      const byId = await this.getStationById(baseStationId(matchStationId));
      if (byId) {
        return byId;
      }
    }

    return this.searchStationByName(query, matchStationId);
  }

  /**
   * The stations a name matches, in the order the API ranks them - what the
   * configurator offers when a page is given a stop it does not have yet.
   */
  async searchStations(query: string): Promise<StationLocation[]> {
    const trimmed = query.trim();
    if (trimmed === "") {
      return [];
    }

    const data = await this.fetchJson(
      `${this.locationsUrl}?query=${encodeURIComponent(trimmed)}&locationTypes=STATION`,
    );
    if (!Array.isArray(data)) {
      return [];
    }

    return data
      .filter(hasCoordinates)
      .map((station) => this.toStationLocation(station));
  }

  /** Sub-stations share the parent's coordinates. */
  private async getStationById(id: string): Promise<StationLocation | null> {
    const station = await this.fetchJson(
      `${this.stationsUrl}/${encodeURIComponent(id)}`,
    );
    return hasCoordinates(station) ? this.toStationLocation(station) : null;
  }

  private async searchStationByName(
    query: string,
    matchStationId?: string,
  ): Promise<StationLocation | null> {
    const data = await this.fetchJson(
      `${this.locationsUrl}?query=${encodeURIComponent(query)}`,
    );
    if (!Array.isArray(data)) {
      return null;
    }

    const stations = data.filter(hasCoordinates);
    const station =
      pickStation(stations, matchStationId) ?? stations[0] ?? null;
    return station ? this.toStationLocation(station) : null;
  }

  private async fetchJson(url: string): Promise<unknown> {
    try {
      const response = await fetchWithTimeout(url, {
        headers: {
          accept: "application/json",
          "user-agent": "Mozilla/5.0",
        },
      });
      return response.ok ? await response.json() : null;
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

interface LocationCandidate {
  globalId?: string;
  name?: string;
  place?: string;
  latitude?: number;
  longitude?: number;
}

/** `de:09162:1108:3:3` is a stop point of the station `de:09162:1108`. */
function baseStationId(stationId: string): string {
  return stationId.split(":").slice(0, 3).join(":");
}

function hasCoordinates(
  candidate: unknown,
): candidate is LocationCandidate & { latitude: number; longitude: number } {
  const location = candidate as LocationCandidate | null;
  return Boolean(
    location &&
    location.globalId &&
    typeof location.latitude === "number" &&
    typeof location.longitude === "number",
  );
}

/** Prefers the station the configured id belongs to, so a name collision cannot win. */
function pickStation<T extends { globalId?: string }>(
  stations: T[],
  matchStationId?: string,
): T | null {
  if (!matchStationId) {
    return null;
  }

  const exact = stations.find((station) => station.globalId === matchStationId);
  if (exact) {
    return exact;
  }

  return (
    stations
      .filter((station) => matchStationId.startsWith(station.globalId ?? ""))
      .reduce<T | null>(
        (longest, station) =>
          longest === null ||
          (station.globalId?.length ?? 0) > (longest.globalId?.length ?? 0)
            ? station
            : longest,
        null,
      ) ?? null
  );
}
