import type {
  NearbyStation,
  NearbyStationRepository,
} from "../../domain/ports/nearby-station-repository.js";
import { fetchWithTimeout } from "../../utils/http.js";
import type { VbbApiLocation } from "./vbb-api-types.js";

const V6_BASE = "https://v6.bvg.transport.rest";

/**
 * The API filters by distance itself, so it is asked for a neighbourhood wide
 * enough for any configured radius; the poller then narrows it down.
 */
const SEARCH_RADIUS_METERS = 1_000;
const MAX_RESULTS = 20;

/** BVG's stop lookup is `A=1@O=…@L=<IBNR>@`; departures are addressed by the IBNR. */
export class VbbStationRepository implements NearbyStationRepository {
  async getNearbyStations(
    latitude: number,
    longitude: number,
  ): Promise<NearbyStation[]> {
    const url = new URL(`${V6_BASE}/locations/nearby`);
    url.searchParams.set("latitude", String(latitude));
    url.searchParams.set("longitude", String(longitude));
    url.searchParams.set("distance", String(SEARCH_RADIUS_METERS));
    url.searchParams.set("results", String(MAX_RESULTS));
    url.searchParams.set("stops", "true");
    url.searchParams.set("addresses", "false");
    url.searchParams.set("poi", "false");

    console.log(`[VBB API] Fetching nearby stops: ${url.toString()}`);

    const response = await fetchWithTimeout(url.toString(), {
      headers: {
        accept: "application/json",
        "user-agent": "Mozilla/5.0",
      },
    });

    if (!response.ok) {
      throw new Error(
        `VBB API error: ${response.status} ${response.statusText}`,
      );
    }

    const data = await response.json();
    if (!Array.isArray(data)) {
      return [];
    }

    return data
      .filter(isStopWithPosition)
      .map((location) => toNearbyStation(location));
  }
}

/** A stop that knows where it is; the API's other location types are not stops. */
type StopWithPosition = VbbApiLocation & {
  id: string;
  name: string;
  location: { latitude: number; longitude: number };
};

function isStopWithPosition(
  location: VbbApiLocation,
): location is StopWithPosition {
  const position = location.location;
  return (
    location.type === "stop" &&
    typeof location.id === "string" &&
    typeof location.name === "string" &&
    location.name.length > 0 &&
    typeof position?.latitude === "number" &&
    typeof position.longitude === "number"
  );
}

function toNearbyStation(location: StopWithPosition): NearbyStation {
  return {
    id: location.id,
    name: location.name,
    latitude: location.location.latitude,
    longitude: location.location.longitude,
    distanceMeters:
      typeof location.distance === "number" ? location.distance : undefined,
  };
}
