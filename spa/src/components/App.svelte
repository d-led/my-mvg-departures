<script lang="ts">
  import { onMount, tick } from "svelte";
  import { ConfigParser } from "../adapters/config/config-parser.js";
  import { CompositeDepartureRepository } from "../adapters/composite-departure-repository.js";
  import { MvgStationRepository } from "../adapters/mvg/mvg-station-repository.js";
  import { LocalStorageCache } from "../adapters/storage/local-storage-cache.js";
  import { LocalStorageConfigStorage } from "../adapters/storage/local-storage-config-storage.js";
  import { DepartureGroupingService } from "../application/services/departure-grouping-service.js";
  import { MultiStopPoller } from "../application/services/multi-stop-poller.js";
  import { OnTheRunPoller } from "../application/services/on-the-run-poller.js";
  import type { AppConfig, RouteConfiguration, GroupedDepartures, OnTheRunConfiguration } from "../domain/models/index.js";
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
  type Poller = {
    start: () => Promise<void>;
    stop: () => void;
    refreshNow: () => Promise<void>;
  };
  // eslint-disable-next-line svelte/prefer-svelte-reactivity -- Set is reactive in Svelte 5 with proper usage
  let activePollers = new Set<Poller>(); // Track all active pollers
  let unsupportedProviders = $state<string[]>([]);
  let isPageSuspended = $state<boolean>(false);
  let onTheRunConfig = $state<OnTheRunConfiguration | null>(null);
  let onTheRunPoller = $state<OnTheRunPoller | null>(null);
  let onTheRunStatusMessages = $state<string[]>([]);
  const ON_THE_RUN_ROUTE = "on-the-run";

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
  const mvgStationRepository = new MvgStationRepository();
  // departureRepository will be created per route based on stop configs
  let departureRepository: CompositeDepartureRepository | null = null;
  let groupingService: DepartureGroupingService | null = null;

  // Initialize all - matches Python version's initializeAll() function
  function initializeAll() {
    // Initialize time format toggle
    if (currentRoute?.display?.timeFormatToggleSeconds !== undefined) {
      initTimeFormatToggle(currentRoute.display.timeFormatToggleSeconds);
    }
    
    // Calculate dynamic font sizes if fill_vertical_space is enabled
    // This matches Python: if (window.DEPARTURES_CONFIG && window.DEPARTURES_CONFIG.fillVerticalSpace) { requestAnimationFrame(() => { calculateFillVerticalSpace(); }); }
    if (currentRoute?.display?.fillVerticalSpace && groupedDepartures.length > 0) {
      // Note: This is called from within requestAnimationFrame already, so we can call directly
      // The outer requestAnimationFrame ensures DOM is ready
      calculateFillVerticalSpace({
        fillVerticalSpace: true,
        fontScalingFactorWhenFilling: currentRoute?.display?.fontScalingFactorWhenFilling ?? 1.0,
      });
      // Wait for layout to complete after font scaling (matches Python view pattern)
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          initDestinationScrolling();
        });
      });
    } else if (!currentRoute?.display?.fillVerticalSpace && groupedDepartures.length > 0) {
      // When fillVerticalSpace is disabled, still set font sizes from config to prevent overlap
      // Note: This is called from within requestAnimationFrame already, so we can call directly
      // The outer requestAnimationFrame ensures DOM is ready
      setFontSizesFromConfig(currentRoute?.display);
      // Wait for layout to complete after font size changes (matches Python view pattern)
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          initDestinationScrolling();
        });
      });
    } else {
      // No font scaling, but still need to check for clipped destinations
      requestAnimationFrame(() => {
        initDestinationScrolling();
      });
    }
  }

  onMount(() => {
    let cleanupVisibility: (() => void) | undefined;
    let cleanupResize: (() => void) | undefined;
    let cleanupHash: (() => void) | undefined;

    const setup = async () => {
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
      cleanupHash = () => {
        window.removeEventListener("hashchange", handleHashChange);
      };

      // Listen for window resize to recalculate font sizes (matches Python exactly)
      // Handle window resize for fill_vertical_space (matches Python: lines 1426-1436)
      let resizeTimeout: number | null = null;
      const handleResize = () => {
        if (currentRoute?.display?.fillVerticalSpace) {
          // Debounce resize events (matches Python: 150ms)
          if (resizeTimeout) clearTimeout(resizeTimeout);
          resizeTimeout = window.setTimeout(() => {
            calculateFillVerticalSpace({
              fillVerticalSpace: true,
              fontScalingFactorWhenFilling:
                currentRoute?.display?.fontScalingFactorWhenFilling ?? 1.0,
            });
          }, 150);
        }
      };
      window.addEventListener("resize", handleResize);
      cleanupResize = () => {
        if (resizeTimeout) {
          clearTimeout(resizeTimeout);
        }
        window.removeEventListener("resize", handleResize);
      };

      // Detect when page/tab is suspended/hidden (Page Visibility API only)
      // When suspended, grey out all rows to signal staleness
      // Main use case: browser suspends tab timers when tab is hidden, data becomes stale
      async function handleVisibilityChange() {
        const wasSuspended = isPageSuspended;

        // Only set stale when page is actually hidden (tab suspended)
        // Don't set stale on focus loss - only when browser suspends timers
        if (document.hidden) {
          isPageSuspended = true;
          if (!wasSuspended) {
            console.log(
              "Page SUSPENDED (tab hidden/device sleeping) - marking data as stale",
            );
          }
        } else if (!document.hidden && wasSuspended && activePollers.size > 0) {
          // Page became visible again - force immediate refresh to get fresh data
          console.log(
            "Page VISIBLE again (tab shown/device woke up) - forcing immediate refresh",
          );
          try {
            // Refresh all active pollers
            for (const poller of activePollers) {
              await poller.refreshNow();
            }
          } catch (error) {
            console.error("Error during forced refresh:", error);
          }
        }
      }

      // Check initial state
      if (document.hidden) {
        isPageSuspended = true;
      }

      // Listen for visibility changes (Page Visibility API)
      document.addEventListener("visibilitychange", handleVisibilityChange);
      cleanupVisibility = () => {
        document.removeEventListener("visibilitychange", handleVisibilityChange);
      };
    };

    void setup();

    return () => {
      cleanupVisibility?.();
      cleanupResize?.();
      cleanupHash?.();
    };
  });

  // Recalculate font sizes after departures update
  // This matches Python's phx:update handler: requestAnimationFrame(() => { calculateFillVerticalSpace(); })
  $effect(() => {
    // Access reactive values to trigger effect (intentionally unused to trigger reactivity)
    void groupedDepartures;
    void currentRoute;

    void handleDeparturesUpdate();
  });

  async function handleDeparturesUpdate(): Promise<void> {
    if (currentRoute?.display?.fillVerticalSpace && groupedDepartures.length > 0) {
      // Wait for Svelte to finish rendering
      await tick();

      // Use requestAnimationFrame to ensure DOM is fully laid out (matches Python exactly)
      requestAnimationFrame(() => {
        console.log("Recalculating font sizes (fillVerticalSpace enabled)");
        calculateFillVerticalSpace({
          fillVerticalSpace: true,
          fontScalingFactorWhenFilling:
            currentRoute?.display?.fontScalingFactorWhenFilling ?? 1.0,
        });
        // Initialize time format toggle (will reinitialize if already running)
        initTimeFormatToggle(currentRoute?.display?.timeFormatToggleSeconds ?? 0);
        // Wait for layout to complete after font scaling (matches Python view pattern)
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            initDestinationScrolling();
          });
        });
      });
    } else if (!currentRoute?.display?.fillVerticalSpace) {
      console.log("fillVerticalSpace is disabled, setting font sizes from config");
      // When fillVerticalSpace is disabled, still set font sizes from config and ensure proper line-heights
      // This prevents font overlap (matches Python: CSS variables are always set)
      await tick();
      requestAnimationFrame(() => {
        setFontSizesFromConfig(currentRoute?.display);
        initTimeFormatToggle(currentRoute?.display?.timeFormatToggleSeconds ?? 0);
        // Wait for layout to complete after font size changes (matches Python view pattern)
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            initDestinationScrolling();
          });
        });
      });
    }
  }

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
      onTheRunConfig = stored.onTheRun ?? null;
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
    
    // Stop ALL existing pollers and clear the set
    console.log(`Stopping ${activePollers.size} active poller(s)`);
    for (const poller of activePollers) {
      poller.stop();
    }
    activePollers.clear();
    onTheRunPoller = null;
    
    // Cleanup time format toggle
    cleanupTimeFormatToggle();

    // Clear cache to prevent cross-route contamination
    // This is critical when routes share station IDs but have different configurations
    await cache.clear();
    console.log("Cache cleared when switching routes");

    // Clear existing departures and unsupported providers when switching routes
    groupedDepartures = [];
    unsupportedProviders = [];
    currentRoute = route;
    await configStorage.setCurrentRoutePath(route.path);
    onTheRunStatusMessages = [];
    
    // Update browser tab title (happens on initial load and when switching routes)
    const pageTitle = route.display?.title ?? "MVG Departures";
    document.title = pageTitle;
    console.log(`Set page title to: ${pageTitle}`);
    
    // Only update hash if explicitly requested (user navigation, not initial load)
    if (updateHash) {
      // Use hash-based routing for SPA (don't use pushState with pathname)
      // Use hash to avoid server-side routing issues
      const hash = route.path === "/" ? "" : route.path;
      window.location.hash = hash;
    }

    const isOnTheRunRoute = route.isOnTheRun ?? route.path === ON_THE_RUN_ROUTE;
    if (isOnTheRunRoute && onTheRunConfig) {
      onTheRunStatusMessages = ["Fetching location..."];
      await startOnTheRunPolling(route, onTheRunConfig);
      return;
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

      const newPoller = new MultiStopPoller(
        departureRepository,
        cache,
        groupingService,
        route.stops,
        refreshInterval,
        {
          onUpdate: async (groups, pollerId) => {
            // Only accept updates from pollers that are still in the active set
            if (!activePollers.has(newPoller)) {
              console.log(`[${pollerId}] Ignoring update from stopped poller (race condition prevented)`);
              return;
            }
            
            console.log(`[${pollerId}] Received ${groups.length} direction group(s) with ${groups.reduce((sum, g) => sum + g.departures.length, 0)} total departures`);
            groupedDepartures = groups;
            // Set status to degraded if unsupported providers, otherwise success
            apiStatus = unsupportedProviders.length > 0 ? "degraded" : "success";
            lastUpdateTime = new Date();
            
            // Clear stale state when new data arrives
            // Fresh data means staleness is resolved
            if (isPageSuspended) {
              console.log('New data received - clearing stale state');
              isPageSuspended = false;
            }
            // Wait for Svelte to update the DOM before calculating layout
            await tick();
            // Use multiple requestAnimationFrame calls + small delay to ensure DOM is fully laid out
            // This is critical for column width calculations to prevent overlap on first load
            // The delay ensures fonts are applied and layout is calculated before measuring
            requestAnimationFrame(() => {
              requestAnimationFrame(() => {
                setTimeout(() => {
                  initializeAll();
                }, 50);
              });
            });
          },
          onError: (error, pollerId) => {
            // Only accept errors from pollers that are still in the active set
            if (!activePollers.has(newPoller)) {
              console.log(`[${pollerId}] Ignoring error from stopped poller`);
              return;
            }
            console.error(`[${pollerId}] API poll error:`, error);
            apiStatus = "error";
          },
        },
        route.display // Pass route display config for header color inheritance
      );

      // Add to active pollers set BEFORE starting
      activePollers.add(newPoller);
      await newPoller.start();
      
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

  async function startOnTheRunPolling(
    route: RouteConfiguration,
    config: OnTheRunConfiguration,
  ) {
    console.log("Starting on-the-run polling");
    groupedDepartures = [];
    unsupportedProviders = [];
    onTheRunStatusMessages = ["Fetching location..."];
    apiStatus = "unknown";

    const refreshInterval = config.updateLocationIntervalSeconds ?? 20;
    refreshIntervalSeconds = refreshInterval;

    const newPoller = new OnTheRunPoller(
      mvgStationRepository,
      cache,
      config,
      {
        onUpdate: async (groups, pollerId) => {
          if (!activePollers.has(newPoller)) {
            console.log(
              `[${pollerId}] Ignoring update from stopped poller (race condition prevented)`,
            );
            return;
          }

          console.log(
            `[${pollerId}] Received ${groups.length} direction group(s) with ${groups.reduce((sum, group) => sum + group.departures.length, 0)} total departures`,
          );
          groupedDepartures = groups;
          apiStatus = unsupportedProviders.length > 0 ? "degraded" : "success";
          lastUpdateTime = new Date();

          if (isPageSuspended) {
            console.log("New data received - clearing stale state");
            isPageSuspended = false;
          }

          await tick();
          requestAnimationFrame(() => {
            requestAnimationFrame(() => {
              setTimeout(() => {
                initializeAll();
              }, 50);
            });
          });
        },
        onError: (error, pollerId) => {
          if (!activePollers.has(newPoller)) {
            console.log(`[${pollerId}] Ignoring error from stopped poller`);
            return;
          }
          console.error(`[${pollerId}] On-the-run poll error:`, error);
          apiStatus = "error";
        },
        onUnsupportedProviders: (providers) => {
          unsupportedProviders = providers;
        },
        onStatusUpdate: (messages, pollerId) => {
          if (!activePollers.has(newPoller)) {
            console.log(`[${pollerId}] Ignoring status update from stopped poller`);
            return;
          }
          onTheRunStatusMessages = messages;
        },
      },
      route.display,
    );

    onTheRunPoller = newPoller;
    activePollers.add(newPoller);
    await newPoller.start();

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        setTimeout(() => {
          initializeAll();
        }, 50);
      });
    });
  }

  async function handleConfigSave(tomlConfig: string): Promise<void> {
    // Validation is done in ConfigModal before calling this
    // But we still validate here as a safety check
    const parsed = configParser.parseToml(tomlConfig);
    
    // Store both: parsed config (for app use) and raw TOML (for editing)
    await configStorage.saveConfig(parsed);
    await configStorage.saveConfigToml(tomlConfig);
    config = parsed;
    onTheRunConfig = parsed.onTheRun ?? null;
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

  function isOnTheRunRouteActive(): boolean {
    return (
      currentRoute?.isOnTheRun === true ||
      currentRoute?.path === ON_THE_RUN_ROUTE
    );
  }

  async function handleLocationUpdateClick() {
    if (!onTheRunPoller) {
      console.warn("On-the-run poller not available");
      return;
    }
    await onTheRunPoller.refreshNow();
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
    <DeparturesList
      {groupedDepartures}
      {unsupportedProviders}
      display={currentRoute?.display}
      {isPageSuspended}
      statusMessages={isOnTheRunRouteActive() ? onTheRunStatusMessages : []}
    />
  </div>

  <StatusBar
    {apiStatus}
    onConfigClick={openConfig}
    routes={config?.routes ?? []}
    currentRoutePath={currentRoute?.path ?? null}
    onRouteChange={handleRouteChange}
    refreshIntervalSeconds={refreshIntervalSeconds}
    showLocationUpdate={Boolean(onTheRunConfig)}
    onLocationUpdateClick={handleLocationUpdateClick}
    locationUpdateDisabled={!onTheRunPoller || !isOnTheRunRouteActive()}
  />

  {#if showConfigModal}
    <ConfigModal
      onSave={handleConfigSave}
      onCancel={handleConfigCancel}
    />
  {/if}
</div>

<!-- Styles are in external CSS file: /static/css/departures.css -->
