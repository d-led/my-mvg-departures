import type {
  PollProgress,
  RetryWaitProgress,
} from "../domain/models/poll-progress.js";

/**
 * One line for the empty timetable while a cycle runs. It names the API calls
 * ("3 of 8 stops ok") because those are what make a large configuration slow.
 */
export function describeFetchProgress(progress: PollProgress): string {
  if (progress.stopsTotal === 0) {
    return "";
  }

  if (progress.stopsCompleted === 0) {
    return progress.stopsTotal === 1
      ? "Fetching departures…"
      : `Fetching ${progress.stopsTotal} stops…`;
  }

  const failed =
    progress.stopsFailed > 0 ? `, ${progress.stopsFailed} failed` : "";
  return `Fetching departures… ${progress.stopsOk} of ${progress.stopsTotal} stops ok${failed}`;
}

/** "Retrying Chiemgaustr. in 2 s (attempt 2 of 3)", or "... now ...". */
export function describeRetryWait(wait: RetryWaitProgress): string {
  return `Retrying ${wait.stationName} ${describeWhen(wait.remainingMs)} (attempt ${wait.nextAttempt} of ${wait.attempts})`;
}

function describeWhen(remainingMs: number): string {
  return remainingMs > 0 ? `in ${Math.ceil(remainingMs / 1000)} s` : "now";
}
