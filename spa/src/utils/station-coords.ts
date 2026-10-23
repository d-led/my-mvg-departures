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

/**
 * Coordinates the caller already knows - a nearby lookup answered them - so the
 * map link needs no lookup through an API that may not know this stop at all.
 */
export function rememberStationCoords(
  stationId: string,
  latitude: number,
  longitude: number,
): void {
  cache.set(coordsKey(stationId), { lat: latitude, lng: longitude });
}

async function fetchCoords(
  stationId: string,
  stopName: string,
  provider: string,
): Promise<{ lat: number; lng: number } | null> {
  const key = coordsKey(stationId);
  const cached = cache.get(key);
  if (cached) return cached;

  const pending = inFlight.get(key);
  if (pending) return pending;

  const lookup = lookUpCoords(key, stationId, stopName, provider).finally(() =>
    inFlight.delete(key),
  );
  inFlight.set(key, lookup);
  return lookup;
}

async function lookUpCoords(
  key: string,
  stationId: string,
  stopName: string,
  provider: string,
): Promise<{ lat: number; lng: number } | null> {
  try {
    const coords =
      provider === "vbb"
        ? await vbbCoords(stationId)
        : await mvgCoords(stationId, stopName);
    if (coords) {
      cache.set(key, coords);
    }
    return coords;
  } catch {
    // A map link is a nicety: an unknown stop or a failing API is not an error.
    return null;
  }
}

async function mvgCoords(
  stationId: string,
  stopName: string,
): Promise<{ lat: number; lng: number } | null> {
  const query = stopName.includes(",")
    ? (stopName.trim().split(",")[0] ?? stopName)
    : stopName;
  const { MvgStationRepository } =
    await import("../adapters/mvg/mvg-station-repository.js");
  const station = await new MvgStationRepository().getStationByQuery(
    query,
    stationId,
  );
  return station ? { lat: station.latitude, lng: station.longitude } : null;
}

async function vbbCoords(
  stationId: string,
): Promise<{ lat: number; lng: number } | null> {
  const { fetchVbbStationPosition } =
    await import("../adapters/vbb/vbb-station-coordinates.js");
  const position = await fetchVbbStationPosition(stationId);
  return position ? { lat: position.latitude, lng: position.longitude } : null;
}

/**
 * Get coordinates for a station (from cache or the stop's own API). Calls
 * onCoords when coords are available.
 */
export function getStationCoords(
  stationId: string,
  stopName: string,
  provider: string,
  onCoords?: (coords: { lat: number; lng: number }) => void,
): Promise<{ lat: number; lng: number } | null> {
  const cached = cache.get(coordsKey(stationId));
  if (cached) {
    onCoords?.(cached);
    return Promise.resolve(cached);
  }
  return fetchCoords(stationId, stopName, provider).then((c) => {
    if (c) onCoords?.(c);
    return c;
  });
}

export function getCachedCoords(
  stationId: string,
): { lat: number; lng: number } | undefined {
  return cache.get(coordsKey(stationId));
}
