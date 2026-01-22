<script lang="ts">
  import { onMount, tick } from "svelte";
  import { ConfigParser } from "../adapters/config/config-parser.js";
  import { CompositeDepartureRepository } from "../adapters/composite-departure-repository.js";
  import { LocalStorageCache } from "../adapters/storage/local-storage-cache.js";
  import { LocalStorageConfigStorage } from "../adapters/storage/local-storage-config-storage.js";
  import { DepartureGroupingService } from "../application/services/departure-grouping-service.js";
  import { MultiStopPoller } from "../application/services/multi-stop-poller.js";
  import type { AppConfig, RouteConfiguration, GroupedDepartures } from "../domain/models/index.js";
  import { calculateFillVerticalSpace, setFontSizesFromConfig } from "../utils/font-scaling.js";
  import { initDestinationScrolling } from "../utils/destination-scrolling.js";
  import { initTimeFormatToggle, cleanupTimeFormatToggle } from "../utils/time-format-toggle.js";
  import ConfigModal from "./ConfigModal.svelte";
  import DeparturesList from "./DeparturesList.svelte";
  import StatusBar from "./StatusBar.svelte";

  let config = $state<AppConfig | null>(null);
  let currentRoute = $state<RouteConfiguration | null>(null);
  let groupedDepartures = $state<GroupedDepartures[]>([]);
  let showConfigModal = $state(false);
  let apiStatus = $state<"success" | "error" | "degraded" | "unknown">("unknown");
  let lastUpdateTime = $state<Date | null>(null);
  let refreshIntervalSeconds = $state<number>(20);
  let poller: MultiStopPoller | null = null;
  let unsupportedProviders = $state<string[]>([]);

  function formatDate(date: Date): string {
    // Format date as YYYY-MM-DD (e.g., "2026-01-21")
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
  }

  const configStorage = new LocalStorageConfigStorage();
  const configParser = new ConfigParser();
  const cache = new LocalStorageCache();
  // departureRepository will be created per route based on stop configs
  let departureRepository: CompositeDepartureRepository | null = null;
  let groupingService: DepartureGroupingService | null = null;

  // Initialize all - matches Python version's initializeAll() function
  function initializeAll() {
    // Initialize time format toggle
    if (currentRoute?.display?.timeFormatToggleSeconds !== undefined) {
      initTimeFormatToggle(currentRoute.display.timeFormatToggleSeconds);
    }
    
    // Initialize destination scrolling for clipped text
    initDestinationScrolling();
    
    // Calculate dynamic font sizes if fill_vertical_space is enabled
    // This matches Python: if (window.DEPARTURES_CONFIG && window.DEPARTURES_CONFIG.fillVerticalSpace) { requestAnimationFrame(() => { calculateFillVerticalSpace(); }); }
    if (currentRoute?.display?.fillVerticalSpace && groupedDepartures.length > 0) {
      // Use requestAnimationFrame to ensure DOM is fully rendered (matches Python exactly)
      requestAnimationFrame(() => {
        calculateFillVerticalSpace({
          fillVerticalSpace: true,
          fontScalingFactorWhenFilling: currentRoute?.display?.fontScalingFactorWhenFilling ?? 1.0,
        });
        initDestinationScrolling();
      });
    } else if (!currentRoute?.display?.fillVerticalSpace && groupedDepartures.length > 0) {
      // When fillVerticalSpace is disabled, still set font sizes from config to prevent overlap
      requestAnimationFrame(() => {
        setFontSizesFromConfig(currentRoute?.display);
        initDestinationScrolling();
      });
    }
  }

  onMount(async () => {
    await loadConfig();
    
    // Initialize CSS variables for font sizes (even if fillVerticalSpace is disabled)
    // Set default values from CSS
    const root = document.documentElement;
    if (!root.style.getPropertyValue("--font-size-route-number")) {
      // Initialize with default rem values (will be overridden by fillVerticalSpace if enabled)
      root.style.setProperty("--font-size-route-number", "4rem");
      root.style.setProperty("--font-size-destination", "4rem");
      root.style.setProperty("--font-size-platform", "2.5rem");
      root.style.setProperty("--font-size-time", "4rem");
      root.style.setProperty("--font-size-direction-header", "4rem");
      root.style.setProperty("--font-size-stop-header", "3rem");
      root.style.setProperty("--font-size-no-departures", "2.5rem");
      root.style.setProperty("--font-size-pagination-indicator", "2rem");
      root.style.setProperty("--font-size-countdown-text", "1.8rem");
      root.style.setProperty("--font-size-delay-amount", "2rem");
      root.style.setProperty("--font-size-status-header", "4rem");
    }
    
    await initializeRoute();
    
    // Listen for hash changes (hash-based routing)
    window.addEventListener("hashchange", handleHashChange);
    
    // Listen for window resize to recalculate font sizes (matches Python exactly)
    // Handle window resize for fill_vertical_space (matches Python: lines 1426-1436)
    let resizeTimeout: number | null = null;
    window.addEventListener("resize", () => {
      if (currentRoute?.display?.fillVerticalSpace) {
        // Debounce resize events (matches Python: 150ms)
        if (resizeTimeout) clearTimeout(resizeTimeout);
        resizeTimeout = window.setTimeout(() => {
          calculateFillVerticalSpace({
            fillVerticalSpace: true,
            fontScalingFactorWhenFilling: currentRoute?.display?.fontScalingFactorWhenFilling ?? 1.0,
          });
        }, 150);
      }
    });
  });

  // Recalculate font sizes after departures update
  // This matches Python's phx:update handler: requestAnimationFrame(() => { calculateFillVerticalSpace(); })
  $effect(async () => {
    // Access reactive values to trigger effect (intentionally unused to trigger reactivity)
    void groupedDepartures;
    void currentRoute;
    
    if (currentRoute?.display?.fillVerticalSpace && groupedDepartures.length > 0) {
      // Wait for Svelte to finish rendering
      await tick();
      
      // Use requestAnimationFrame to ensure DOM is fully laid out (matches Python exactly)
      requestAnimationFrame(() => {
        console.log("Recalculating font sizes (fillVerticalSpace enabled)");
        calculateFillVerticalSpace({
          fillVerticalSpace: true,
          fontScalingFactorWhenFilling: currentRoute?.display?.fontScalingFactorWhenFilling ?? 1.0,
        });
        // Also initialize destination scrolling (for clipped text)
        initDestinationScrolling();
        // Initialize time format toggle (will reinitialize if already running)
        initTimeFormatToggle(currentRoute?.display?.timeFormatToggleSeconds ?? 0);
      });
    } else if (!currentRoute?.display?.fillVerticalSpace) {
      console.log("fillVerticalSpace is disabled, setting font sizes from config");
      // When fillVerticalSpace is disabled, still set font sizes from config and ensure proper line-heights
      // This prevents font overlap (matches Python: CSS variables are always set)
      await tick();
      requestAnimationFrame(() => {
        setFontSizesFromConfig(currentRoute?.display);
        initTimeFormatToggle(currentRoute?.display?.timeFormatToggleSeconds ?? 0);
        initDestinationScrolling();
      });
    }
  });

  function handleHashChange() {
    const hash = window.location.hash.slice(1); // Remove leading #
    if (!config || config.routes.length === 0) {
      return;
    }
    const route = config.routes.find((r) => r.path === hash || (hash === "" && r.path === "/"));
    if (route) {
      switchRoute(route, false); // false = don't update hash (hash already changed)
    }
  }

  async function loadConfig() {
    // Always prefer TOML as source of truth (ensures undefined values are preserved correctly)
    // JSON serialization can lose undefined values or preserve incorrect false values
    const tomlString = await configStorage.getConfigToml();
    let stored: AppConfig | null = null;
    
    if (tomlString) {
      try {
        stored = configParser.parseToml(tomlString);
        // Save the parsed version for faster access next time (though we'll always parse from TOML)
        await configStorage.saveConfig(stored);
        console.log("Parsed TOML config (source of truth)");
      } catch (error) {
        console.error("Failed to parse stored TOML config:", error);
      }
    }
    
    // Fallback to parsed JSON only if TOML is not available
    if (!stored) {
      stored = await configStorage.getConfig();
      if (stored) {
        console.log("Loaded config from cached JSON (TOML not available)");
      }
    }
    
    // If no config found, load example config from static resources
    if (!stored) {
      try {
        // Use relative path to work with both root and subdirectory deployments
        const configPath = "./config.example.toml";
        const response = await fetch(configPath);
        if (response.ok) {
          const exampleToml = await response.text();
          stored = configParser.parseToml(exampleToml);
          // Store the example config in localStorage so it persists
          await configStorage.saveConfig(stored);
          await configStorage.saveConfigToml(exampleToml);
          console.log(`Loaded example config from ${configPath} and stored in localStorage`);
        } else {
          console.warn("Failed to fetch example config:", response.status, response.statusText);
        }
      } catch (error) {
        console.error("Failed to load example config:", error);
      }
    }
    
    if (stored) {
      config = stored;
      console.log(`Loaded config with ${stored.routes.length} route(s)`);
      stored.routes.forEach((route, idx) => {
        console.log(`  Route ${idx + 1}: path="${route.path}", ${route.stops.length} stop(s), fillVerticalSpace=${route.display?.fillVerticalSpace ?? false}`);
      });
    } else {
      console.log("No config found in localStorage and failed to load example config");
    }
  }

  async function initializeRoute() {
    if (!config || config.routes.length === 0) {
      return;
    }

    // Get current route from hash (hash-based routing for SPA)
    const hash = window.location.hash.slice(1); // Remove leading #
    
    // If hash is empty or just "/", use the first route (default) but don't change the URL
    let route: RouteConfiguration | undefined;
    if (hash === "" || hash === "/") {
      route = config.routes[0];
      // Use the route but don't set the hash - keep URL at root
      if (route) {
        await switchRoute(route, false); // false = don't update hash
      }
      return;
    } else {
      route = config.routes.find((r) => r.path === hash);
    }
    
    // Fallback to first route if not found
    if (!route) {
      route = config.routes[0];
    }
    
    if (route) {
      await switchRoute(route, true); // true = update hash (user navigated)
    }
  }

  async function switchRoute(route: RouteConfiguration, updateHash: boolean = true) {
    console.log(`Switching to route: ${route.path} (${route.stops.length} stop(s))`);
    
    // Stop existing poller and wait for it to fully stop
    if (poller) {
      poller.stop();
      poller = null;
      // Small delay to ensure interval is cleared
      await new Promise(resolve => setTimeout(resolve, 10));
    }
    
    // Cleanup time format toggle
    cleanupTimeFormatToggle();

    // Clear existing departures and unsupported providers when switching routes
    groupedDepartures = [];
    unsupportedProviders = [];
    currentRoute = route;
    await configStorage.setCurrentRoutePath(route.path);
    
    // Only update hash if explicitly requested (user navigation, not initial load)
    if (updateHash) {
      // Use hash-based routing for SPA (don't use pushState with pathname)
      // Use hash to avoid server-side routing issues
      const hash = route.path === "/" ? "" : route.path;
      window.location.hash = hash;
    }

    // Start polling for all stops in route
    if (route.stops.length > 0) {
      console.log(`Starting poller for ${route.stops.length} stop(s):`, route.stops.map(s => `${s.stationName} (${s.stationId}, api=${s.apiProvider ?? "mvg"})`));
      console.log(`Route display config:`, {
        randomHeaderColors: route.display?.randomHeaderColors,
        headerBackgroundBrightness: route.display?.headerBackgroundBrightness,
        fillVerticalSpace: route.display?.fillVerticalSpace,
        title: route.display?.title,
      });
      
      // Create composite repository that routes to correct API per stop
      // This matches the Python version's CompositeDepartureRepository behavior
      departureRepository = new CompositeDepartureRepository(route.stops);
      unsupportedProviders = departureRepository.getUnsupportedProviders();
      groupingService = new DepartureGroupingService(departureRepository);
      
      // Set API status to degraded if unsupported providers are detected
      if (unsupportedProviders.length > 0) {
        apiStatus = "degraded";
      }
      
      const refreshInterval = route.refreshIntervalSeconds ?? route.display?.refreshIntervalSeconds ?? 20;
      refreshIntervalSeconds = refreshInterval;

      poller = new MultiStopPoller(
        departureRepository,
        cache,
        groupingService,
        route.stops,
        refreshInterval,
        {
          onUpdate: async (groups) => {
            console.log(`Received ${groups.length} direction group(s) with ${groups.reduce((sum, g) => sum + g.departures.length, 0)} total departures`);
            groupedDepartures = groups;
            // Set status to degraded if unsupported providers, otherwise success
            apiStatus = unsupportedProviders.length > 0 ? "degraded" : "success";
            lastUpdateTime = new Date();
            // Wait for Svelte to update the DOM before calculating layout
            await tick();
            // Use multiple requestAnimationFrame calls to ensure DOM is fully laid out
            // This is critical for column width calculations to prevent overlap
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                initializeAll();
              });
            });
          },
          onError: (error) => {
            console.error("API poll error:", error);
            apiStatus = "error";
          },
        },
        route.display // Pass route display config for header color inheritance
      );

      await poller.start();
      
      // Call initializeAll after initial poll completes (matches Python's initializeAll on page load)
      // Use multiple requestAnimationFrame calls + small delay to ensure DOM is fully ready
      // This is critical on page reload (Ctrl+R) when DOM might be ready but layout not yet calculated
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          // Additional small delay to ensure layout is calculated (especially on page reload)
          setTimeout(() => {
            initializeAll();
          }, 50);
        });
      });
    }
  }

  async function handleConfigSave(tomlConfig: string): Promise<void> {
    // Validation is done in ConfigModal before calling this
    // But we still validate here as a safety check
    const parsed = configParser.parseToml(tomlConfig);
    
    // Store both: parsed config (for app use) and raw TOML (for editing)
    await configStorage.saveConfig(parsed);
    await configStorage.saveConfigToml(tomlConfig);
    config = parsed;
    showConfigModal = false;
    await initializeRoute();
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
      switchRoute(route, true); // true = update hash (user explicitly changed route)
    }
  }
</script>

<div class="container" class:fill-vertical-space={currentRoute?.display?.fillVerticalSpace ?? false} role="main" aria-label="MVG Departures Dashboard">
  <div class="header-section">
    <h1>{currentRoute?.display?.title ?? "MVG Departures"}</h1>
    <div class="last-update" aria-live="polite" aria-atomic="true">
      {#if lastUpdateTime}
        Last updated: {formatDate(lastUpdateTime)} {lastUpdateTime.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })}
      {/if}
    </div>
  </div>

  <div id="departures" role="region" aria-label="Departure information" aria-live="polite" aria-atomic="false">
    <DeparturesList {groupedDepartures} {unsupportedProviders} display={currentRoute?.display} />
  </div>

  <StatusBar
    {apiStatus}
    {showConfigModal}
    onConfigClick={openConfig}
    routes={config?.routes ?? []}
    currentRoutePath={currentRoute?.path ?? null}
    onRouteChange={handleRouteChange}
    refreshIntervalSeconds={refreshIntervalSeconds}
  />

  {#if showConfigModal}
    <ConfigModal
      onSave={handleConfigSave}
      onCancel={handleConfigCancel}
    />
  {/if}
</div>

<!-- Styles are in external CSS file: /static/css/departures.css -->
