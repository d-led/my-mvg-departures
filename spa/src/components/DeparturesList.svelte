<script lang="ts">
  import type { GroupedDepartures, DisplayConfiguration } from "../domain/models/index.js";

  let {
    groupedDepartures = [],
    display = undefined,
  }: {
    groupedDepartures?: GroupedDepartures[];
    display?: DisplayConfiguration;
  } = $props();

  function formatTime(departure: any): string {
    const now = new Date();
    const diffMs = departure.time.getTime() - now.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 0) {
      return "now";
    } else if (diffMinutes < 60) {
      return `${diffMinutes}m`;
    } else {
      const hours = Math.floor(diffMinutes / 60);
      const mins = diffMinutes % 60;
      return `${hours}h ${mins}m`;
    }
  }


  function getDelayMinutes(departure: any): number | null {
    if (departure.delaySeconds > 0) {
      return Math.floor(departure.delaySeconds / 60);
    }
    return null;
  }

  function getTransportTypeCss(transportType: string): string {
    const map: Record<string, string> = {
      "U-Bahn": "ubahn",
      "S-Bahn": "sbahn",
      Bus: "bus",
      Tram: "tram",
    };
    return map[transportType] || "regional";
  }
</script>

{#if groupedDepartures.length === 0}
  <div role="status" aria-live="polite" class="no-departures">
    No departures available
  </div>
{:else}
  {#each groupedDepartures as group, groupIndex (groupIndex)}
    <div class="direction-group">
      <h2 class="direction-header" role="heading" aria-level="2">
        {#if groupIndex === 0}
          <span class="direction-header-text">{group.directionName}</span>
          <div class="direction-header-time status-header-item" id="datetime-display" aria-label="Current date and time">
            {new Date().toLocaleString("de-DE")}
          </div>
        {:else}
          {group.directionName}
        {/if}
      </h2>
      <ul role="list" aria-label="Departures for {group.directionName}">
        {#each group.departures as departure (departure.line + departure.destination + departure.time.getTime())}
          <li
            class="departure-row {departure.isCancelled ? 'cancelled' : ''}"
            role="listitem"
            aria-label="{departure.transportType} {departure.line} to {departure.destination}, {formatTime(departure)}"
          >
            <div class="route-container" aria-hidden="true">
              <span class="route-number">
                <span class="route-badge route-badge-{getTransportTypeCss(departure.transportType)}">
                  {departure.line}
                </span>
              </span>
              <span class="destination">
                <span class="destination-text">{departure.destination}</span>
              </span>
            </div>
            <div class="time-container" aria-hidden="true">
              <span class="platform">{departure.platform || ""}</span>
              <span class="time {departure.delaySeconds > 0 ? 'delay' : ''} {departure.isRealtime ? 'realtime' : ''}">
                {formatTime(departure)}
                {#if getDelayMinutes(departure)}
                  <span class="delay-amount" aria-hidden="true">+{getDelayMinutes(departure)}m</span>
                {/if}
              </span>
            </div>
            <span class="sr-only">
              {departure.transportType} {departure.line} to {departure.destination}, {formatTime(departure)}
            </span>
          </li>
        {/each}
      </ul>
    </div>
  {/each}
{/if}

<style>
  .no-departures {
    width: 100%;
    text-align: center;
    font-size: var(--font-size-no-departures, 2.5rem);
    color: #9ca3af;
    padding: 2rem 0;
    font-style: italic;
  }

  .direction-group {
    width: 100%;
  }

  .direction-header {
    font-size: var(--font-size-direction-header, 2.5rem);
    font-weight: 700;
    margin: 0.5rem 0 0.25rem 0;
    padding: 0.5rem 0.75rem;
    border-bottom: 2px solid rgba(0, 0, 0, 0.2);
    opacity: 0.85;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 0.5rem;
    background-color: var(--banner-color, #087BC4);
    color: white;
  }

  .direction-header-text {
    flex: 1;
    min-width: 0;
  }

  .direction-header-time {
    flex-shrink: 0;
    margin-left: 1em;
    white-space: nowrap;
    display: flex;
    align-items: center;
    line-height: 1;
    font-size: var(--font-size-status-header, 1.875rem);
  }

  .departure-row {
    display: flex;
    align-items: center;
    padding: 0.75rem 0 0.75rem 0.75rem;
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    min-height: 4.5rem;
    width: 100%;
    box-sizing: border-box;
  }

  .departure-row.cancelled {
    opacity: 0.5;
    text-decoration: line-through;
  }

  .route-container {
    flex: 1 1 auto;
    display: grid;
    grid-template-columns: var(--route-column-width, 6.5em) 1fr;
    align-items: center;
    gap: 0.3em;
    min-width: 0;
    overflow: hidden;
    padding: 0 0.75rem 0 0;
  }

  .route-number {
    font-weight: 700;
    font-size: var(--font-size-route-number, 4rem);
    text-align: left;
    padding: 0;
    min-width: 0;
    white-space: nowrap;
    justify-self: start;
    display: flex;
    align-items: center;
    gap: 0.3em;
  }

  .route-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0.1em 0.3em;
    min-width: 1.6em;
    font-weight: 700;
    color: #fff;
    line-height: 1;
    font-size: 0.9em;
  }

  .route-badge-ubahn {
    background-color: #00508c;
    border-radius: 0.15em;
  }

  .route-badge-sbahn {
    background-color: #009551;
    border-radius: 50%;
    padding: 0.15em 0.35em;
  }

  .route-badge-bus {
    background-color: #005d79;
    border-radius: 50%;
    padding: 0.15em 0.35em;
  }

  .route-badge-tram {
    background-color: #dd0b2f;
    border-radius: 0.15em;
  }

  .route-badge-regional {
    background-color: #6b7280;
    border-radius: 0.25em;
  }

  .destination {
    overflow-x: hidden;
    overflow-y: hidden;
    white-space: nowrap;
    padding: 0;
    min-width: 0;
    font-size: var(--font-size-destination, 3.5rem);
    font-weight: 500;
    text-align: left;
    justify-self: start;
  }

  .time-container {
    flex: 0 0 auto;
    display: grid;
    grid-template-columns: var(--platform-column-width, auto) var(--time-column-width, auto);
    align-items: center;
    padding: 0 0.75rem 0 0.75rem;
    margin-right: 0;
    gap: var(--time-container-gap, 0.75rem);
    width: var(--time-container-width, auto);
  }

  .platform {
    flex: 0 0 auto;
    font-size: var(--font-size-platform, 2.5rem);
    font-weight: 400;
    text-align: left;
    padding: 0;
    white-space: nowrap;
    min-width: fit-content;
    color: #6b7280;
  }

  .time {
    text-align: right;
    font-weight: 600;
    font-size: var(--font-size-time, 4rem);
    white-space: nowrap;
    min-width: fit-content;
    overflow: hidden;
    transition: opacity 0.3s ease-in-out;
  }

  .time.delay {
    color: #d97706;
  }

  .time.realtime {
    color: #059669;
  }

  .delay-amount {
    color: #dc2626;
    font-size: var(--font-size-delay-amount, 2rem);
    font-weight: 500;
    margin-left: 0.5rem;
  }

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border-width: 0;
  }
</style>
