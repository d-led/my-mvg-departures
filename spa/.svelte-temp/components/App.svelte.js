import 'svelte/internal/disclose-version';

App[$.FILENAME] = 'src/components/App.svelte';

import * as $ from 'svelte/internal/client';
import { onMount, tick } from "svelte";
import { ConfigParser } from "../adapters/config/config-parser.js";
import { CompositeDepartureRepository } from "../adapters/composite-departure-repository.js";
import { LocalStorageCache } from "../adapters/storage/local-storage-cache.js";
import { LocalStorageConfigStorage } from "../adapters/storage/local-storage-config-storage.js";
import { DepartureGroupingService } from "../application/services/departure-grouping-service.js";
import { MultiStopPoller } from "../application/services/multi-stop-poller.js";
import { calculateFillVerticalSpace } from "../utils/font-scaling.js";
import { initDestinationScrolling } from "../utils/destination-scrolling.js";
import { initTimeFormatToggle, cleanupTimeFormatToggle } from "../utils/time-format-toggle.js";
import ConfigModal from "./ConfigModal.svelte";
import DeparturesList from "./DeparturesList.svelte";
import StatusBar from "./StatusBar.svelte";

var root_1 = $.add_locations($.from_html(`<div role="main" aria-label="MVG Departures Dashboard"><div class="header-section"><h1> </h1> <div class="last-update" aria-live="polite" aria-atomic="true"><!></div></div> <div id="departures" role="region" aria-label="Departure information" aria-live="polite" aria-atomic="false"><!></div> <!> <!></div>`), App[$.FILENAME], [[294, 0, [[295, 2, [[296, 4], [297, 4]]], [304, 2]]]]);

export default function App($$anchor, $$props) {
	$.check_target(new.target);
	$.push($$props, true, App);

	let config = $.tag($.state(null), 'config');
	let currentRoute = $.tag($.state(null), 'currentRoute');
	let groupedDepartures = $.tag($.state($.proxy([])), 'groupedDepartures');
	let showConfigModal = $.tag($.state(false), 'showConfigModal');
	let apiStatus = $.tag($.state("unknown"), 'apiStatus');
	let lastUpdateTime = $.tag($.state(null), 'lastUpdateTime');
	let refreshIntervalSeconds = $.tag($.state(20), 'refreshIntervalSeconds');
	let poller = null;
	const configStorage = new LocalStorageConfigStorage();
	const configParser = new ConfigParser();
	const cache = new LocalStorageCache();

	// departureRepository will be created per route based on stop configs
	let departureRepository = null;

	let groupingService = null;

	// Initialize all - matches Python version's initializeAll() function
	function initializeAll() {
		// Initialize time format toggle
		if ($.strict_equals($.get(currentRoute)?.display?.timeFormatToggleSeconds, undefined, false)) {
			initTimeFormatToggle($.get(currentRoute).display.timeFormatToggleSeconds);
		}

		// Initialize destination scrolling for clipped text
		initDestinationScrolling();

		// Calculate dynamic font sizes if fill_vertical_space is enabled
		// This matches Python: if (window.DEPARTURES_CONFIG && window.DEPARTURES_CONFIG.fillVerticalSpace) { requestAnimationFrame(() => { calculateFillVerticalSpace(); }); }
		if ($.get(currentRoute)?.display?.fillVerticalSpace && $.get(groupedDepartures).length > 0) {
			// Use requestAnimationFrame to ensure DOM is fully rendered (matches Python exactly)
			requestAnimationFrame(() => {
				calculateFillVerticalSpace({
					fillVerticalSpace: true,
					fontScalingFactorWhenFilling: $.get(currentRoute)?.display?.fontScalingFactorWhenFilling ?? 1.0
				});

				initDestinationScrolling();
			});
		}
	}

	onMount(async () => {
		(await $.track_reactivity_loss(loadConfig()))();

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

		(await $.track_reactivity_loss(initializeRoute()))();

		// Listen for hash changes (hash-based routing)
		window.addEventListener("hashchange", handleHashChange);

		// Listen for window resize to recalculate font sizes (matches Python exactly)
		// Handle window resize for fill_vertical_space (matches Python: lines 1426-1436)
		let resizeTimeout = null;

		window.addEventListener("resize", () => {
			if ($.get(currentRoute)?.display?.fillVerticalSpace) {
				// Debounce resize events (matches Python: 150ms)
				if (resizeTimeout) clearTimeout(resizeTimeout);

				resizeTimeout = window.setTimeout(
					() => {
						calculateFillVerticalSpace({
							fillVerticalSpace: true,
							fontScalingFactorWhenFilling: $.get(currentRoute)?.display?.fontScalingFactorWhenFilling ?? 1.0
						});
					},
					150
				);
			}
		});
	});

	// Recalculate font sizes after departures update
	// This matches Python's phx:update handler: requestAnimationFrame(() => { calculateFillVerticalSpace(); })
	$.user_effect(async () => {
		// Access reactive values to trigger effect
		const _ = $.get(groupedDepartures);

		const __ = $.get(currentRoute);

		if ($.get(currentRoute)?.display?.fillVerticalSpace && $.get(groupedDepartures).length > 0) {
			// Wait for Svelte to finish rendering
			(await $.track_reactivity_loss(tick()))();

			// Use requestAnimationFrame to ensure DOM is fully laid out (matches Python exactly)
			requestAnimationFrame(() => {
				console.log("Recalculating font sizes (fillVerticalSpace enabled)");

				calculateFillVerticalSpace({
					fillVerticalSpace: true,
					fontScalingFactorWhenFilling: $.get(currentRoute)?.display?.fontScalingFactorWhenFilling ?? 1.0
				});

				// Also initialize destination scrolling (for clipped text)
				initDestinationScrolling();

				// Initialize time format toggle (will reinitialize if already running)
				initTimeFormatToggle($.get(currentRoute)?.display?.timeFormatToggleSeconds ?? 0);
			});
		} else if (!$.get(currentRoute)?.display?.fillVerticalSpace) {
			console.log("fillVerticalSpace is disabled, using default font sizes");

			// Still initialize time format toggle even if fillVerticalSpace is disabled
			requestAnimationFrame(() => {
				initTimeFormatToggle($.get(currentRoute)?.display?.timeFormatToggleSeconds ?? 0);
			});
		}
	});

	function handleHashChange() {
		const hash = window.location.hash.slice(1); // Remove leading #

		if (!$.get(config) || $.strict_equals($.get(config).routes.length, 0)) {
			return;
		}

		const route = $.get(config).routes.find((r) => $.strict_equals(r.path, hash) || $.strict_equals(hash, "") && $.strict_equals(r.path, "/"));

		if (route) {
			switchRoute(route, false); // false = don't update hash (hash already changed)
		}
	}

	async function loadConfig() {
		const stored = (await $.track_reactivity_loss(configStorage.getConfig()))();

		if (stored) {
			$.set(config, stored, true);
			console.log(`Loaded config with ${stored.routes.length} route(s)`);

			stored.routes.forEach((route, idx) => {
				console.log(`  Route ${idx + 1}: path="${route.path}", ${route.stops.length} stop(s), fillVerticalSpace=${route.display?.fillVerticalSpace ?? false}`);
			});
		} else {
			console.log("No config found in localStorage");
		}
	}

	async function initializeRoute() {
		if (!$.get(config) || $.strict_equals($.get(config).routes.length, 0)) {
			return;
		}

		// Get current route from hash (hash-based routing for SPA)
		const hash = window.location.hash.slice(1); // Remove leading #

		// If hash is empty or just "/", use the first route (default) but don't change the URL
		let route;

		if ($.strict_equals(hash, "") || $.strict_equals(hash, "/")) {
			route = $.get(config).routes[0];

			// Use the route but don't set the hash - keep URL at root
			if (route) {
				(await $.track_reactivity_loss(switchRoute(route, false) // false = don't update hash
				))();
			}

			return;
		} else {
			route = $.get(config).routes.find((r) => $.strict_equals(r.path, hash));
		}

		// Fallback to first route if not found
		if (!route) {
			route = $.get(config).routes[0];
		}

		if (route) {
			(await $.track_reactivity_loss(switchRoute(route, true) // true = update hash (user navigated)
			))();
		}
	}

	async function switchRoute(route, updateHash = true) {
		console.log(`Switching to route: ${route.path} (${route.stops.length} stop(s))`);

		// Stop existing poller and wait for it to fully stop
		if (poller) {
			poller.stop();
			poller = null;

			// Small delay to ensure interval is cleared
			(await $.track_reactivity_loss(new Promise((resolve) => setTimeout(resolve, 10))))();
		}

		// Cleanup time format toggle
		cleanupTimeFormatToggle();

		// Clear existing departures when switching routes
		$.set(groupedDepartures, [], true);

		$.set(currentRoute, route, true);
		(await $.track_reactivity_loss(configStorage.setCurrentRoutePath(route.path)))();

		// Only update hash if explicitly requested (user navigation, not initial load)
		if (updateHash) {
			// Use hash-based routing for SPA (don't use pushState with pathname)
			// Use hash to avoid server-side routing issues
			const hash = $.strict_equals(route.path, "/") ? "" : route.path;

			window.location.hash = hash;
		}

		// Start polling for all stops in route
		if (route.stops.length > 0) {
			console.log(...$.log_if_contains_state('log', `Starting poller for ${route.stops.length} stop(s):`, route.stops.map((s) => `${s.stationName} (${s.stationId}, api=${s.apiProvider ?? "mvg"})`)));

			// Create composite repository that routes to correct API per stop
			// This matches the Python version's CompositeDepartureRepository behavior
			departureRepository = new CompositeDepartureRepository(route.stops);

			groupingService = new DepartureGroupingService(departureRepository);

			const refreshInterval = route.refreshIntervalSeconds ?? route.display?.refreshIntervalSeconds ?? 20;

			$.set(refreshIntervalSeconds, refreshInterval, true);

			poller = new MultiStopPoller(departureRepository, cache, groupingService, route.stops, refreshInterval, {
				onUpdate: (groups) => {
					console.log(`Received ${groups.length} direction group(s) with ${groups.reduce((sum, g) => sum + g.departures.length, 0)} total departures`);
					$.set(groupedDepartures, groups, true);
					$.set(apiStatus, "success");
					$.set(lastUpdateTime, new Date(), true);

					// Call initializeAll after data update (matches Python's phx:update handler)
					// Use requestAnimationFrame to ensure DOM is ready
					requestAnimationFrame(() => {
						initializeAll();
					});
				},

				onError: (error) => {
					console.error(...$.log_if_contains_state('error', "API poll error:", error));
					$.set(apiStatus, "error");
				}
			});

			(await $.track_reactivity_loss(poller.start()))();

			// Call initializeAll after initial poll completes (matches Python's initializeAll on page load)
			// Wait a bit for DOM to be ready
			requestAnimationFrame(() => {
				initializeAll();
			});
		}
	}

	function handleConfigSave(tomlConfig) {
		try {
			const parsed = configParser.parseToml(tomlConfig);

			configStorage.saveConfig(parsed).then(() => {
				$.set(config, parsed, true);
				$.set(showConfigModal, false);
				initializeRoute();
			});
		} catch(error) {
			console.error(...$.log_if_contains_state('error', "Failed to parse config:", error));
			alert("Failed to parse TOML config. Please check the format.");
		}
	}

	function handleConfigCancel() {
		$.set(showConfigModal, false);
	}

	function openConfig() {
		$.set(showConfigModal, true);
	}

	function handleRouteChange(path) {
		if (!$.get(config)) {
			return;
		}

		const route = $.get(config).routes.find((r) => $.strict_equals(r.path, path));

		if (route) {
			switchRoute(route, true); // true = update hash (user explicitly changed route)
		}
	}

	var $$exports = { ...$.legacy_api() };
	var div = root_1();
	let classes;
	var div_1 = $.child(div);
	var h1 = $.child(div_1);
	var text = $.child(h1, true);

	$.reset(h1);

	var div_2 = $.sibling(h1, 2);
	var node = $.child(div_2);

	{
		var consequent = ($$anchor) => {
			var text_1 = $.text();

			$.template_effect(($0) => $.set_text(text_1, `Last updated: ${$0 ?? ''}`), [() => $.get(lastUpdateTime).toLocaleTimeString()]);
			$.append($$anchor, text_1);
		};

		$.add_svelte_meta(
			() => $.if(node, ($$render) => {
				if ($.get(lastUpdateTime)) $$render(consequent);
			}),
			'if',
			App,
			298,
			6
		);
	}

	$.reset(div_2);
	$.reset(div_1);

	var div_3 = $.sibling(div_1, 2);
	var node_1 = $.child(div_3);

	{
		let $0 = $.derived(() => $.get(currentRoute)?.display);

		$.add_svelte_meta(
			() => DeparturesList(node_1, {
				get groupedDepartures() {
					return $.get(groupedDepartures);
				},

				get display() {
					return $.get($0);
				}
			}),
			'component',
			App,
			305,
			4,
			{ componentTag: 'DeparturesList' }
		);
	}

	$.reset(div_3);

	var node_2 = $.sibling(div_3, 2);

	{
		let $0 = $.derived(() => $.get(config)?.routes ?? []);
		let $1 = $.derived(() => $.get(currentRoute)?.path ?? null);

		$.add_svelte_meta(
			() => StatusBar(node_2, {
				get apiStatus() {
					return $.get(apiStatus);
				},

				get showConfigModal() {
					return $.get(showConfigModal);
				},
				onConfigClick: openConfig,
				get routes() {
					return $.get($0);
				},

				get currentRoutePath() {
					return $.get($1);
				},
				onRouteChange: handleRouteChange,
				get refreshIntervalSeconds() {
					return $.get(refreshIntervalSeconds);
				}
			}),
			'component',
			App,
			308,
			2,
			{ componentTag: 'StatusBar' }
		);
	}

	var node_3 = $.sibling(node_2, 2);

	{
		var consequent_1 = ($$anchor) => {
			$.add_svelte_meta(
				() => ConfigModal($$anchor, {
					get currentConfig() {
						return $.get(config);
					},
					onSave: handleConfigSave,
					onCancel: handleConfigCancel
				}),
				'component',
				App,
				319,
				4,
				{ componentTag: 'ConfigModal' }
			);
		};

		$.add_svelte_meta(
			() => $.if(node_3, ($$render) => {
				if ($.get(showConfigModal)) $$render(consequent_1);
			}),
			'if',
			App,
			318,
			2
		);
	}

	$.reset(div);

	$.template_effect(() => {
		classes = $.set_class(div, 1, 'container', null, classes, {
			'fill-vertical-space': $.get(currentRoute)?.display?.fillVerticalSpace ?? false
		});

		$.set_text(text, $.get(currentRoute)?.display?.title ?? "MVG Departures");
	});

	$.append($$anchor, div);

	return $.pop($$exports);
}