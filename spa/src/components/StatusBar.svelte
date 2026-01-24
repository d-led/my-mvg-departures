<script lang="ts">
  import { onMount, onDestroy } from "svelte";
  import type { RouteConfiguration } from "../domain/models/index.js";

  let {
    apiStatus,
    onConfigClick,
    routes = [],
    currentRoutePath = null,
    onRouteChange = () => {},
    refreshIntervalSeconds = 20,
    showLocationUpdate = false,
    onLocationUpdateClick = () => {},
    locationUpdateDisabled = false,
  }: {
    apiStatus: "success" | "error" | "degraded" | "unknown";
    onConfigClick: () => void;
    routes?: RouteConfiguration[];
    currentRoutePath?: string | null;
    onRouteChange?: (path: string) => void;
    refreshIntervalSeconds?: number;
    showLocationUpdate?: boolean;
    onLocationUpdateClick?: () => void;
    locationUpdateDisabled?: boolean;
  } = $props();
  
  let showRouteSelector = $state(false);
  let countdownElapsed = $state(0);
  let countdownInterval: number | null = null;
  let countdownCircle: SVGElement | null = null;
  const radius = 5;
  const circumference = 2 * Math.PI * radius;

  function toggleRouteSelector() {
    showRouteSelector = !showRouteSelector;
  }

  function selectRoute(path: string) {
    onRouteChange(path);
    showRouteSelector = false;
  }

  function startCountdown() {
    // Clear any existing interval
    if (countdownInterval !== null) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }

    // Find the countdown circle
    const circleEl = document.querySelector(".refresh-countdown circle.progress") as SVGElement;
    if (!circleEl) {
      // Retry after a short delay if element not found
      setTimeout(startCountdown, 100);
      return;
    }
    countdownCircle = circleEl;

    // Set up the circle
    circleEl.setAttribute("stroke-dasharray", circumference.toString());
    countdownElapsed = 0;
    circleEl.setAttribute("stroke-dashoffset", "0");

    const updateInterval = 100; // Update every 100ms for smooth animation

    function updateCountdown() {
      if (!countdownCircle) return;

      countdownElapsed += updateInterval;
      const progress = countdownElapsed / (refreshIntervalSeconds * 1000);
      const offset = circumference * (1 - progress);
      countdownCircle.setAttribute("stroke-dashoffset", offset.toString());

      // Update screen reader text with remaining time
      const remainingSeconds = Math.ceil((refreshIntervalSeconds * 1000 - countdownElapsed) / 1000);
      const srText = document.getElementById("refresh-countdown-sr");
      if (srText && remainingSeconds > 0) {
        srText.textContent = `Refresh countdown: ${remainingSeconds} seconds remaining`;
      }

      // When countdown reaches the end, reset
      if (countdownElapsed >= refreshIntervalSeconds * 1000) {
        countdownElapsed = 0;
        if (srText) {
          srText.textContent = "Refresh countdown: updating";
        }
      }
    }

    countdownInterval = window.setInterval(updateCountdown, updateInterval);
  }

  onMount(() => {
    // Start countdown when component mounts
    startCountdown();
  });

  onDestroy(() => {
    // Clean up interval on component destroy
    if (countdownInterval !== null) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
  });

  // Restart countdown when refresh interval changes or when API status changes (new update)
  $effect(() => {
    // Access reactive values to trigger effect (intentionally unused to trigger reactivity)
    void refreshIntervalSeconds;
    void apiStatus;
    
    // Restart countdown when interval changes or on successful update
    if (apiStatus === "success") {
      startCountdown();
    }
  });
</script>

<svelte:window onclick={(e) => {
  const target = e.target as HTMLElement;
  if (showRouteSelector && !target.closest(".route-selector-container")) {
    showRouteSelector = false;
  }
}} />

<div class="status-floating-box" role="status" aria-label="System status indicators">
  <div class="status-floating-box-item" id="api-status-container" role="img" aria-label="API status: {apiStatus}" title="MVG API connection status">
    {#if apiStatus === "success"}
      <svg class="api-status-icon api-success" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    {:else if apiStatus === "error"}
      <svg class="api-status-icon api-error" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    {:else if apiStatus === "degraded"}
      <svg class="api-status-icon api-degraded" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
      </svg>
    {:else}
      <svg class="api-status-icon api-unknown" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true">
        <path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z" />
      </svg>
    {/if}
  </div>

  <div class="status-floating-box-item refresh-countdown" role="img" aria-label="Refresh countdown timer" title="Time until next data refresh">
    <svg viewBox="0 0 12 12" width="100%" height="100%" aria-hidden="true">
      <circle cx="6" cy="6" r="5" class="background"></circle>
      <circle cx="6" cy="6" r="5" class="progress" transform="rotate(-90 6 6)"></circle>
    </svg>
    <span class="sr-only" id="refresh-countdown-sr">Refresh countdown timer</span>
  </div>

  {#if showLocationUpdate}
    <button
      class="status-floating-box-item location-button"
      onclick={onLocationUpdateClick}
      aria-label="Update location"
      title={locationUpdateDisabled ? "Switch to Next to me to update location" : "Update location"}
      type="button"
      disabled={locationUpdateDisabled}
    >
      <svg class="location-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
        <path d="M12 2a.75.75 0 0 1 .75.75v1.81a7.45 7.45 0 0 1 6.69 6.69h1.81a.75.75 0 0 1 0 1.5h-1.81a7.45 7.45 0 0 1-6.69 6.69v1.81a.75.75 0 0 1-1.5 0v-1.81a7.45 7.45 0 0 1-6.69-6.69H2.75a.75.75 0 0 1 0-1.5h1.81a7.45 7.45 0 0 1 6.69-6.69V2.75A.75.75 0 0 1 12 2Zm0 4a6 6 0 1 0 0 12 6 6 0 0 0 0-12Zm0 3a3 3 0 1 1 0 6 3 3 0 0 1 0-6Z"/>
      </svg>
    </button>
  {/if}

  <button
    class="status-floating-box-item config-button"
    onclick={onConfigClick}
    aria-label="Open configuration"
    title="Open configuration"
    type="button"
  >
    <svg class="config-icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 15.5A3.5 3.5 0 0 1 8.5 12A3.5 3.5 0 0 1 12 8.5a3.5 3.5 0 0 1 3.5 3.5a3.5 3.5 0 0 1-3.5 3.5m7.43-2.53c.04-.32.07-.64.07-.97c0-.33-.03-.66-.07-1l2.11-1.63c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.31-.61-.22l-2.49 1c-.52-.4-1.06-.73-1.69-.98l-.37-2.65A.506.506 0 0 0 14 2h-4c-.25 0-.46.18-.5.42l-.37 2.65c-.63.25-1.17.59-1.69.98l-2.49-1c-.22-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64L4.57 11c-.04.34-.07.67-.07 1c0 .33.03.65.07.97l-2.11 1.66c-.19.15-.25.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1.01c.52.4 1.06.74 1.69.99l.37 2.65c.04.24.25.42.5.42h4c.25 0 .46-.18.5-.42l.37-2.65c.63-.26 1.17-.59 1.69-.99l2.49 1.01c.22.08.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.66Z"/>
    </svg>
  </button>

  <a
    href="https://github.com/d-led/my-mvg-departures"
    target="_blank"
    rel="noopener noreferrer"
    class="status-floating-box-github status-floating-box-item"
    aria-label="View repository on GitHub (opens in new tab)"
    title="View repository on GitHub"
  >
    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
      <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.46-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/>
    </svg>
    <span class="sr-only">View repository on GitHub</span>
  </a>
  
  <!-- Route selector (replaces presence counter) -->
  <!-- Debug: routes.length = {routes.length}, currentRoutePath = {currentRoutePath} -->
  {#if routes.length > 1}
    <div class="route-selector-container">
      <button
        class="route-selector-button"
        onclick={(e) => {
          e.stopPropagation();
          toggleRouteSelector();
        }}
        aria-label="Select view/route"
        title="Select view/route"
        type="button"
        aria-expanded={showRouteSelector}
        aria-haspopup="true"
      >
        <svg
          class="route-selector-icon"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          aria-hidden="true"
          width="18"
          height="18"
        >
          <path d="M3 6h18v2H3zM3 11h18v2H3zM3 16h18v2H3z" />
        </svg>
      </button>
      
      {#if showRouteSelector}
        <div class="route-selector-dropdown" role="menu" aria-label="Available routes" tabindex="-1">
          {#each routes as route (route.path)}
            <button
              class="route-selector-item {currentRoutePath === route.path ? 'active' : ''}"
              onclick={() => selectRoute(route.path)}
              role="menuitem"
              type="button"
            >
              {route.display?.title || route.path || "Default"}
            </button>
          {/each}
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .status-floating-box {
    position: fixed;
    bottom: 0.5rem;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.4rem 0.6rem;
    background-color: rgba(128, 128, 128, 0.3);
    backdrop-filter: blur(4px);
    border-radius: 0.4rem;
    z-index: 1000;
  }

  :global([data-theme="light"]) .status-floating-box {
    background-color: rgba(128, 128, 128, 0.2);
  }

  :global([data-theme="dark"]) .status-floating-box {
    background-color: rgba(128, 128, 128, 0.4);
  }

  .status-floating-box-item {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1em;
    height: 1em;
    min-width: 1em;
    min-height: 1em;
    flex-shrink: 0;
  }

  .config-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(0, 0, 0, 0.8);
    transition: opacity 0.2s;
    /* Override parent 1em constraint to allow larger icon */
    width: 18px;
    height: 18px;
    min-width: 18px;
    min-height: 18px;
  }

  .location-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(0, 0, 0, 0.8);
    transition: opacity 0.2s;
    width: 18px;
    height: 18px;
    min-width: 18px;
    min-height: 18px;
  }

  .location-button:disabled {
    cursor: not-allowed;
    opacity: 0.4;
  }

  :global([data-theme="dark"]) .location-button {
    color: rgba(255, 255, 255, 0.8);
  }

  .location-button:hover:not(:disabled) {
    opacity: 0.8;
  }

  .location-icon {
    width: 18px;
    height: 18px;
    display: block;
  }

  :global([data-theme="dark"]) .config-button {
    color: rgba(255, 255, 255, 0.8);
  }

  .config-button:hover {
    opacity: 0.8;
  }

  .config-icon {
    width: 18px;
    height: 18px;
    display: block;
    /* Slightly larger (18px vs 16px) to account for whitespace in viewBox */
  }

  .api-status-icon {
    width: 100%;
    height: 100%;
    display: block;
  }

  .api-status-icon.api-success {
    color: #059669;
  }

  .api-status-icon.api-error {
    color: #dc2626;
  }

  .api-status-icon.api-unknown {
    color: rgba(255, 255, 255, 0.5);
  }

  .api-status-icon.api-degraded {
    color: #d97706;
  }

  .refresh-countdown svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  .refresh-countdown circle {
    fill: none;
    stroke-width: 2;
    transition: stroke-dashoffset 0.1s linear;
  }

  :global([data-theme="light"]) .refresh-countdown circle {
    stroke: rgba(0, 0, 0, 0.3);
  }

  :global([data-theme="light"]) .refresh-countdown circle.progress {
    stroke: rgba(0, 0, 0, 0.8);
  }

  :global([data-theme="dark"]) .refresh-countdown circle {
    stroke: rgba(255, 255, 255, 0.3);
  }

  :global([data-theme="dark"]) .refresh-countdown circle.progress {
    stroke: rgba(255, 255, 255, 0.8);
  }

  .status-floating-box-github {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 1em;
    height: 1em;
    min-width: 1em;
    min-height: 1em;
    flex-shrink: 0;
    text-decoration: none;
    transition: opacity 0.2s;
  }

  .status-floating-box-github:hover {
    opacity: 0.8;
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

  .route-selector-container {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 18px !important;
    height: 18px !important;
    min-width: 18px !important;
    min-height: 18px !important;
    flex-shrink: 0;
  }

  .route-selector-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(0, 0, 0, 0.85);
    transition: opacity 0.2s;
    width: 18px;
    height: 18px;
    min-width: 18px;
    min-height: 18px;
    opacity: 0.9;
  }

  :global([data-theme="dark"]) .route-selector-button {
    color: rgba(255, 255, 255, 0.85);
  }

  .route-selector-button:hover {
    opacity: 0.8;
  }

  .route-selector-button svg {
    width: 100%;
    height: 100%;
    display: block;
  }

  .route-selector-dropdown {
    position: absolute;
    bottom: calc(100% + 0.5rem);
    right: 0;
    background: white;
    border-radius: 0.375rem;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    min-width: 150px;
    z-index: 1000;
    overflow: hidden;
  }

  :global([data-theme="dark"]) .route-selector-dropdown {
    background: #1d232a;
    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);
  }

  .route-selector-item {
    display: block;
    width: 100%;
    padding: 0.5rem 0.75rem;
    text-align: left;
    background: none;
    border: none;
    cursor: pointer;
    color: #111827;
    font-size: 0.875rem;
    transition: background-color 0.2s;
  }

  :global([data-theme="dark"]) .route-selector-item {
    color: #f9fafb;
  }

  .route-selector-item:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  :global([data-theme="dark"]) .route-selector-item:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }

  .route-selector-item.active {
    background-color: rgba(8, 123, 196, 0.1);
    font-weight: 600;
  }

  :global([data-theme="dark"]) .route-selector-item.active {
    background-color: rgba(8, 123, 196, 0.2);
  }
</style>
