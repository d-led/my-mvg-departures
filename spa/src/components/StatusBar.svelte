<script lang="ts">
  import type { RouteConfiguration } from "../domain/models/index.js";

  let {
    apiStatus,
    showConfigModal,
    onConfigClick,
    routes = [],
    currentRoutePath = null,
    onRouteChange = () => {},
  }: {
    apiStatus: "success" | "error" | "degraded" | "unknown";
    showConfigModal: boolean;
    onConfigClick: () => void;
    routes?: RouteConfiguration[];
    currentRoutePath?: string | null;
    onRouteChange?: (path: string) => void;
  } = $props();
  
  let showRouteSelector = $state(false);

  function toggleRouteSelector() {
    showRouteSelector = !showRouteSelector;
  }

  function selectRoute(path: string) {
    onRouteChange(path);
    showRouteSelector = false;
  }

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

  <button
    class="status-floating-box-item config-button"
    onclick={onConfigClick}
    aria-label="Open configuration"
    title="Open configuration"
    type="button"
  >
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true">
      <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z" />
      <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
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
  {#if routes.length > 1}
    <div class="status-floating-box-item route-selector-container">
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
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
        </svg>
      </button>
      
      {#if showRouteSelector}
        <div class="route-selector-dropdown" role="menu" aria-label="Available routes" onclick={(e) => e.stopPropagation()}>
          {#each routes as route}
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

  [data-theme="light"] .status-floating-box {
    background-color: rgba(128, 128, 128, 0.2);
  }

  [data-theme="dark"] .status-floating-box {
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
    color: inherit;
    transition: opacity 0.2s;
  }

  .config-button:hover {
    opacity: 0.8;
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

  [data-theme="light"] .refresh-countdown circle {
    stroke: rgba(0, 0, 0, 0.3);
  }

  [data-theme="light"] .refresh-countdown circle.progress {
    stroke: rgba(0, 0, 0, 0.8);
  }

  [data-theme="dark"] .refresh-countdown circle {
    stroke: rgba(255, 255, 255, 0.3);
  }

  [data-theme="dark"] .refresh-countdown circle.progress {
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
  }

  .route-selector-button {
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: inherit;
    transition: opacity 0.2s;
    width: 1em;
    height: 1em;
    min-width: 1em;
    min-height: 1em;
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

  [data-theme="dark"] .route-selector-dropdown {
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

  [data-theme="dark"] .route-selector-item {
    color: #f9fafb;
  }

  .route-selector-item:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  [data-theme="dark"] .route-selector-item:hover {
    background-color: rgba(255, 255, 255, 0.1);
  }

  .route-selector-item.active {
    background-color: rgba(8, 123, 196, 0.1);
    font-weight: 600;
  }

  [data-theme="dark"] .route-selector-item.active {
    background-color: rgba(8, 123, 196, 0.2);
  }
</style>
