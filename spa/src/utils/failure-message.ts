import type {
  GroupedDepartures,
  StopFetchFailure,
} from "../domain/models/index.js";

/**
 * A loud notice only earns its space on a screen that would otherwise be empty.
 * When departures are already on screen, the degraded status icon and the
 * per-stop "refresh failed" marker are enough, and nothing jumps in the way on
 * a small display.
 */
export function shouldShowFailureNotice(
  failures: StopFetchFailure[],
  groups: GroupedDepartures[],
): boolean {
  return (
    failures.length > 0 &&
    !groups.some((group) => group.departures.length > 0)
  );
}

/** One-line summary of the stops that could not be refreshed. */
export function describeStopFailures(failures: StopFetchFailure[]): string {
  if (failures.length === 0) {
    return "";
  }

  const names = failures.map((failure) => failure.stationName).join(", ");
  if (failures.length === 1) {
    return `No data from ${names}`;
  }
  return `No data from ${failures.length} stops: ${names}`;
}

/** Per-stop reasons, one per line, for the failure notice's tooltip. */
export function describeStopFailureDetails(
  failures: StopFetchFailure[],
): string {
  return failures
    .map((failure) => `${failure.stationName}: ${failure.message}`)
    .join("\n");
}
