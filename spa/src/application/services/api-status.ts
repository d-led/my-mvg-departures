export type ApiStatus = "success" | "error" | "degraded" | "unknown";

/**
 * Mirrors the server-side poller's status rule: a cycle without failures is a
 * success, a cycle where only some stops failed is degraded, and a cycle where
 * every stop failed is an error.
 */
export function determineApiStatus(
  successCount: number,
  failureCount: number,
): ApiStatus {
  if (failureCount === 0) {
    return "success";
  }
  return successCount > 0 ? "degraded" : "error";
}
