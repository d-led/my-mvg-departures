<script lang="ts">
  import { onMount } from "svelte";
  import { SvelteMap, SvelteSet } from "svelte/reactivity";
  import type { WizardResult } from "../utils/config-modifier.js";

  const {
    onComplete,
    onCancel,
    existingMainStopIds,
    routeStopIdsByPath,
    onTheRunDisabled,
  } = $props();

  // Removed unused errorMessage and errorTimeout for lint compliance
  let isLoadingSubStops = $state(false);
  let searchError = $state<string | null>(null);
  let selectedCount = $state(0);
  let configTarget = $state<"main" | "route" | "current" | "">("" as any);
  let currentRoutePath = $state("");
  let newRouteTitle = $state("");
  let newRoutePath = $state("");
  let selectFullStop = $state<boolean>(false);
  let searchQuery = $state("");
  let isSearching = $state(false);
  let searchResults = $state<any[]>([]);
  // eslint-disable-next-line svelte/no-unnecessary-state-wrap -- SvelteSet needs $state wrapper for reassignments
  let selectedStops = $state(new SvelteSet<string>());
  // eslint-disable-next-line svelte/no-unnecessary-state-wrap -- SvelteMap needs $state wrapper for reassignments
  let selectedSubStops = $state(new SvelteMap<string, { id: string; title: string; platformValue?: string | number | null; platformKind?: "platform" | "stop" | null; parentStopId?: string }>());
  // eslint-disable-next-line svelte/no-unnecessary-state-wrap -- SvelteMap needs $state wrapper for reassignments
  let subStopRoutes = $state(new SvelteMap<string, any[]>());
  let currentStep = $state<"target" | "route-details" | "search" | "select" | "substops" | "configure" | "review">("target");

  function normalizeRoutePath(path: string) {
    if (!path) {
      return "";
    }
    return path.startsWith("/") ? path : `/${path}`;
  }

  function isOnTheRunRoute(path: string) {
    return path === "on-the-run" || path === "/on-the-run";
  }

  function getTargetRoutePath() {
    if (configTarget === "current") {
      return normalizeRoutePath(currentRoutePath);
    }
    if (configTarget === "route") {
      return normalizeRoutePath(newRoutePath);
    }
    return "";
  }

  function getDisabledStopIds() {
    if (configTarget === "main") {
      return new Set(existingMainStopIds);
    }

    const routePath = getTargetRoutePath();
    if (!routePath) {
      return new Set<string>();
    }

    return new Set(routeStopIdsByPath[routePath] ?? []);
  }

  function isStopDisabled(stopId: string) {
    return getDisabledStopIds().has(stopId);
  }

  onMount(() => {
    // Get current route from hash-based routing (e.g., /#/hochaeckerstrasse)
    const hash = window.location.hash;
    // Hash format: #/routename or just # for main
    if (hash.length > 1) {
      currentRoutePath = hash.substring(1); // Remove the # prefix, keep everything after
      if (currentRoutePath === "/" || currentRoutePath === "") {
        currentRoutePath = ""; // Clear if it's just the main route
      }
    }
    
    // Preselect the current route unless it's on-the-run
    if (currentRoutePath && !onTheRunDisabled && !isOnTheRunRoute(currentRoutePath)) {
      configTarget = "current";
    } else {
      configTarget = "main";
    }

    // Add global keyboard event listener
    const handleGlobalKeydown = (event: KeyboardEvent) => {
      handleKeydown(event);
    };
    
    window.addEventListener("keydown", handleGlobalKeydown);
    
    return () => {
      window.removeEventListener("keydown", handleGlobalKeydown);
    };
  });

  async function handleSearch() {
    if (!searchQuery.trim()) return;

    isSearching = true;
    searchError = null;

    try {
      // Call MVG's public API endpoint directly
      // Base: https://www.mvg.de/api/bgw-pt/v3
      // Endpoint: /locations?query=...&locationTypes=STATION
      
      const params = new globalThis.URLSearchParams({
        query: searchQuery.trim(),
        locationTypes: "STATION",
      });

      const response = await fetch(
        `https://www.mvg.de/api/bgw-pt/v3/locations?${params.toString()}`
      );
      const data = await response.json();

      if (Array.isArray(data) && data.length > 0) {
        searchResults = data.map((result: any) => {
          // Check if this result has sub-stops (physical stops)
          const subStops: any[] = [];
          if (result.children && Array.isArray(result.children)) {
            subStops.push(
              ...result.children.map((child: any) => ({
                id: child.globalId,
                name: child.name,
                place: child.place || result.place || "Munich",
                type: child.type,
                parentId: result.globalId,
              }))
            );
          }
          return {
            id: result.globalId,
            name: result.name,
            place: result.place || "Munich",
            type: result.type,
            subStops,
          };
        });

        currentStep = "select";
      } else {
        searchError = "No stops found";
      }
    } catch (error) {
      searchError =
        error instanceof Error
          ? error.message
          : "Failed to search stations";
      console.error("Search error:", error);
    } finally {
      isSearching = false;
    }
  }

  function handleSelectStop(stopId: string) {
    if (isStopDisabled(stopId)) {
      return;
    }

    if (selectedStops.has(stopId)) {
      selectedStops.delete(stopId);
    } else {
      selectedStops.add(stopId);
    }
    selectedCount = selectedStops.size;
  }

  function getDefaultSubStopTitle(
    _subStopId: string,
    platformValue?: string | number | null,
    platformKind?: "platform" | "stop" | null,
  ) {
    if (platformValue !== undefined && platformValue !== null && `${platformValue}`.trim() !== "") {
      if (platformKind === "platform") {
        return `Platform ${platformValue}`;
      }
      if (platformKind === "stop") {
        return `Stop ${platformValue}`;
      }
    }
    return "Stop";
  }

  function getSubStopTitleForDisplay(
    subStopId: string,
    title?: string,
    platformValue?: string | number | null,
    platformKind?: "platform" | "stop" | null,
  ) {
    const defaultTitle = getDefaultSubStopTitle(subStopId, platformValue, platformKind);
    if (!title) return defaultTitle;
    if (/^(stop|platform)\s+\d+$/i.test(title) && title !== defaultTitle) {
      return defaultTitle;
    }
    return title;
  }

  function handleSelectSubStop(
    subStopId: string,
    subStopName: string,
    platformValue?: string | number | null,
    platformKind?: "platform" | "stop" | null,
    parentStopId?: string,
  ) {
    if (selectedSubStops.has(subStopId)) {
      selectedSubStops.delete(subStopId);
    } else {
      // Auto-generate title from stop ID (e.g., "Stop 2" from "de:09162:1108:2:2")
      const defaultTitle = getDefaultSubStopTitle(subStopId, platformValue, platformKind);
      selectedSubStops.set(subStopId, { 
        id: subStopId, 
        title: defaultTitle,
        platformValue,
        platformKind,
        parentStopId,
      });
      
      // When selecting a sub-stop, also add its parent stop to the main selection
      // so both the parent and child are configured
      if (parentStopId && !selectedStops.has(parentStopId)) {
        selectedStops.add(parentStopId);
        selectedCount = selectedStops.size;
      }
    }
  }
  
  function updateSubStopTitle(subStopId: string, title: string) {
    const entry = selectedSubStops.get(subStopId);
    if (entry) {
      selectedSubStops.set(subStopId, { ...entry, title });
    }
  }

  async function proceedToSubStops() {
    if (selectedStops.size === 0) return;
    
    // Load route information and discover substops from departure data
    isLoadingSubStops = true;
    currentStep = "substops";
    
    try {
      const allSubStops = new SvelteMap<string, any>(); // SvelteMap of parent stop ID to its substops
      
      for (const stopId of Array.from(selectedStops)) {
        const stop = searchResults.find(r => r.id === stopId);
        if (!stop) continue;
        
        console.log('Fetching departures for:', stop.name, stopId);
        
        // Fetch departures to discover physical stops
        const subStopsData = await fetchSubStopsFromDepartures(stopId, stop.name);
        
        if (subStopsData.length > 0) {
          allSubStops.set(stopId, {
            mainStop: stop,
            subStops: subStopsData
          });
          
          // Now update the search results to include these substops
          const resultIndex = searchResults.findIndex(r => r.id === stopId);
          if (resultIndex >= 0) {
            searchResults[resultIndex] = {
              ...searchResults[resultIndex],
              subStops: subStopsData
            };
          }
        }
      }
      
      console.log('Discovered substops:', allSubStops);
      
      // Show substops step if we found any
      if (allSubStops.size > 0) {
        return;
      }
      
      // If no substops were found, skip to configuration
      console.log('No substops found, skipping to configure');
      currentStep = "configure";
      
    } catch (error) {
      console.error("Error loading substop routes:", error);
      currentStep = "configure"; // Fallback to configure on error
    } finally {
      isLoadingSubStops = false;
    }
  }

  async function fetchSubStopsFromDepartures(stopId: string, stopName: string) {
    try {
      const params = new globalThis.URLSearchParams({
        globalId: stopId,
        limit: "100",
        transportTypes: "UBAHN,TRAM,SBAHN,BUS,REGIONAL_BUS,BAHN",
      });

      const response = await fetch(
        `https://www.mvg.de/api/bgw-pt/v3/departures?${params.toString()}`,
        {
          method: "GET",
          headers: {
            "Accept": "application/json",
          },
        }
      );

      if (!response.ok) {
        console.error(`Failed to fetch departures for ${stopId}`);
        return [];
      }

      const data = await response.json();
      
      // Extract unique physical stops from departures
      const physicalStops = new SvelteMap<string, { id: string; name: string; parentId: string; platformValue: string | number | null; platformKind: "platform" | "stop" | null; routes: any[] }>();
      
      if (Array.isArray(data)) {
        for (const departure of data) {
          const physicalStopId = departure.stopPointGlobalId || stopId;
          const platformLabel =
            departure.platformName ??
            departure.platformDisplay ??
            departure.platform;
          const stopPosition = departure.stopPositionNumber;
          let platformValue: string | number | null = null;
          let platformKind: "platform" | "stop" | null = null;

          // For rail lines, use API platform/stop fields
          if (platformLabel !== undefined && platformLabel !== null && `${platformLabel}`.trim() !== "") {
            platformValue = platformLabel;
            platformKind = "platform";
          } else if (stopPosition !== undefined && stopPosition !== null && `${stopPosition}`.trim() !== "") {
            platformValue = stopPosition;
            platformKind = "stop";
          } else {
            // For bus stops without explicit platform info, extract from ID
            // Format: de:09162:1108:3:3 -> last segment is stop number
            const idParts = physicalStopId.split(":");
            if (idParts.length >= 5) {
              const stopNum = idParts[idParts.length - 1];
              if (stopNum && stopNum !== stopId.split(":").pop()) {
                platformValue = stopNum;
                platformKind = "stop";
              }
            }
          }

          const transportType = departure.transportType || departure.type;
          const lineLabel = departure.label || departure.line;
          
          if (!physicalStops.has(physicalStopId)) {
            physicalStops.set(physicalStopId, {
              id: physicalStopId,
              name: departure.stopPointName || stopName,
              parentId: stopId,
              platformValue: platformValue ?? null,
              platformKind: platformKind ?? null,
              routes: []
            });
          } else {
            // Update existing stop if we now have better platform info
            const existing = physicalStops.get(physicalStopId)!;
            if ((platformValue !== undefined && platformValue !== null && `${platformValue}`.trim() !== "") && !existing.platformValue) {
              existing.platformValue = platformValue;
              existing.platformKind = platformKind;
            }
          }
          
          // Add route info
          const stop = physicalStops.get(physicalStopId)!;
          const routeKey = `${lineLabel} ${departure.destination}`;
          
          if (!stop.routes.some((r: any) => `${r.line} ${r.destination}` === routeKey)) {
            stop.routes.push({
              line: lineLabel,
              destination: departure.destination,
              transportType,
            });
          }
        }
      }

      const subStops = Array.from(physicalStops.values());
      
      console.log(`Found ${subStops.length} physical stops with platform info:`, subStops.map(s => ({
        id: s.id,
        name: s.name,
        platformValue: s.platformValue,
        platformKind: s.platformKind,
        routes: s.routes.length
      })));
      
      // Store routes in the map
      for (const subStop of subStops) {
        subStopRoutes.set(subStop.id, subStop.routes);
      }
      
      console.log(`Found ${subStops.length} physical stops for ${stopName}:`, subStops);
      
      // Only return substops if there's more than one physical stop
      return subStops.length > 1 ? subStops : [];
      
    } catch (error) {
      console.error(`Error fetching departures for ${stopId}:`, error);
      return [];
    }
  }

  async function proceedToConfiguration() {
    if (selectedStops.size === 0) return;
    currentStep = "configure";
  }
  
  function generateDirectionMappings(): SvelteMap<string, string[]> {
    // Generate direction mappings for the main stop based on sub-stops
    // Use the actual platform/stop label from API, not the custom title
    const mappings = new SvelteMap<string, string[]>();
    
    for (const [subStopId, subStopData] of selectedSubStops.entries()) {
      const routes = subStopRoutes.get(subStopId) || [];
      const routeStrings = routes.map((r: any) => `${r.line} ${r.destination}`);
      
      if (routeStrings.length > 0) {
        // Use the auto-generated platform/stop label (Platform X, Stop Y) as the mapping key
        // This ensures routes are correctly grouped by their physical platform/stop
        const label = getDefaultSubStopTitle(
          subStopId,
          subStopData.platformValue,
          subStopData.platformKind
        );
        mappings.set(label, routeStrings);
      }
    }
    
    return mappings;
  }
  
  function resetWizard() {
    currentStep = "target";
    searchQuery = "";
    searchResults = [];
    selectedStops = new SvelteSet();
    selectedSubStops = new SvelteMap();
    subStopRoutes = new SvelteMap();
    selectFullStop = false;
    newRouteTitle = "";
    newRoutePath = "";
    selectedCount = 0;
  }


  async function handleComplete() {
    const stopsConfig: any[] = [];
    const directionMappings = generateDirectionMappings();
    
    // If configuring "on the run" (current), don't save to main config
    if (configTarget === "current") {
      console.log("Skipping 'on the run' config - not saved to main stops");
      resetWizard();
      await onComplete({ target: "main", stops: [] });
      return;
    }
    
    console.log("=== WIZARD HANDLECOMPLETE ===");
    console.log("selectFullStop:", selectFullStop);
    console.log("selectedStops:", Array.from(selectedStops));
    console.log("selectedSubStops:", Array.from(selectedSubStops.entries()));
    
    for (const stopId of Array.from(selectedStops)) {
      const stop = searchResults.find((r) => r.id === stopId);
      
      // If full stop is selected, create a main entry with direction mappings
      if (selectFullStop && directionMappings.size > 0) {
        console.log(`Adding main stop: ${stopId} with ${directionMappings.size} direction mappings`);
        stopsConfig.push({
          station_id: stopId,
          station_name: stop?.name || stopId,
          max_departures_per_stop: 4,
          max_departures_per_route: 2,
          max_hours_in_advance: 3,
          show_ungrouped: false,
          direction_mappings: Object.fromEntries(Array.from(directionMappings.entries())),
        });
      }
      
      // Add individual sub-stops that belong to this parent stop
      for (const [subStopId, subStopData] of selectedSubStops.entries()) {
        // Only add if this sub-stop belongs to the current stop (or no parent specified)
        if (subStopData.parentStopId && subStopData.parentStopId !== stopId) {
          continue;
        }
        
        // Use the actual platform/stop label as the default title (Stop X / Platform Y)
        const defaultLabel = getDefaultSubStopTitle(
          subStopId,
          subStopData.platformValue,
          subStopData.platformKind,
        );
        const displayTitle =
          subStopData.title !== defaultLabel ? subStopData.title : undefined;
        const ungroupedTitle = displayTitle ?? defaultLabel;

        console.log(
          `Adding sub-stop: ${subStopId} (parent: ${subStopData.parentStopId}) with title: "${ungroupedTitle}"`,
        );
        
        const config: any = {
          station_id: subStopId,
          station_name: stop?.name || stopId,
          max_departures_per_stop: 4,
          max_departures_per_route: 2,
          max_hours_in_advance: 3,
          show_ungrouped: true,
        };
        
        // Always set ungrouped_title so the header shows "Stop X" instead of "Other"
        config.custom_title = ungroupedTitle;
        
        stopsConfig.push(config);
      }
    }

    console.log("Final stopsConfig being sent to merge:", stopsConfig);
    const wizardResult: WizardResult = {
      target: configTarget === "main" ? "main" : "route",
      ...(configTarget !== "main" && {
        route: {
          path: getTargetRoutePath() || "/",
          title: newRouteTitle,
        },
      }),
      stops: stopsConfig,
    };
    await onComplete(wizardResult);
    resetWizard();
  }

  function handleKeydown(event: KeyboardEvent) {
    // Ignore keypresses if user is typing in an input field
    const target = event.target as HTMLElement;
    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
      // Let Enter work in the search input
      if (event.key === "Enter" && currentStep === "search" && target.classList.contains("search-input")) {
        handleSearch();
        return;
      }
      // Let Enter work in route-details inputs
      if (event.key === "Enter" && currentStep === "route-details") {
        if (newRouteTitle.trim() && newRoutePath.trim()) {
          currentStep = "search";
          event.preventDefault();
        }
        return;
      }
      return;
    }

    if (event.key === "Escape") {
      onCancel();
      return;
    }

    if (event.key === "Enter") {
      // Handle Enter key to proceed to next step
      if (currentStep === "target") {
        if (configTarget === "route") {
          currentStep = "route-details";
        } else if (configTarget) {
          currentStep = "search";
        }
      } else if (currentStep === "route-details") {
        if (newRouteTitle.trim() && newRoutePath.trim()) {
          currentStep = "search";
        }
      } else if (currentStep === "search") {
        if (!isSearching && searchQuery.trim()) {
          handleSearch();
        }
      } else if (currentStep === "select") {
        if (selectedCount > 0) {
          proceedToSubStops();
        }
      } else if (currentStep === "substops") {
        if (!isLoadingSubStops) {
          proceedToConfiguration();
        }
      } else if (currentStep === "configure") {
        handleComplete();
      }
      event.preventDefault();
    }
  }
</script>

<div
  class="wizard-overlay"
  onclick={(event) => {
    if (event.target === event.currentTarget) {
      onCancel();
    }
  }}
  onkeydown={handleKeydown}
  role="button"
  tabindex="0"
  aria-label="Close wizard dialog"
>
  <div class="wizard-content">
    <div class="wizard-header">
      <h2>Configuration Wizard</h2>
      <button class="close-button" onclick={onCancel} aria-label="Close">×</button>
    </div>

    <div class="wizard-body">
      {#if currentStep === "target"}
        <div class="step-content">
          <p>Routes let you have different views.</p>
          <p>Choose whether to set up your main departures board or a route:</p>

          <div class="target-options">
            <button
              class="target-button"
              class:active={configTarget === "main"}
              onclick={() => (configTarget = "main")}
            >
              <div class="target-icon-main">🏠</div>
              <div class="target-text">
                <strong>Main</strong>
                <span>Your main departures board</span>
              </div>
            </button>
            {#if currentRoutePath}
              <button
                class="target-button"
                class:active={configTarget === "current"}
                onclick={() => (configTarget = "current")}
              >
                <div class="target-icon-current">{currentRoutePath.replace(/^\//, "")}</div>
                <div class="target-text">
                  <strong>Current Route</strong>
                  <span>Update this route's config</span>
                </div>
              </button>
            {/if}
            <button
              class="target-button target-button-new"
              class:active={configTarget === "route"}
              onclick={() => (configTarget = "route")}
            >
              <div class="target-icon-new">+</div>
              <div class="target-text">
                <strong>New Route</strong>
                <span>Create a separate route</span>
              </div>
            </button>
          </div>
        </div>
      {:else if currentStep === "route-details"}
        <div class="step-content">
          <h3>New Route Details</h3>
          <p>Provide a title and URL path for your new route:</p>

          <div class="route-form">
            <div class="form-field">
              <label for="route-title">Route Title</label>
              <input
                id="route-title"
                type="text"
                placeholder="e.g., Ostbahnhof Departures"
                bind:value={newRouteTitle}
                class="form-input"
              />
              <span class="field-hint">This will be displayed as the page title</span>
            </div>

            <div class="form-field">
              <label for="route-path">Route Path</label>
              <div class="path-input-wrapper">
                <span class="path-prefix">/</span>
                <input
                  id="route-path"
                  type="text"
                  placeholder="e.g., hochaeckerstrasse"
                  bind:value={newRoutePath}
                  class="form-input path-input"
                  oninput={(e) => {
                    // Auto-sanitize: lowercase, replace spaces with hyphens, remove special chars
                    const input = e.currentTarget as globalThis.HTMLInputElement;
                    input.value = input.value
                      .toLowerCase()
                      .replace(/\s+/g, '-')
                      .replace(/[^a-z0-9-]/g, '');
                    newRoutePath = input.value;
                  }}
                />
              </div>
              <span class="field-hint">URL slug (lowercase, hyphens only). Full URL: /#/{newRoutePath || 'yourpath'}</span>
            </div>
          </div>
        </div>
      {:else if currentStep === "search"}
        <div class="step-content">
          <h3>Step 1: Search for Stops</h3>
          <p>Search for a transit stop by name:</p>

          <div class="search-container">
            <input
              type="text"
              placeholder="e.g., Giesing München"
              bind:value={searchQuery}
              onkeydown={(e) => {
                if (e.key === "Enter") handleSearch();
              }}
              disabled={isSearching}
              class="search-input"
            />
            <button
              onclick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
              class="search-button"
            >
              {isSearching ? "Searching..." : "Search"}
            </button>
          </div>

          {#if searchError}
            <div class="error-message" role="alert">
              {searchError}
            </div>
          {/if}

          {#if searchResults.length > 0}
            <div class="results-list">
              <p class="results-count">Found {searchResults.length} stop(s):</p>
              {#each searchResults as result (result.id)}
                <div class="result-item">
                  <span class="result-info">
                    <strong>{result.name}</strong>
                    {#if result.place}
                      <span class="result-place"> • {result.place}</span>
                    {/if}
                  </span>
                  <span class="result-id">{result.id}</span>
                </div>
              {/each}
            </div>
          {/if}
        </div>
      {:else if currentStep === "select"}
        <div class="step-content">
          <h3>Step 2: Select Stops</h3>
          <p>Select which stops you want to configure.</p>
          <p>You will be able to select physical stops in the next step.</p>

          <div class="stops-checklist">
            {#each searchResults as stop (stop.id)}
              <label class="checkbox-item" class:disabled={isStopDisabled(stop.id)}>
                <input
                  type="checkbox"
                  checked={selectedStops.has(stop.id)}
                  disabled={isStopDisabled(stop.id)}
                  onchange={() => handleSelectStop(stop.id)}
                />
                <span class="checkbox-label">
                  <strong>{stop.name}</strong>
                  <span class="stop-meta">
                    {#if stop.place}
                      <span class="stop-place">{stop.place}</span>
                    {/if}
                    <span class="stop-id">{stop.id}</span>
                  </span>
                </span>
              </label>
            {/each}
          </div>
        </div>
      {:else if currentStep === "substops"}
        <div class="step-content">
          <h3>Step 2b: Configure Physical Stops</h3>
          <p>Choose which platforms to monitor and set custom names:</p>

          {#if isLoadingSubStops}
            <div class="loading-indicator">Loading route information...</div>
          {:else}
            <div class="substops-context">
              {#each Array.from(selectedStops) as stopId (stopId)}
                {@const mainStop = searchResults.find((s) => s.id === stopId)}
                {#if mainStop}
                  <div class="context-item">
                    <strong>{mainStop.name}</strong> ({mainStop.id})
                  </div>
                {/if}
              {/each}
            </div>
            
            <div class="substops-list">
              {#each Array.from(selectedStops) as stopId (stopId)}
                {@const mainStop = searchResults.find((s) => s.id === stopId)}
                {#if mainStop && mainStop.subStops && mainStop.subStops.length > 0}
                  <div class="substop-group">
                    <h4 class="substop-group-title">{mainStop.name}</h4>
                    
                    <label class="full-stop-checkbox">
                      <input
                        type="checkbox"
                        checked={selectFullStop}
                        onchange={(e) => (selectFullStop = e.currentTarget.checked)}
                      />
                      <span>Select full stop (with route mappings)</span>
                    </label>
                    
                    <div class="substop-options">
                      {#each mainStop.subStops as subStop (subStop.id)}
                        {@const routes = subStopRoutes.get(subStop.id) || []}
                        {@const isSelected = selectedSubStops.has(subStop.id)}
                        {@const subStopData = selectedSubStops.get(subStop.id)}
                        <div class="substop-card" class:selected={isSelected}>
                          <label class="substop-checkbox-label">
                            <input
                              type="checkbox"
                              checked={isSelected}
                              onchange={() => handleSelectSubStop(subStop.id, subStop.name, subStop.platformValue, subStop.platformKind, stopId)}
                            />
                            <span class="substop-info">
                              <span class="substop-name">
                                {subStop.name} ({getSubStopTitleForDisplay(subStop.id, subStopData?.title, subStop.platformValue, subStop.platformKind)})
                              </span>
                              <span class="substop-id">{subStop.id}</span>
                            </span>
                          </label>
                          
                          {#if isSelected}
                            <div class="substop-title-input">
                              <label for="title-{subStop.id}">Title:</label>
                              <input
                                id="title-{subStop.id}"
                                type="text"
                                value={subStopData?.title || ""}
                                placeholder="e.g., Stop 2, Towards Giesing"
                                onchange={(e) => updateSubStopTitle(subStop.id, e.currentTarget.value)}
                              />
                            </div>
                          {/if}
                          
                          {#if routes.length > 0}
                            <div class="substop-routes">
                              <span class="routes-label">Routes:</span>
                              <div class="route-list">
                                {#each routes as route (route.line + route.destination)}
                                  <div class="route-row" title="{route.line} → {route.destination}">
                                    <span class="route-number">
                                      {#if route.transportType === "UBAHN"}
                                        <svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="0 0 25 25" class="route-icon" aria-hidden="true"><rect fill="#00508c" width="25" height="25"/><path fill="#fff" d="M20.9,2h-5v13.1c0,2.4-.8,4.1-3.4,4.1s-3.5-1.7-3.5-4.1V2h-4.9v13.5c0,5.7,4.6,7.8,8.4,7.8s8.4-2.1,8.4-7.8V2s0,0,0,0Z"/></svg>
                                      {:else if route.transportType === "SBAHN"}
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 31.98 31.98" class="route-icon" aria-hidden="true"><path d="M15.99,0A15.99,15.99,0,1,0,31.98,15.99,16.023,16.023,0,0,0,15.99,0" fill="#009551" fill-rule="evenodd"/><path d="M25.67,6.31c0,4.74-.04,4.66-.04,4.66C23.29,8.68,14.77,5.05,13.08,7.86c-1.99,3.31,4.32,4.53,9.48,6.29,6.15,2.1,6.06,9.19,1.58,12.61-5.93,4.52-13.23,2.38-18.69-1.71V20.16c1.3,1.52,3.44,2.52,6.47,3.61,1.72.62,6.13,1.59,7.26-.41,1.52-2.69-2.43-3.54-4.02-3.83a16.155,16.155,0,0,1-6.35-2.44c-4.64-3.07-4.42-9.04.11-12.23C14,1.27,21.12,2.52,25.67,6.31" fill="#fff" fill-rule="evenodd"/></svg>
                                      {:else if route.transportType === "TRAM"}
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="route-icon" aria-hidden="true"><rect width="32" height="32" fill="#dd0b2f"/><path d="M18.9,11.8h2.01v1.38a2.719,2.719,0,0,1,2.43-1.59a1.758,1.758,0,0,1,1.13.36A2.972,2.972,0,0,1,25.24,13a2.567,2.567,0,0,1,2.38-1.41a1.847,1.847,0,0,1,1.62.79a3.47,3.47,0,0,1,.5,2.02v4.81H27.56V15.39c0-1.13-.32-1.7-.97-1.7a1,1,0,0,0-.92.68a3.158,3.158,0,0,0-.25,1.33v3.5H23.23V15.16c0-.99-.32-1.48-.96-1.48a1.013,1.013,0,0,0-.94.76a3.694,3.694,0,0,0-.24,1.4V19.2H18.9V11.8m-3.73,4.06a1.611,1.611,0,0,0-.87.23a1.005,1.005,0,0,0-.19,1.53.829.829,0,0,0,.62.25a1.107,1.107,0,0,0,.99-.6a2.53,2.53,0,0,0,.32-1.3l-.01-.04C15.54,15.88,15.25,15.86,15.17,15.86Zm.84-1.28v-.21a1.018,1.018,0,0,0-.51-.89a1.785,1.785,0,0,0-.95-.28a5.384,5.384,0,0,0-1.91.57V12.1a5.613,5.613,0,0,1,2.38-.47q3.045,0,3.04,3.19v4.4H16.18V18.09a4.924,4.924,0,0,1-.94,1a2.094,2.094,0,0,1-1.24.32a2.081,2.081,0,0,1-1.6-.71a2.6,2.6,0,0,1-.64-1.83a2,2,0,0,1,1.58-2.07A10.788,10.788,0,0,1,16.01,14.58ZM9.13,11.8l.06,1.51a3.412,3.412,0,0,1,.68-1.18a1.556,1.556,0,0,1,1.14-.42c.09,0,.32.03.69.07l-.05,2.18a2.9,2.9,0,0,0-.79-.1c-1,0-1.5.77-1.5,2.3v3.07H7.17V13.7c0-.31-.02-.95-.06-1.91H9.13ZM1.3,9.37H7.71v1.97H5.66V19.2H3.4V11.34H1.3Z" fill="#fff" fill-rule="evenodd"/></svg>
                                      {:else}
                                        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32" class="route-icon" aria-hidden="true"><path d="M16,0A16,16,0,1,1,0,16,16.034,16.034,0,0,1,16,0" fill="#005d79" fill-rule="evenodd"/><path d="M28.43,12.85a7.084,7.084,0,0,0-2.25-.56q-1.68,0-1.68,1.08c0,.46.39.84,1.18,1.15a10.3,10.3,0,0,1,2.21,1.02a3.178,3.178,0,0,1,1.19,2.7a3.2,3.2,0,0,1-1.33,2.8a4.846,4.846,0,0,1-2.85.78a10.854,10.854,0,0,1-3.09-.57l.23-2.38a6.584,6.584,0,0,0,2.69.7c1.08,0,1.62-.37,1.62-1.12,0-.51-.4-.93-1.19-1.27a16.466,16.466,0,0,1-2.2-1.03a2.906,2.906,0,0,1-1.19-2.49A3.1,3.1,0,0,1,23.1,10.9a4.932,4.932,0,0,1,2.83-.73a11.091,11.091,0,0,1,2.7.45l-.2,2.23M12.35,10.47h2.62v7.04a2.58,2.58,0,0,0,.4,1.52a1.476,1.476,0,0,0,1.26.62c1.03,0,1.55-.81,1.55-2.43V10.47h2.63V17.6a4.05,4.05,0,0,1-1.28,3.2a4.48,4.48,0,0,1-3.05,1.02a4.185,4.185,0,0,1-2.85-1a3.709,3.709,0,0,1-1.28-2.96Zm-4.8,9.04a1.2,1.2,0,0,0,.88-.38a1.274,1.274,0,0,0,.38-.94c0-.84-.55-1.27-1.65-1.27H6.06V19.5H7.55Zm-.53-4.57a1.771,1.771,0,0,0,1.02-.28A1.129,1.129,0,0,0,8.1,12.8a1.521,1.521,0,0,0-.93-.3H6.05v2.45h.97ZM3.47,10.45H8a3.514,3.514,0,0,1,2.13.62a2.454,2.454,0,0,1,1,2.12a3.087,3.087,0,0,1-.41,1.71a2.761,2.761,0,0,1-1.33.99a2.506,2.506,0,0,1,2.02,2.72q0,2.97-4.07,2.97H3.46V10.45Z" fill="#fff" fill-rule="evenodd"/></svg>
                                      {/if}
                                      <span class="route-line-text">{route.line}</span>
                                    </span>
                                    <span class="route-dest">{route.destination}</span>
                                  </div>
                                {/each}
                              </div>
                            </div>
                          {:else}
                            <div class="substop-routes">
                              <span class="no-routes">No route info available</span>
                            </div>
                          {/if}
                        </div>
                      {/each}
                    </div>
                  </div>
                {/if}
              {/each}
            </div>
            
            {#if selectedSubStops.size === 0 && !selectFullStop}
              <p class="info-text">
                💡 If no substops are selected, the main stop will show all routes from all platforms
              </p>
            {/if}
          {/if}
        </div>
      {:else if currentStep === "configure"}
        <div class="step-content">
          <h3>Step 3: Review Configuration</h3>
          <p>Selected stops and their configuration:</p>

          <div class="config-preview">
            {#if selectFullStop}
              {#each Array.from(selectedStops) as stopId (stopId)}
                {@const stop = searchResults.find((s) => s.id === stopId)}
                <div class="config-item">
                  <h4>{stop?.name} (Full Stop)</h4>
                  <div class="config-fields">
                    <div class="field">
                      <span class="field-label">Station ID:</span>
                      <code>{stopId}</code>
                    </div>
                    <div class="field">
                      <span class="field-label">Show ungrouped:</span>
                      <span>false</span>
                    </div>
                    <div class="field">
                      <span class="field-label">Direction mappings:</span>
                      <div class="mappings-preview">
                        {#each Array.from(selectedSubStops.entries()) as [subStopId, subStopData] (subStopId)}
                          <div class="mapping-item">
                            <strong>"{subStopData.title}"</strong>
                            <div class="mapping-routes">
                              {#each subStopRoutes.get(subStopId) || [] as route (route.line)}
                                <span class="route-chip-small">{route.line}</span>
                              {/each}
                            </div>
                          </div>
                        {/each}
                      </div>
                    </div>
                  </div>
                </div>
              {/each}
            {/if}
            
            {#each Array.from(selectedSubStops.entries()) as [subStopId, subStopData] (subStopId)}
              {@const stop = searchResults.find((s) => s.id === Array.from(selectedStops)[0])}
              <div class="config-item">
                <h4>{stop?.name} - {subStopData.title}</h4>
                <div class="config-fields">
                  <div class="field">
                    <span class="field-label">Station ID:</span>
                    <code>{subStopId}</code>
                  </div>
                  <div class="field">
                    <span class="field-label">Title:</span>
                    <span>{subStopData.title}</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Show ungrouped:</span>
                    <span>true</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Max departures per stop:</span>
                    <span>4</span>
                  </div>
                  <div class="field">
                    <span class="field-label">Max departures per route:</span>
                    <span>2</span>
                  </div>
                </div>
              </div>
            {/each}
          </div>
          <p class="info-text">
            💡 You can fine-tune these settings by editing the generated TOML config
          </p>
        </div>
      {/if}
    </div>

    <div class="wizard-footer">
      {#if currentStep === "target"}
        <button class="button button-secondary" onclick={onCancel}>Cancel</button>
        <button 
          class="button button-primary" 
          onclick={() => {
            if (configTarget === "route") {
              currentStep = "route-details";
            } else {
              currentStep = "search";
            }
          }}
        >
          Next
        </button>
      {:else if currentStep === "route-details"}
        <button class="button button-secondary" onclick={() => (currentStep = "target")}>
          Back
        </button>
        <button class="button button-secondary" onclick={onCancel}>Cancel</button>
        <button
          class="button button-primary"
          onclick={() => (currentStep = "search")}
          disabled={!newRouteTitle.trim() || !newRoutePath.trim()}
        >
          Next
        </button>
      {:else if currentStep === "search"}
        <button class="button button-secondary" onclick={onCancel}>Cancel</button>
        <button
          class="button button-primary"
          onclick={handleSearch}
          disabled={isSearching || !searchQuery.trim()}
        >
          {isSearching ? "Searching..." : "Search"}
        </button>
      {:else if currentStep === "select"}
        <button class="button button-secondary" onclick={() => (currentStep = "search")}>
          Back
        </button>
        <button class="button button-secondary" onclick={onCancel}>Cancel</button>
        <button
          class="button button-primary"
          onclick={proceedToSubStops}
          disabled={selectedCount === 0}
        >
          Next ({selectedCount} selected)
        </button>
      {:else if currentStep === "substops"}
        <button class="button button-secondary" onclick={() => (currentStep = "select")}>
          Back
        </button>
        <button class="button button-secondary" onclick={onCancel}>Cancel</button>
        <button
          class="button button-primary"
          onclick={proceedToConfiguration}
        >
          Next
        </button>
      {:else if currentStep === "configure"}
        <button class="button button-secondary" onclick={() => {
          // Go back to substops if there were any, otherwise back to select
          const hasSubStops = Array.from(selectedStops)
            .some(id => {
              const stop = searchResults.find(r => r.id === id);
              return stop && stop.subStops && stop.subStops.length > 0;
            });
          currentStep = hasSubStops ? "substops" : "select";
        }}>
          Back
        </button>
        <button class="button button-secondary" onclick={onCancel}>Cancel</button>
        <button class="button button-primary" onclick={handleComplete}>
          Create Configuration
        </button>
      {/if}
    </div>
  </div>
</div>

<style>
  .wizard-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10001;
  }

  .wizard-content {
    background: white;
    border-radius: 0.5rem;
    padding: 1.5rem;
    max-width: 90vw;
    max-height: 90vh;
    min-height: 500px;
    width: 700px;
    display: flex;
    flex-direction: column;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
    overflow: hidden;
  }

  :global([data-theme="dark"]) .wizard-content {
    background: #1d232a;
    color: #f9fafb;
  }

  .wizard-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
  }

  .wizard-header h2 {
    margin: 0;
    font-size: 1.5rem;
    font-weight: 700;
  }

  .close-button {
    background: none;
    border: none;
    font-size: 2rem;
    cursor: pointer;
    padding: 0;
    width: 2rem;
    height: 2rem;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6b7280;
  }

  .close-button:hover {
    color: #111827;
  }

  :global([data-theme="dark"]) .close-button {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .close-button:hover {
    color: #f9fafb;
  }

  .wizard-body {
    flex: 1 1 auto;
    overflow-y: auto;
    margin-bottom: 1rem;
  }

  .step-content h3 {
    margin: 0 0 0.5rem 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .step-content > p {
    margin: 0 0 0.75rem 0;
    color: #6b7280;
    font-size: 0.875rem;
  }

  .target-options {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    margin-bottom: 1rem;
  }

  .target-button {
    display: flex;
    gap: 1rem;
    align-items: center;
    padding: 1rem;
    border: 2px solid #e5e7eb;
    border-radius: 0.5rem;
    background: white;
    cursor: pointer;
    transition: all 0.2s;
    text-align: left;
  }

  .target-button:hover {
    border-color: #087bc4;
    background-color: #f0f9ff;
  }

  .target-button.active {
    border-color: #087bc4;
    background-color: #dbeafe;
  }

  :global([data-theme="dark"]) .target-button {
    background: #111827;
    border-color: #374151;
  }

  :global([data-theme="dark"]) .target-button:hover {
    border-color: #60a5fa;
    background-color: #1e3a8a;
  }

  :global([data-theme="dark"]) .target-button.active {
    border-color: #60a5fa;
    background-color: #1e3a8a;
  }

  .target-icon-main {
    font-size: 2.5rem;
    flex-shrink: 0;
    line-height: 1;
  }

  .target-icon-current {
    font-size: 1.2rem;
    font-weight: bold;
    flex-shrink: 0;
    line-height: 1;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #087bc4;
    background-color: #dbeafe;
    padding: 0.5rem 0.75rem;
    border-radius: 0.375rem;
    min-width: 3rem;
    text-align: center;
  }

  :global([data-theme="dark"]) .target-icon-current {
    color: #93c5fd;
    background-color: #1e3a8a;
  }

  .target-icon-new {
    font-size: 3rem;
    flex-shrink: 0;
    line-height: 1;
    font-weight: 300;
    color: #10b981;
  }

  .target-button-new .target-icon-new {
    color: #10b981;
  }

  :global([data-theme="dark"]) .target-button-new .target-icon-new {
    color: #6ee7b7;
  }

  .target-text {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .target-text strong {
    font-size: 1rem;
  }

  .target-text span {
    font-size: 0.8rem;
    color: #6b7280;
  }

  :global([data-theme="dark"]) .target-text span {
    color: #9ca3af;
  }

  :global([data-theme="dark"]) .step-content > p {
    color: #9ca3af;
  }

  .search-container {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.75rem;
  }

  .search-input {
    flex: 1;
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 1rem;
    box-sizing: border-box;
  }

  .search-input:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  :global([data-theme="dark"]) .search-input {
    background: #111827;
    color: #f9fafb;
    border-color: #374151;
  }

  .search-button {
    padding: 0.75rem 1.5rem;
    background-color: #087bc4;
    color: white;
    border: none;
    border-radius: 0.375rem;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .search-button:hover:not(:disabled) {
    background-color: #0669a3;
  }

  .search-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .error-message {
    background-color: #fee2e2;
    border: 1px solid #fca5a5;
    border-radius: 0.375rem;
    padding: 0.75rem;
    margin-bottom: 1rem;
    color: #991b1b;
    font-size: 0.875rem;
  }

  :global([data-theme="dark"]) .error-message {
    background-color: #7f1d1d;
    border-color: #dc2626;
    color: #fca5a5;
  }

  .results-list {
    border: 1px solid #e5e7eb;
    border-radius: 0.375rem;
    overflow: hidden;
  }

  :global([data-theme="dark"]) .results-list {
    border-color: #374151;
  }

  .results-count {
    margin: 0;
    padding: 0.75rem;
    background-color: #f9fafb;
    font-size: 0.875rem;
    font-weight: 500;
  }

  :global([data-theme="dark"]) .results-count {
    background-color: #111827;
  }

  .result-item {
    padding: 0.75rem;
    border-top: 1px solid #e5e7eb;
    display: flex;
    justify-content: space-between;
    align-items: center;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .result-item:hover {
    background-color: #f3f4f6;
  }

  :global([data-theme="dark"]) .result-item {
    border-top-color: #374151;
  }

  :global([data-theme="dark"]) .result-item:hover {
    background-color: #374151;
  }

  .result-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .result-place {
    font-size: 0.875rem;
    color: #6b7280;
  }

  :global([data-theme="dark"]) .result-place {
    color: #9ca3af;
  }

  .result-id {
    font-size: 0.75rem;
    color: #9ca3af;
    font-family: monospace;
  }

  .stops-checklist {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }

  .checkbox-item {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    padding: 0.4rem 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.25rem;
    cursor: pointer;
    transition: background-color 0.2s;
    font-size: 0.875rem;
  }

  .checkbox-item:hover {
    background-color: #f9fafb;
  }

  :global([data-theme="dark"]) .checkbox-item {
    border-color: #374151;
  }

  :global([data-theme="dark"]) .checkbox-item:hover {
    background-color: #111827;
  }

  .checkbox-item input[type="checkbox"] {
    margin-top: 0.15rem;
    cursor: pointer;
    flex-shrink: 0;
  }

  .checkbox-item input[type="checkbox"]:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .checkbox-item.disabled {
    opacity: 0.6;
    pointer-events: none;
  }

  .checkbox-item.disabled .checkbox-label {
    color: var(--text-secondary, #666);
  }

  .checkbox-label {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    flex: 1;
  }

  .stop-meta {
    display: flex;
    gap: 0.5rem;
    align-items: center;
    font-size: 0.7rem;
  }

  .stop-place {
    color: #6b7280;
  }

  :global([data-theme="dark"]) .stop-place {
    color: #9ca3af;
  }

  .stop-id {
    font-family: monospace;
    color: #9ca3af;
    background-color: #f3f4f6;
    padding: 0.1rem 0.3rem;
    border-radius: 0.15rem;
  }

  :global([data-theme="dark"]) .stop-id {
    color: #d1d5db;
    background-color: #374151;
  }

  .config-preview {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .config-item {
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    padding: 1rem;
  }

  :global([data-theme="dark"]) .config-item {
    border-color: #374151;
    background-color: #111827;
  }

  .config-item h4 {
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
  }

  .config-fields {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .field {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.875rem;
  }

  .field .field-label {
    font-weight: 500;
    color: #6b7280;
  }

  :global([data-theme="dark"]) .field .field-label {
    color: #9ca3af;
  }

  .field code {
    background-color: #f3f4f6;
    padding: 0.25rem 0.5rem;
    border-radius: 0.25rem;
    font-family: monospace;
    font-size: 0.8rem;
  }

  :global([data-theme="dark"]) .field code {
    background-color: #374151;
  }

  .info-text {
    margin: 1rem 0 0 0;
    padding: 0.75rem;
    background-color: #dbeafe;
    border-radius: 0.375rem;
    font-size: 0.875rem;
    color: #1e40af;
  }

  :global([data-theme="dark"]) .info-text {
    background-color: #1e3a8a;
    color: #93c5fd;
  }

  .wizard-footer {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
    flex-shrink: 0;
    margin-top: auto;
  }

  .button {
    padding: 0.5rem 1rem;
    border-radius: 0.375rem;
    font-weight: 500;
    cursor: pointer;
    border: none;
    transition: background-color 0.2s;
  }

  .button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .button-primary {
    background-color: #087bc4;
    color: white;
  }

  .button-primary:hover:not(:disabled) {
    background-color: #0669a3;
  }

  .button-secondary {
    background-color: #e5e7eb;
    color: #111827;
  }

  .button-secondary:hover {
    background-color: #d1d5db;
  }

  :global([data-theme="dark"]) .button-secondary {
    background-color: #374151;
    color: #f9fafb;
  }

  :global([data-theme="dark"]) .button-secondary:hover {
    background-color: #4b5563;
  }

  .route-form {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }

  .form-field {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .form-field label {
    font-weight: 600;
    font-size: 0.875rem;
    color: #374151;
  }

  :global([data-theme="dark"]) .form-field label {
    color: #d1d5db;
  }

  .form-input {
    padding: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    font-size: 1rem;
    box-sizing: border-box;
    width: 100%;
  }

  .form-input:focus {
    outline: none;
    border-color: #087bc4;
    box-shadow: 0 0 0 3px rgba(8, 123, 196, 0.1);
  }

  :global([data-theme="dark"]) .form-input {
    background: #111827;
    color: #f9fafb;
    border-color: #374151;
  }

  :global([data-theme="dark"]) .form-input:focus {
    border-color: #60a5fa;
    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
  }

  .path-input-wrapper {
    display: flex;
    align-items: center;
    gap: 0;
    border: 1px solid #d1d5db;
    border-radius: 0.375rem;
    overflow: hidden;
  }

  .path-input-wrapper:focus-within {
    border-color: #087bc4;
    box-shadow: 0 0 0 3px rgba(8, 123, 196, 0.1);
  }

  :global([data-theme="dark"]) .path-input-wrapper {
    border-color: #374151;
  }

  :global([data-theme="dark"]) .path-input-wrapper:focus-within {
    border-color: #60a5fa;
    box-shadow: 0 0 0 3px rgba(96, 165, 250, 0.1);
  }

  .path-prefix {
    padding: 0.75rem 0.5rem 0.75rem 0.75rem;
    background-color: #f3f4f6;
    color: #6b7280;
    font-weight: 600;
    font-size: 1rem;
    border-right: 1px solid #d1d5db;
  }

  :global([data-theme="dark"]) .path-prefix {
    background-color: #1f2937;
    color: #9ca3af;
    border-right-color: #374151;
  }

  .path-input {
    border: none !important;
    box-shadow: none !important;
    flex: 1;
  }

  .path-input:focus {
    outline: none;
    box-shadow: none !important;
  }

  .field-hint {
    font-size: 0.75rem;
    color: #6b7280;
    font-style: italic;
  }

  :global([data-theme="dark"]) .field-hint {
    color: #9ca3af;
  }

  .loading-indicator {
    text-align: center;
    padding: 2rem;
    color: #6b7280;
    font-style: italic;
  }

  :global([data-theme="dark"]) .loading-indicator {
    color: #9ca3af;
  }

  .substops-list {
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
  }

  .substop-group {
    border: 1px solid #e5e7eb;
    border-radius: 0.5rem;
    padding: 1rem;
    background-color: #f9fafb;
  }

  :global([data-theme="dark"]) .substop-group {
    background-color: #111827;
    border-color: #374151;
  }

  .substop-group-title {
    margin: 0 0 0.75rem 0;
    font-size: 1rem;
    font-weight: 600;
    color: #111827;
  }

  :global([data-theme="dark"]) .substop-group-title {
    color: #f9fafb;
  }

  .substop-options {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .substop-card {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding: 0.75rem;
    border: 2px solid #d1d5db;
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.2s;
    background-color: white;
  }

  .substop-card:hover {
    border-color: #087bc4;
    background-color: #f0f9ff;
  }

  .substop-card.selected {
    border-color: #087bc4;
    background-color: #dbeafe;
  }

  :global([data-theme="dark"]) .substop-card {
    background-color: #1f2937;
    border-color: #374151;
  }

  :global([data-theme="dark"]) .substop-card:hover {
    border-color: #60a5fa;
    background-color: #1e3a8a;
  }

  :global([data-theme="dark"]) .substop-card.selected {
    border-color: #60a5fa;
    background-color: #1e40af;
  }

  .substop-card input[type="checkbox"] {
    margin-top: 0.25rem;
    cursor: pointer;
    flex-shrink: 0;
  }

  .substop-name {
    font-weight: 600;
    font-size: 0.875rem;
  }

  .substop-id {
    font-family: monospace;
    font-size: 0.7rem;
    color: #6b7280;
    background-color: #f3f4f6;
    padding: 0.15rem 0.4rem;
    border-radius: 0.25rem;
  }

  :global([data-theme="dark"]) .substop-id {
    color: #9ca3af;
    background-color: #374151;
  }

  .substop-routes {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .routes-label {
    font-size: 0.75rem;
    font-weight: 500;
    color: #6b7280;
  }

  :global([data-theme="dark"]) .routes-label {
    color: #9ca3af;
  }

  .route-list {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }

  .route-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
  }

  .route-number {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-weight: 700;
    color: #1f2937;
    white-space: nowrap;
  }

  :global([data-theme="dark"]) .route-number {
    color: #f3f4f6;
  }

  .route-icon {
    height: 1em;
    width: auto;
    vertical-align: middle;
    flex-shrink: 0;
  }

  .route-line-text {
    vertical-align: middle;
  }

  .route-dest {
    font-size: 0.85rem;
    color: #6b7280;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :global([data-theme="dark"]) .route-dest {
    color: #9ca3af;
  }

  .no-routes {
    font-size: 0.75rem;
    color: #9ca3af;
    font-style: italic;
  }

  .substops-context {
    padding: 0.75rem;
    background-color: #f3f4f6;
    border-left: 3px solid #087bc4;
    border-radius: 0.25rem;
    margin-bottom: 1rem;
  }

  :global([data-theme="dark"]) .substops-context {
    background-color: #111827;
    border-left-color: #60a5fa;
  }

  .context-item {
    font-size: 0.875rem;
    color: #374151;
    margin: 0.25rem 0;
  }

  :global([data-theme="dark"]) .context-item {
    color: #d1d5db;
  }

  .full-stop-checkbox {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem;
    margin-bottom: 0.75rem;
    border: 1px solid #d1d5db;
    border-radius: 0.25rem;
    cursor: pointer;
    font-weight: 500;
  }

  :global([data-theme="dark"]) .full-stop-checkbox {
    border-color: #374151;
  }

  .full-stop-checkbox input[type="checkbox"] {
    cursor: pointer;
  }

  .substop-checkbox-label {
    display: flex;
    align-items: flex-start;
    gap: 0.5rem;
    cursor: pointer;
    flex: 1;
  }

  .substop-checkbox-label input[type="checkbox"] {
    margin-top: 0.2rem;
    cursor: pointer;
    flex-shrink: 0;
  }

  .substop-info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
  }


  .substop-title-input {
    padding: 0.5rem;
    background-color: #f9fafb;
    border-radius: 0.25rem;
    margin-top: 0.5rem;
  }

  :global([data-theme="dark"]) .substop-title-input {
    background-color: #1f2937;
  }

  .substop-title-input label {
    display: block;
    font-size: 0.75rem;
    font-weight: 600;
    color: #6b7280;
    margin-bottom: 0.25rem;
  }

  :global([data-theme="dark"]) .substop-title-input label {
    color: #9ca3af;
  }

  .substop-title-input input[type="text"] {
    width: 100%;
    padding: 0.375rem 0.5rem;
    border: 1px solid #d1d5db;
    border-radius: 0.25rem;
    font-size: 0.875rem;
    background-color: white;
    color: #111827;
    box-sizing: border-box;
  }

  :global([data-theme="dark"]) .substop-title-input input[type="text"] {
    background-color: #374151;
    border-color: #4b5563;
    color: #f3f4f6;
  }

  .substop-title-input input[type="text"]:focus {
    outline: none;
    border-color: #087bc4;
    box-shadow: 0 0 0 3px rgba(8, 123, 196, 0.1);
  }

  .route-chip-small {
    display: inline-block;
    padding: 0.1rem 0.4rem;
    background-color: #dbeafe;
    color: #0c4a6e;
    font-size: 0.65rem;
    font-weight: 600;
    border-radius: 0.2rem;
    margin-right: 0.25rem;
  }

  :global([data-theme="dark"]) .route-chip-small {
    background-color: #1e3a8a;
    color: #93c5fd;
  }

  .mapping-item {
    padding: 0.5rem;
    background-color: white;
    border-left: 2px solid #087bc4;
    border-radius: 0.25rem;
    margin-bottom: 0.5rem;
  }

  :global([data-theme="dark"]) .mapping-item {
    background-color: #374151;
    border-left-color: #60a5fa;
  }

  .mapping-routes {
    margin-top: 0.25rem;
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .mappings-preview {
    margin-top: 0.5rem;
  }

</style>
