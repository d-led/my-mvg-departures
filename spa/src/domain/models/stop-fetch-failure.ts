/**
 * A stop whose departures could not be fetched during a refresh cycle.
 * Reported to the UI so a partial outage is visible instead of silently
 * rendering as "no departures".
 */
export interface StopFetchFailure {
  stationId: string;
  stationName: string;
  /** Human readable reason, e.g. "MVG API error: 503 Service Unavailable". */
  message: string;
}

export function createStopFetchFailure(
  stop: { stationId: string; stationName: string },
  error: unknown,
): StopFetchFailure {
  return {
    stationId: stop.stationId,
    stationName: stop.stationName,
    message: error instanceof Error ? error.message : String(error),
  };
}
