/**
 * Fetches and caches station coordinates for map links.
 * Uses MVG location query; cache keyed by stationId.
 */

const cache = new Map<string, { lat: number; lng: number }>();

async function fetchCoords(
  stationId: string,
  stopName: string,
): Promise<{ lat: number; lng: number } | null> {
  if (cache.has(stationId)) return cache.get(stationId)!;
  const query = stopName.includes(",")
    ? (stopName.trim().split(",")[0] ?? stopName)
    : stopName;
  try {
    const { MvgStationRepository } =
      await import("../adapters/mvg/mvg-station-repository.js");
    const repo = new MvgStationRepository();
    const station = await repo.getStationByQuery(query, stationId);
    if (station) {
      const coords = { lat: station.latitude, lng: station.longitude };
      cache.set(stationId, coords);
      return coords;
    }
  } catch {
    // ignore
  }
  return null;
}

/**
 * Get coordinates for a station (from cache or fetch). Calls onCoords when coords are available.
 */
export function getStationCoords(
  stationId: string,
  stopName: string,
  onCoords?: (coords: { lat: number; lng: number }) => void,
): Promise<{ lat: number; lng: number } | null> {
  const cached = cache.get(stationId);
  if (cached) {
    onCoords?.(cached);
    return Promise.resolve(cached);
  }
  return fetchCoords(stationId, stopName).then((c) => {
    if (c) onCoords?.(c);
    return c;
  });
}

export function getCachedCoords(
  stationId: string,
): { lat: number; lng: number } | undefined {
  return cache.get(stationId);
}
