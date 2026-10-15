<script lang="ts">
  import type { StopFetchFailure } from "../domain/models/index.js";
  import {
    describeStopFailureDetails,
    describeStopFailures,
  } from "../utils/failure-message.js";

  let { failures = [] }: { failures?: StopFetchFailure[] } = $props();
</script>

{#if failures.length > 0}
  <div
    class="stop-failures"
    role="status"
    aria-live="polite"
    aria-atomic="true"
    title={describeStopFailureDetails(failures)}
  >
    <span class="stop-failures-icon" aria-hidden="true">⚠</span>
    <span class="stop-failures-text">{describeStopFailures(failures)}</span>
    <span class="stop-failures-hint">keeps retrying</span>
  </div>
{/if}

<style>
  .stop-failures {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.5rem;
    flex-wrap: wrap;
    padding: 0.25rem 0.75rem;
    font-size: clamp(0.9rem, 2vw, 1.3rem);
    line-height: 1.3;
    background-color: #7f1d1d;
    color: #fef2f2;
  }

  :global([data-theme="light"]) .stop-failures {
    background-color: #fee2e2;
    color: #991b1b;
  }

  :global([data-theme="dark"]) .stop-failures {
    background-color: #7f1d1d;
    color: #fef2f2;
  }

  .stop-failures-text {
    font-weight: 600;
  }

  .stop-failures-hint {
    opacity: 0.8;
  }
</style>
