/**
 * Fetches and caches station coordinates for map links.
 * Keyed by station: stop points (`de:09162:1110:4:4`) share their station's coordinates.
 */

const cache = new Map<string, { lat: number; lng: number }>();
/** Several groups of one station ask at once; they wait for the same answer. */
const inFlight = new Map<
  string,
  Promise<{ lat: number; lng: number } | null>
>();

function coordsKey(stationId: string): string {
  return stationId.split(":").slice(0, 3).join(":");
}

async function fetchCoords(
  stationId: string,
  stopName: string,
): Promise<{ lat: number; lng: number } | null> {
  const key = coordsKey(stationId);
  const cached = cache.get(key);
  if (cached) return cached;

  const pending = inFlight.get(key);
  if (pending) return pending;

  const lookup = lookUpCoords(key, stationId, stopName).finally(() =>
    inFlight.delete(key),
  );
  inFlight.set(key, lookup);
  return lookup;
}

async function lookUpCoords(
  key: string,
  stationId: string,
  stopName: string,
): Promise<{ lat: number; lng: number } | null> {
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
      cache.set(key, coords);
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
  const cached = cache.get(coordsKey(stationId));
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
  return cache.get(coordsKey(stationId));
}
