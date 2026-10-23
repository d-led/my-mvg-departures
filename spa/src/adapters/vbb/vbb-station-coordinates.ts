import { fetchWithTimeout } from "../../utils/http.js";

const V6_BASE = "https://v6.bvg.transport.rest";

export interface StationPosition {
  latitude: number;
  longitude: number;
}

/**
 * Where a Berlin stop is. VBB addresses a stop by its IBNR (`900100003`) and
 * answers with the position under `location`. A stop the API does not know is
 * not an error for a map link, so that reports `null`.
 */
export async function fetchVbbStationPosition(
  stationId: string,
): Promise<StationPosition | null> {
  const response = await fetchWithTimeout(
    `${V6_BASE}/stops/${encodeURIComponent(stationId)}`,
    { headers: { accept: "application/json", "user-agent": "Mozilla/5.0" } },
  );

  if (!response.ok) {
    return null;
  }

  return positionOf(await response.json());
}

function positionOf(body: unknown): StationPosition | null {
  const location = (body as { location?: Record<string, unknown> } | null)
    ?.location;
  const latitude = location?.latitude;
  const longitude = location?.longitude;

  return typeof latitude === "number" && typeof longitude === "number"
    ? { latitude, longitude }
    : null;
}
