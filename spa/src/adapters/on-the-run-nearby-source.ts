import type { NearbyStationRepository } from "../domain/ports/nearby-station-repository.js";
import { MvgStationRepository } from "./mvg/mvg-station-repository.js";
import { UnsupportedNearbyStationRepository } from "./unsupported-nearby-station-repository.js";
import { VbbStationRepository } from "./vbb/vbb-station-repository.js";

/**
 * Where the stops around the user come from, and therefore which API answers
 * for their departures: a stop id only means something to its own adapter.
 */
export interface NearbySource {
  readonly adapter: string;
  readonly repository: NearbyStationRepository;
}

/** Adapters that can find stops near a coordinate. MVG is the default network. */
const NEARBY_FINDERS: Record<string, () => NearbyStationRepository> = {
  mvg: () => new MvgStationRepository(),
  vbb: () => new VbbStationRepository(),
};

/**
 * The first configured adapter that can look stops up grounds the page; the
 * rest of `use_adapters` is irrelevant here because the stops it finds are
 * fetched from that same API.
 */
export function nearbySourceFor(
  useAdapters: readonly string[] | undefined,
): NearbySource {
  const configured = (useAdapters ?? ["mvg"]).map((adapter) =>
    adapter.toLowerCase(),
  );
  const adapter = configured.find((name) => name in NEARBY_FINDERS);

  if (!adapter) {
    return {
      adapter: configured[0] ?? "mvg",
      repository: new UnsupportedNearbyStationRepository(
        configured,
        Object.keys(NEARBY_FINDERS),
      ),
    };
  }

  return { adapter, repository: NEARBY_FINDERS[adapter]() };
}
