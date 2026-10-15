import type { GroupedDepartures } from "./grouped-departures.js";
import type { StopFetchFailure } from "./stop-fetch-failure.js";

/** Outcome of one refresh cycle: what was rendered, and what failed. */
export interface PollCycleResult {
  groups: GroupedDepartures[];
  /** Stops that answered (including stops that legitimately have no departures). */
  successCount: number;
  /** Stops whose fetch failed, even after the in-cycle retries. */
  failures: StopFetchFailure[];
}
