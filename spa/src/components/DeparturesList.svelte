<script lang="ts">
  import { onMount } from "svelte";
  import type { GroupedDepartures, DisplayConfiguration } from "../domain/models/index.js";

  let {
    groupedDepartures = [],
    display = undefined,
  }: {
    groupedDepartures?: GroupedDepartures[];
    display?: DisplayConfiguration;
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

  function formatHeaderTime(departure: any): string {
    // Format time for header: "(in X+ min)" or "(in X min)"
    const now = new Date();
    const diffMs = departure.time.getTime() - now.getTime();
    const diffMinutes = Math.floor(diffMs / 60000);

    if (diffMinutes < 0) {
      return "(now)";
    } else if (diffMinutes < 60) {
      return `(in ${diffMinutes}+ min)`;
    } else {
      const hours = Math.floor(diffMinutes / 60);
      const mins = diffMinutes % 60;
      if (mins === 0) {
        return `(in ${hours}+ h)`;
      }
      return `(in ${hours}+ h ${mins}+ min)`;
    }
  }

  function getHeaderText(group: any): string {
    // Format: "StopName → DirectionName" (matches Python - no time suffix)
    // Strip "->" prefix from direction name (matches Python: direction_clean = group.direction_name.lstrip("->"))
    const directionClean = group.directionName.replace(/^->/, "");
    return `${group.stopName} → ${directionClean}`;
  }

  function getIconPath(transportType: string): string {
    // Map transport type to icon filename (matches Python template)
    if (transportType === "U-Bahn") return "ico-subway.svg";
    if (transportType === "S-Bahn") return "ico-metropolitan-railway.svg";
    if (transportType === "Tram") return "ico-tram.svg";
    return "ico-bus.svg"; // Default to bus
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

  function formatDate(date: Date): string {
    // Format date as YYYY-MM-DD (e.g., "2026-01-21")
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
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
    No departures available
  </div>
{:else}
  {#each groupedDepartures as group, groupIndex (groupIndex)}
    <div class="direction-group">
      <h2 
        class="direction-header" 
        role="heading" 
        aria-level="2"
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
      <ul role="list" aria-label="Departures for {group.directionName}">
        {#each group.departures as departure (departure.line + departure.destination + departure.time.getTime())}
          <li
            class="departure-row {departure.isCancelled ? 'cancelled' : ''}"
            role="listitem"
            aria-label="{departure.transportType} {departure.line} to {departure.destination}, {formatTimeRelative(departure)}"
          >
            <div class="route-container" aria-hidden="true">
              <span class="route-number">
                {#if getRouteIconDisplay() === "icon_with_text"}
                  <!-- icon_with_text mode: icon + route number text (default, matches Python) -->
                  <img 
                    class="route-icon" 
                    src={`/assets/${getIconPath(departure.transportType)}`}
                    alt={departure.transportType}
                    aria-hidden="true"
                  />
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
