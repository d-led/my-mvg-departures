/** Where a departure leaves from, as the screen shows it: one number per row. */
export interface StopPlace {
  platform: string | null;
  stopPosition: string | null;
}

/**
 * The VBB (Berlin) API folds the place into the platform string: buses stand at
 * "Pos. 5", U-Bahn platforms read "2 (U9)", S-Bahn just "5". Munich keeps the
 * two apart (`platform` vs `stopPositionNumber`), so splitting them here gives
 * both providers the same pair of fields.
 */
export function splitPlatform(
  rawPlatform: string | number | null | undefined,
  transportType: string,
): StopPlace {
  const text = rawPlatform == null ? "" : String(rawPlatform).trim();
  if (!text) {
    return { platform: null, stopPosition: null };
  }

  if (isRoadBound(transportType)) {
    return { platform: null, stopPosition: standNumber(text) };
  }

  return {
    platform: text.replace(/\s*\([^)]*\)\s*$/, "") || text,
    stopPosition: null,
  };
}

function isRoadBound(transportType: string): boolean {
  return transportType === "Bus" || transportType === "Tram";
}

/** "Pos. 10" -> "10", "Bussteig A" -> "A", "5" -> "5". */
function standNumber(text: string): string {
  const labelled = text.match(
    /(?:pos\.?|steig|bussteig)\s*([A-Za-z0-9]+)\s*$/i,
  );
  if (labelled) {
    return labelled[1];
  }

  const trailing = text.match(/([A-Za-z0-9]+)\s*$/);
  return trailing ? trailing[1] : text;
}
