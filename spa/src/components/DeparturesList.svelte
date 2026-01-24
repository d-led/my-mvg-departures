<script lang="ts">
  import { onMount } from "svelte";
  import type { GroupedDepartures, DisplayConfiguration } from "../domain/models/index.js";

  let {
    groupedDepartures = [],
    unsupportedProviders = [],
    display = undefined,
    isPageSuspended = false,
    statusMessages = [],
  }: {
    groupedDepartures?: GroupedDepartures[];
    unsupportedProviders?: string[];
    display?: DisplayConfiguration;
    isPageSuspended?: boolean;
    statusMessages?: string[];
  } = $props();

  function formatTimeRelative(departure: any): string {
    const now = new Date();
    const diffMs = departure.time.getTime() - now.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);

    // Match Python: format_compact_duration logic
    if (diffSeconds < 0) {
      return "now";
    }
    if (diffSeconds < 60) {
      return "<1m"; // Match Python: if total_seconds < 60, return "<1m"
    }

    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) {
      return `${diffMinutes}m`;
    }

    const hours = Math.floor(diffMinutes / 60);
    const mins = diffMinutes % 60;
    if (mins === 0) {
      return `${hours}h`;
    }
    return `${hours}h${mins}m`;
  }

  function formatTimeAbsolute(departure: any): string {
    const date = new Date(departure.time);
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${hours}:${minutes}`;
  }

  function formatPlannedTimeRelative(departure: any): string {
    if (!departure.plannedTime) {
      return formatTimeRelative(departure);
    }
    const now = new Date();
    const diffMs = departure.plannedTime.getTime() - now.getTime();
    const diffSeconds = Math.floor(diffMs / 1000);

    // Match Python: format_compact_duration logic
    if (diffSeconds < 0) {
      return "now";
    }
    if (diffSeconds < 60) {
      return "<1m"; // Match Python: if total_seconds < 60, return "<1m"
    }

    const diffMinutes = Math.floor(diffSeconds / 60);
    if (diffMinutes < 60) {
      return `${diffMinutes}m`;
    }

    const hours = Math.floor(diffMinutes / 60);
    const mins = diffMinutes % 60;
    if (mins === 0) {
      return `${hours}h`;
    }
    return `${hours}h${mins}m`;
  }

  function formatPlannedTimeAbsolute(departure: any): string {
    if (!departure.plannedTime) {
      return formatTimeAbsolute(departure);
    }
    const date = new Date(departure.plannedTime);
    const hours = date.getHours().toString().padStart(2, "0");
    const minutes = date.getMinutes().toString().padStart(2, "0");
    return `${hours}:${minutes}`;
  }

  function getDelayMinutes(departure: any): number | null {
    // Match Python version: has_delay = departure.delay_seconds is not None and departure.delay_seconds > 60
    // Only delays > 60 seconds (1 minute) are considered delays
    if (departure.delaySeconds != null && departure.delaySeconds > 60) {
      // Match Python: delay_minutes = departure.delay_seconds // 60 (integer division)
      return Math.floor(departure.delaySeconds / 60);
    }
    return null;
  }
  
  function hasDelay(departure: any): boolean {
    // Match Python: has_delay = departure.delay_seconds is not None and departure.delay_seconds > 60
    return departure.delaySeconds != null && departure.delaySeconds > 60;
  }


  function getHeaderText(group: any): string {
    // For stops without departures, header is just the stop name (matches Python template line 140: {{ stop_name }})
    if (group.departures.length === 0) {
      return group.stopName;
    }
    // Format: "StopName → DirectionName" (matches Python - no time suffix)
    // Strip "->" prefix from direction name (matches Python: direction_clean = group.direction_name.lstrip("->"))
    const directionClean = group.directionName.replace(/^->/, "").trim();
    if (!directionClean) {
      return group.stopName;
    }
    return `${group.stopName} → ${directionClean}`;
  }


  function getRouteIconDisplay(): "icon_with_text" | "badge" | "none" {
    // Default to "icon_with_text" (matches Python default)
    return display?.routeIconDisplay ?? "icon_with_text";
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


  function formatDateTime(date: Date): string {
    // Format date and time as "YYYY-MM-DD HH:MM" (matches Python: lines 150-163)
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    const hours = String(date.getHours()).padStart(2, "0");
    const minutes = String(date.getMinutes()).padStart(2, "0");
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  }

  // Update datetime every second (matches Python: setInterval(updateDateTime, 1000))
  let currentDateTime = $state(formatDateTime(new Date()));
  
  onMount(() => {
    const interval = setInterval(() => {
      currentDateTime = formatDateTime(new Date());
    }, 1000);
    
    return () => clearInterval(interval);
  });
</script>

{#if groupedDepartures.length === 0}
  <div role="status" aria-live="polite" class="no-departures">
    {#if statusMessages.length > 0}
      <div class="status-messages" aria-live="polite" aria-atomic="true">
        {#each statusMessages as message (message)}
          <div class="status-message">{message}</div>
        {/each}
      </div>
    {:else if unsupportedProviders.length > 0}
      {unsupportedProviders.join(" and ")} API provider{unsupportedProviders.length > 1 ? "s are" : " is"} not yet implemented in this version.
    {:else}
      No departures available
    {/if}
  </div>
{:else}
  {#each groupedDepartures as group, groupIndex (groupIndex)}
    <div class="direction-group">
      <h2 
        class="direction-header" 
        style={groupIndex === 0 ? undefined : (group.headerColor ? `background-color: ${group.headerColor};` : undefined)}
        data-fill-vertical-space={display?.fillVerticalSpace && groupIndex === 0 ? "true" : undefined}
      >
        {#if groupIndex === 0}
          <span class="direction-header-text">{getHeaderText(group)}</span>
          <div class="direction-header-time status-header-item" id="datetime-display" aria-label="Current date and time: {currentDateTime}">
            {currentDateTime}
          </div>
        {:else}
          {getHeaderText(group)}
        {/if}
      </h2>
      {#if group.departures.length === 0}
        <!-- Stop without departures (matches Python template lines 141-143) -->
        <div class="departure-row" role="status" aria-live="polite">
          <div class="no-departures">No departures</div>
        </div>
      {:else}
      <ul role="list" aria-label="Departures for {group.directionName}">
        {#each group.departures as departure (departure.line + departure.destination + departure.time.getTime())}
          <li
            class="departure-row {departure.isCancelled ? 'cancelled' : ''} {isPageSuspended ? 'stale' : ''}"
            role="listitem"
            aria-label="{departure.transportType} {departure.line} to {departure.destination}, {formatTimeRelative(departure)}"
          >
            <div class="route-container" aria-hidden="true">
              <span class="route-number">
                {#if getRouteIconDisplay() === "icon_with_text"}
                  <!-- icon_with_text mode: icon + route number text (default, matches Python) -->
                  {#if departure.transportType === "U-Bahn"}
                    <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 25 25" class="route-icon" aria-hidden="true"><rect fill="#00508c" width="25" height="25"/><path fill="#fff" d="M20.9,2h-5v13.1c0,2.4-.8,4.1-3.4,4.1s-3.5-1.7-3.5-4.1V2h-4.9v13.5c0,5.7,4.6,7.8,8.4,7.8s8.4-2.1,8.4-7.8V2s0,0,0,0Z"/></svg>
                  {:else if departure.transportType === "S-Bahn"}
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 31.98 31.98" class="route-icon" aria-hidden="true"><path d="M15.99,0A15.99,15.99,0,1,0,31.98,15.99,16.023,16.023,0,0,0,15.99,0" fill="#009551" fill-rule="evenodd"/><path d="M25.67,6.31c0,4.74-.04,4.66-.04,4.66C23.29,8.68,14.77,5.05,13.08,7.86c-1.99,3.31,4.32,4.53,9.48,6.29,6.15,2.1,6.06,9.19,1.58,12.61-5.93,4.52-13.23,2.38-18.69-1.71V20.16c1.3,1.52,3.44,2.52,6.47,3.61,1.72.62,6.13,1.59,7.26-.41,1.52-2.69-2.43-3.54-4.02-3.83a16.155,16.155,0,0,1-6.35-2.44c-4.64-3.07-4.42-9.04.11-12.23C14,1.27,21.12,2.52,25.67,6.31" fill="#fff" fill-rule="evenodd"/></svg>
                  {:else if departure.transportType === "Tram"}
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="route-icon" aria-hidden="true"><rect width="32" height="32" fill="#dd0b2f"/><path d="M18.9,11.8h2.01v1.38a2.719,2.719,0,0,1,2.43-1.59a1.758,1.758,0,0,1,1.13.36A2.972,2.972,0,0,1,25.24,13a2.567,2.567,0,0,1,2.38-1.41a1.847,1.847,0,0,1,1.62.79a3.47,3.47,0,0,1,.5,2.02v4.81H27.56V15.39c0-1.13-.32-1.7-.97-1.7a1,1,0,0,0-.92.68a3.158,3.158,0,0,0-.25,1.33v3.5H23.23V15.16c0-.99-.32-1.48-.96-1.48a1.013,1.013,0,0,0-.94.76a3.694,3.694,0,0,0-.24,1.4V19.2H18.9V11.8m-3.73,4.06a1.611,1.611,0,0,0-.87.23a1.005,1.005,0,0,0-.19,1.53.829.829,0,0,0,.62.25a1.107,1.107,0,0,0,.99-.6a2.53,2.53,0,0,0,.32-1.3l-.01-.04C15.54,15.88,15.25,15.86,15.17,15.86Zm.84-1.28v-.21a1.018,1.018,0,0,0-.51-.89a1.785,1.785,0,0,0-.95-.28a5.384,5.384,0,0,0-1.91.57V12.1a5.613,5.613,0,0,1,2.38-.47q3.045,0,3.04,3.19v4.4H16.18V18.09a4.924,4.924,0,0,1-.94,1a2.094,2.094,0,0,1-1.24.32a2.081,2.081,0,0,1-1.6-.71a2.6,2.6,0,0,1-.64-1.83a2,2,0,0,1,1.58-2.07A10.788,10.788,0,0,1,16.01,14.58ZM9.13,11.8l.06,1.51a3.412,3.412,0,0,1,.68-1.18a1.556,1.556,0,0,1,1.14-.42c.09,0,.32.03.69.07l-.05,2.18a2.9,2.9,0,0,0-.79-.1c-1,0-1.5.77-1.5,2.3v3.07H7.17V13.7c0-.31-.02-.95-.06-1.91H9.13ZM1.3,9.37H7.71v1.97H5.66V19.2H3.4V11.34H1.3Z" fill="#fff" fill-rule="evenodd"/></svg>
                  {:else}
                    <!-- Default to Bus -->
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="route-icon" aria-hidden="true"><path d="M16,0A16,16,0,1,1,0,16,16.034,16.034,0,0,1,16,0" fill="#005d79" fill-rule="evenodd"/><path d="M28.43,12.85a7.084,7.084,0,0,0-2.25-.56q-1.68,0-1.68,1.08c0,.46.39.84,1.18,1.15a10.3,10.3,0,0,1,2.21,1.02a3.178,3.178,0,0,1,1.19,2.7a3.2,3.2,0,0,1-1.33,2.8a4.846,4.846,0,0,1-2.85.78a10.854,10.854,0,0,1-3.09-.57l.23-2.38a6.584,6.584,0,0,0,2.69.7c1.08,0,1.62-.37,1.62-1.12,0-.51-.4-.93-1.19-1.27a16.466,16.466,0,0,1-2.2-1.03a2.906,2.906,0,0,1-1.19-2.49A3.1,3.1,0,0,1,23.1,10.9a4.932,4.932,0,0,1,2.83-.73a11.091,11.091,0,0,1,2.7.45l-.2,2.23M12.35,10.47h2.62v7.04a2.58,2.58,0,0,0,.4,1.52a1.476,1.476,0,0,0,1.26.62c1.03,0,1.55-.81,1.55-2.43V10.47h2.63V17.6a4.05,4.05,0,0,1-1.28,3.2a4.48,4.48,0,0,1-3.05,1.02a4.185,4.185,0,0,1-2.85-1a3.709,3.709,0,0,1-1.28-2.96Zm-4.8,9.04a1.2,1.2,0,0,0,.88-.38a1.274,1.274,0,0,0,.38-.94c0-.84-.55-1.27-1.65-1.27H6.06V19.5H7.55Zm-.53-4.57a1.771,1.771,0,0,0,1.02-.28A1.129,1.129,0,0,0,8.1,12.8a1.521,1.521,0,0,0-.93-.3H6.05v2.45h.97ZM3.47,10.45H8a3.514,3.514,0,0,1,2.13.62a2.454,2.454,0,0,1,1,2.12a3.087,3.087,0,0,1-.41,1.71a2.761,2.761,0,0,1-1.33.99a2.506,2.506,0,0,1,2.02,2.72q0,2.97-4.07,2.97H3.46V10.45Z" fill="#fff" fill-rule="evenodd"/></svg>
                  {/if}
                  <span class="route-line-text">{departure.line}</span>
                {:else if getRouteIconDisplay() === "badge"}
                  <!-- badge mode: route number in colored transport type shape -->
                  <span class="route-badge route-badge-{getTransportTypeCss(departure.transportType)}">
                    {departure.line}
                  </span>
                {:else}
                  <!-- none mode: text only -->
                  {departure.line}
                {/if}
              </span>
              <span class="destination">
                <span class="destination-text">{departure.destination}</span>
              </span>
            </div>
            <div 
              class="time-container" 
              aria-hidden="true"
              data-time-relative={display?.splitShowDelay ? formatPlannedTimeRelative(departure) : formatTimeRelative(departure)}
              data-time-absolute={display?.splitShowDelay ? formatPlannedTimeAbsolute(departure) : formatTimeAbsolute(departure)}
            >
              <span class="platform">{departure.platform || ""}</span>
              <span class="time {hasDelay(departure) ? 'delay' : ''} {departure.isRealtime ? 'realtime' : ''}">
                {#if display?.splitShowDelay}
                  <!-- splitShowDelay=true: show planned time + separate delay indicator -->
                  {formatPlannedTimeRelative(departure)}
                  {#if getDelayMinutes(departure)}
                    <span class="delay-amount" aria-hidden="true">+{getDelayMinutes(departure)}m</span>
                  {/if}
                {:else}
                  <!-- splitShowDelay=false (default): show expected time (includes delay) - NO delay indicator -->
                  {formatTimeRelative(departure)}
                {/if}
              </span>
            </div>
            <span class="sr-only">
              {departure.transportType} {departure.line} to {departure.destination}, {formatTimeRelative(departure)}
            </span>
          </li>
        {/each}
      </ul>
      {/if}
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

  .status-messages {
    display: inline-flex;
    flex-direction: column;
    gap: 0.5rem;
    font-style: normal;
    color: #6b7280;
  }

  .status-message {
    font-size: calc(var(--font-size-no-departures, 2.5rem) * 0.6);
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

  .departure-row.stale {
    opacity: 0.5;
    /* No strikethrough - just greyed out to signal staleness */
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

  .destination-text {
    display: inline-block;
    white-space: nowrap;
  }

  /* Auto-scroll animation for clipped destination text */
  @keyframes scroll-destination {
    0%,
    30% {
      transform: translateX(0);
    }
    50%,
    70% {
      transform: translateX(var(--scroll-distance, -18%));
    }
    100% {
      transform: translateX(0);
    }
  }

  .destination-text:global(.clipped) {
    animation: scroll-destination 20s ease-in-out infinite;
    will-change: transform;
  }

  /* Pause animation on interaction for better UX */
  .destination:hover .destination-text:global(.clipped),
  .destination:active .destination-text:global(.clipped),
  .departure-row:hover .destination-text:global(.clipped) {
    animation-play-state: paused;
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
