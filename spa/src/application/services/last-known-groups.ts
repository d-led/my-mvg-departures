import type { GroupedDepartures } from "../../domain/models/grouped-departures.js";

/**
 * What each stop last delivered, so a stop whose refresh fails keeps its place
 * on the board with the departures it had - greyed out - instead of blanking
 * until the API answers again.
 *
 * Only the departures still to come are kept: a stop that stays down would
 * otherwise carry a growing tail of rows whose time has passed, which the board
 * would label "now" forever.
 */
export class LastKnownGroups {
  private readonly byStation = new Map<string, GroupedDepartures[]>();

  /** A stop answered: remember what it said, even when it said "nothing". */
  remember(stationId: string, groups: GroupedDepartures[]): void {
    this.byStation.set(
      stationId,
      groups.map((group) => ({ ...group })),
    );
  }

  /** What the stop shows while its refresh fails: the departures still to come. */
  stale(stationId: string, now: Date = new Date()): GroupedDepartures[] {
    const remembered = this.byStation.get(stationId) ?? [];

    return remembered
      .map((group) => ({
        ...group,
        refreshFailed: true,
        departures: group.departures.filter(
          (departure) => departure.time >= now,
        ),
      }))
      .filter((group) => group.departures.length > 0);
  }
}
