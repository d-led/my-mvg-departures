<script lang="ts">
  import { onMount } from "svelte";
  import { ConfigParser } from "../adapters/config/config-parser.js";
  import { MvgDepartureRepository } from "../adapters/mvg/mvg-departure-repository.js";
  import { LocalStorageCache } from "../adapters/storage/local-storage-cache.js";
  import { LocalStorageConfigStorage } from "../adapters/storage/local-storage-config-storage.js";
  import { DepartureGroupingService } from "../application/services/departure-grouping-service.js";
  import { ApiPoller } from "../application/services/api-poller.js";
  import type { AppConfig, RouteConfiguration, GroupedDepartures } from "../domain/models/index.js";
  import ConfigModal from "./ConfigModal.svelte";
  import DeparturesList from "./DeparturesList.svelte";
  import StatusBar from "./StatusBar.svelte";

  let config = $state<AppConfig | null>(null);
  let currentRoute = $state<RouteConfiguration | null>(null);
  let groupedDepartures = $state<GroupedDepartures[]>([]);
  let showConfigModal = $state(false);
  let apiStatus = $state<"success" | "error" | "degraded" | "unknown">("unknown");
  let lastUpdateTime = $state<Date | null>(null);
  let poller: ApiPoller | null = null;

  const configStorage = new LocalStorageConfigStorage();
  const configParser = new ConfigParser();
  const departureRepository = new MvgDepartureRepository();
  const cache = new LocalStorageCache();
  const groupingService = new DepartureGroupingService(departureRepository);

  onMount(async () => {
    await loadConfig();
    await initializeRoute();
  });

  async function loadConfig() {
    const stored = await configStorage.getConfig();
    if (stored) {
      config = stored;
    }
  }

  async function initializeRoute() {
    if (!config || config.routes.length === 0) {
      return;
    }

    // Get current route from URL or storage
    const path = window.location.pathname || "/";
    const storedPath = await configStorage.getCurrentRoutePath();
    const routePath = storedPath || path;

    const route = config.routes.find((r) => r.path === routePath) || config.routes[0];
    if (route) {
      await switchRoute(route);
    }
  }

  async function switchRoute(route: RouteConfiguration) {
    // Stop existing poller
    if (poller) {
      poller.stop();
      poller = null;
    }

    currentRoute = route;
    await configStorage.setCurrentRoutePath(route.path);
    window.history.pushState({}, "", route.path);

    // Start polling for all stops in route
    if (route.stops.length > 0) {
      // For now, poll the first stop (we can extend to multiple stops later)
      const stopConfig = route.stops[0];
      const refreshInterval = route.refreshIntervalSeconds ?? route.display?.refreshIntervalSeconds ?? 20;

      poller = new ApiPoller(
        departureRepository,
        cache,
        groupingService,
        stopConfig,
        refreshInterval,
        {
          onUpdate: (groups) => {
            groupedDepartures = groups;
            apiStatus = "success";
            lastUpdateTime = new Date();
          },
          onError: (error) => {
            console.error("API poll error:", error);
            apiStatus = "error";
          },
        }
      );

      await poller.start();
    }
  }

  function handleConfigSave(tomlConfig: string) {
    try {
      const parsed = configParser.parseToml(tomlConfig);
      configStorage.saveConfig(parsed).then(() => {
        config = parsed;
        showConfigModal = false;
        initializeRoute();
      });
    } catch (error) {
      console.error("Failed to parse config:", error);
      alert("Failed to parse TOML config. Please check the format.");
    }
  }

  function handleConfigCancel() {
    showConfigModal = false;
  }

  function openConfig() {
    showConfigModal = true;
  }

  function handleRouteChange(path: string) {
    if (!config) {
      return;
    }
    const route = config.routes.find((r) => r.path === path);
    if (route) {
      switchRoute(route);
    }
  }
</script>

<div class="container">
  <div class="header-section">
    <h1>{currentRoute?.display?.title ?? "MVG Departures"}</h1>
    <div class="last-update" aria-live="polite" aria-atomic="true">
      {#if lastUpdateTime}
        Last updated: {lastUpdateTime.toLocaleTimeString()}
      {/if}
    </div>
  </div>

  <div id="departures" role="region" aria-label="Departure information" aria-live="polite" aria-atomic="false">
    <DeparturesList {groupedDepartures} display={currentRoute?.display} />
  </div>

  <StatusBar
    {apiStatus}
    {showConfigModal}
    onConfigClick={openConfig}
    routes={config?.routes ?? []}
    currentRoutePath={currentRoute?.path ?? null}
    onRouteChange={handleRouteChange}
  />

  {#if showConfigModal}
    <ConfigModal
      currentConfig={config}
      onSave={handleConfigSave}
      onCancel={handleConfigCancel}
    />
  {/if}
</div>

<style>
  .container {
    width: 100vw;
    max-width: 100vw;
    height: 100vh;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    box-sizing: border-box;
  }

  .header-section {
    display: none;
  }

  h1 {
    display: none;
  }

  .last-update {
    display: none;
  }

  #departures {
    flex: 1 1 100%;
    overflow-y: auto;
    overflow-x: hidden;
    position: relative;
    width: 100%;
    height: 100%;
    box-sizing: border-box;
    padding: 0;
    margin: 0;
  }
</style>
