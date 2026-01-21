import 'svelte/internal/disclose-version';

DeparturesList[$.FILENAME] = 'src/components/DeparturesList.svelte';

import * as $ from 'svelte/internal/client';

var root_1 = $.add_locations($.from_html(`<div role="status" aria-live="polite" class="no-departures svelte-1apnbj7">No departures available</div>`), DeparturesList[$.FILENAME], [[128, 2]]);
var root_4 = $.add_locations($.from_html(`<span class="direction-header-text svelte-1apnbj7"> </span> <div class="direction-header-time status-header-item svelte-1apnbj7" id="datetime-display" aria-label="Current date and time"> </div>`, 1), DeparturesList[$.FILENAME], [[142, 10], [143, 10]]);
var root_8 = $.add_locations($.from_html(`<span class="delay-amount svelte-1apnbj7" aria-hidden="true"> </span>`), DeparturesList[$.FILENAME], [[179, 20]]);
var root_7 = $.add_locations($.from_html(` <!>`, 1), DeparturesList[$.FILENAME], []);

var root_6 = $.add_locations($.from_html(`<li role="listitem"><div class="route-container svelte-1apnbj7" aria-hidden="true"><span class="route-number svelte-1apnbj7"><span> </span></span> <span class="destination svelte-1apnbj7"><span class="destination-text"> </span></span></div> <div class="time-container svelte-1apnbj7" aria-hidden="true"><span class="platform svelte-1apnbj7"> </span> <span><!></span></div> <span class="sr-only svelte-1apnbj7"> </span></li>`), DeparturesList[$.FILENAME], [
	[
		152,
		10,
		[
			[157, 12, [[158, 14, [[159, 16]]], [163, 14, [[164, 16]]]]],
			[167, 12, [[173, 14], [174, 14]]],
			[187, 12]
		]
	]
]);

var root_3 = $.add_locations($.from_html(`<div class="direction-group svelte-1apnbj7"><h2 class="direction-header svelte-1apnbj7" role="heading" aria-level="2"><!></h2> <ul role="list"></ul></div>`), DeparturesList[$.FILENAME], [[133, 4, [[134, 6], [150, 6]]]]);

const $$css = {
	hash: 'svelte-1apnbj7',
	code: '\n  .no-departures.svelte-1apnbj7 {\n    width: 100%;\n    text-align: center;\n    font-size: var(--font-size-no-departures, 2.5rem);\n    color: #9ca3af;\n    padding: 2rem 0;\n    font-style: italic;\n  }\n\n  .direction-group.svelte-1apnbj7 {\n    width: 100%;\n  }\n\n  .direction-header.svelte-1apnbj7 {\n    font-size: var(--font-size-direction-header, 2.5rem);\n    font-weight: 700;\n    margin: 0.5rem 0 0.25rem 0;\n    padding: 0.5rem 0.75rem;\n    border-bottom: 2px solid rgba(0, 0, 0, 0.2);\n    opacity: 0.85;\n    display: flex;\n    justify-content: space-between;\n    align-items: center;\n    gap: 0.5rem;\n    background-color: var(--banner-color, #087BC4);\n    color: white;\n  }\n\n  .direction-header-text.svelte-1apnbj7 {\n    flex: 1;\n    min-width: 0;\n  }\n\n  .direction-header-time.svelte-1apnbj7 {\n    flex-shrink: 0;\n    margin-left: 1em;\n    white-space: nowrap;\n    display: flex;\n    align-items: center;\n    line-height: 1;\n    font-size: var(--font-size-status-header, 1.875rem);\n  }\n\n  .departure-row.svelte-1apnbj7 {\n    display: flex;\n    align-items: center;\n    padding: 0.75rem 0 0.75rem 0.75rem;\n    border-bottom: 1px solid rgba(0, 0, 0, 0.08);\n    min-height: 4.5rem;\n    width: 100%;\n    box-sizing: border-box;\n  }\n\n  .departure-row.cancelled.svelte-1apnbj7 {\n    opacity: 0.5;\n    text-decoration: line-through;\n  }\n\n  .route-container.svelte-1apnbj7 {\n    flex: 1 1 auto;\n    display: grid;\n    grid-template-columns: var(--route-column-width, 6.5em) 1fr;\n    align-items: center;\n    gap: 0.3em;\n    min-width: 0;\n    overflow: hidden;\n    padding: 0 0.75rem 0 0;\n  }\n\n  .route-number.svelte-1apnbj7 {\n    font-weight: 700;\n    font-size: var(--font-size-route-number, 4rem);\n    text-align: left;\n    padding: 0;\n    min-width: 0;\n    white-space: nowrap;\n    justify-self: start;\n    display: flex;\n    align-items: center;\n    gap: 0.3em;\n  }\n\n  .route-badge.svelte-1apnbj7 {\n    display: inline-flex;\n    align-items: center;\n    justify-content: center;\n    padding: 0.1em 0.3em;\n    min-width: 1.6em;\n    font-weight: 700;\n    color: #fff;\n    line-height: 1;\n    font-size: 0.9em;\n  }\n\n  .route-badge-ubahn.svelte-1apnbj7 {\n    background-color: #00508c;\n    border-radius: 0.15em;\n  }\n\n  .route-badge-sbahn.svelte-1apnbj7 {\n    background-color: #009551;\n    border-radius: 50%;\n    padding: 0.15em 0.35em;\n  }\n\n  .route-badge-bus.svelte-1apnbj7 {\n    background-color: #005d79;\n    border-radius: 50%;\n    padding: 0.15em 0.35em;\n  }\n\n  .route-badge-tram.svelte-1apnbj7 {\n    background-color: #dd0b2f;\n    border-radius: 0.15em;\n  }\n\n  .route-badge-regional.svelte-1apnbj7 {\n    background-color: #6b7280;\n    border-radius: 0.25em;\n  }\n\n  .destination.svelte-1apnbj7 {\n    overflow-x: hidden;\n    overflow-y: hidden;\n    white-space: nowrap;\n    padding: 0;\n    min-width: 0;\n    font-size: var(--font-size-destination, 3.5rem);\n    font-weight: 500;\n    text-align: left;\n    justify-self: start;\n  }\n\n  .time-container.svelte-1apnbj7 {\n    flex: 0 0 auto;\n    display: grid;\n    grid-template-columns: var(--platform-column-width, auto) var(--time-column-width, auto);\n    align-items: center;\n    padding: 0 0.75rem 0 0.75rem;\n    margin-right: 0;\n    gap: var(--time-container-gap, 0.75rem);\n    width: var(--time-container-width, auto);\n  }\n\n  .platform.svelte-1apnbj7 {\n    flex: 0 0 auto;\n    font-size: var(--font-size-platform, 2.5rem);\n    font-weight: 400;\n    text-align: left;\n    padding: 0;\n    white-space: nowrap;\n    min-width: fit-content;\n    color: #6b7280;\n  }\n\n  .time.svelte-1apnbj7 {\n    text-align: right;\n    font-weight: 600;\n    font-size: var(--font-size-time, 4rem);\n    white-space: nowrap;\n    min-width: fit-content;\n    overflow: hidden;\n    transition: opacity 0.3s ease-in-out;\n  }\n\n  .time.delay.svelte-1apnbj7 {\n    color: #d97706;\n  }\n\n  .time.realtime.svelte-1apnbj7 {\n    color: #059669;\n  }\n\n  .delay-amount.svelte-1apnbj7 {\n    color: #dc2626;\n    font-size: var(--font-size-delay-amount, 2rem);\n    font-weight: 500;\n    margin-left: 0.5rem;\n  }\n\n  .sr-only.svelte-1apnbj7 {\n    position: absolute;\n    width: 1px;\n    height: 1px;\n    padding: 0;\n    margin: -1px;\n    overflow: hidden;\n    clip: rect(0, 0, 0, 0);\n    white-space: nowrap;\n    border-width: 0;\n  }\n\n/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiRGVwYXJ0dXJlc0xpc3Quc3ZlbHRlIiwic291cmNlcyI6WyJEZXBhcnR1cmVzTGlzdC5zdmVsdGUiXSwic291cmNlc0NvbnRlbnQiOlsiPHNjcmlwdCBsYW5nPVwidHNcIj5cbiAgaW1wb3J0IHR5cGUgeyBHcm91cGVkRGVwYXJ0dXJlcywgRGlzcGxheUNvbmZpZ3VyYXRpb24gfSBmcm9tIFwiLi4vZG9tYWluL21vZGVscy9pbmRleC5qc1wiO1xuXG4gIGxldCB7XG4gICAgZ3JvdXBlZERlcGFydHVyZXMgPSBbXSxcbiAgICBkaXNwbGF5ID0gdW5kZWZpbmVkLFxuICB9OiB7XG4gICAgZ3JvdXBlZERlcGFydHVyZXM/OiBHcm91cGVkRGVwYXJ0dXJlc1tdO1xuICAgIGRpc3BsYXk/OiBEaXNwbGF5Q29uZmlndXJhdGlvbjtcbiAgfSA9ICRwcm9wcygpO1xuXG4gIGZ1bmN0aW9uIGZvcm1hdFRpbWVSZWxhdGl2ZShkZXBhcnR1cmU6IGFueSk6IHN0cmluZyB7XG4gICAgY29uc3Qgbm93ID0gbmV3IERhdGUoKTtcbiAgICBjb25zdCBkaWZmTXMgPSBkZXBhcnR1cmUudGltZS5nZXRUaW1lKCkgLSBub3cuZ2V0VGltZSgpO1xuICAgIGNvbnN0IGRpZmZNaW51dGVzID0gTWF0aC5mbG9vcihkaWZmTXMgLyA2MDAwMCk7XG5cbiAgICBpZiAoZGlmZk1pbnV0ZXMgPCAwKSB7XG4gICAgICByZXR1cm4gXCJub3dcIjtcbiAgICB9IGVsc2UgaWYgKGRpZmZNaW51dGVzIDwgNjApIHtcbiAgICAgIHJldHVybiBgJHtkaWZmTWludXRlc31tYDtcbiAgICB9IGVsc2Uge1xuICAgICAgY29uc3QgaG91cnMgPSBNYXRoLmZsb29yKGRpZmZNaW51dGVzIC8gNjApO1xuICAgICAgY29uc3QgbWlucyA9IGRpZmZNaW51dGVzICUgNjA7XG4gICAgICBpZiAobWlucyA9PT0gMCkge1xuICAgICAgICByZXR1cm4gYCR7aG91cnN9aGA7XG4gICAgICB9XG4gICAgICByZXR1cm4gYCR7aG91cnN9aCR7bWluc31tYDtcbiAgICB9XG4gIH1cblxuICBmdW5jdGlvbiBmb3JtYXRUaW1lQWJzb2x1dGUoZGVwYXJ0dXJlOiBhbnkpOiBzdHJpbmcge1xuICAgIGNvbnN0IGRhdGUgPSBuZXcgRGF0ZShkZXBhcnR1cmUudGltZSk7XG4gICAgY29uc3QgaG91cnMgPSBkYXRlLmdldEhvdXJzKCkudG9TdHJpbmcoKS5wYWRTdGFydCgyLCBcIjBcIik7XG4gICAgY29uc3QgbWludXRlcyA9IGRhdGUuZ2V0TWludXRlcygpLnRvU3RyaW5nKCkucGFkU3RhcnQoMiwgXCIwXCIpO1xuICAgIHJldHVybiBgJHtob3Vyc306JHttaW51dGVzfWA7XG4gIH1cblxuICBmdW5jdGlvbiBmb3JtYXRQbGFubmVkVGltZVJlbGF0aXZlKGRlcGFydHVyZTogYW55KTogc3RyaW5nIHtcbiAgICBpZiAoIWRlcGFydHVyZS5wbGFubmVkVGltZSkge1xuICAgICAgcmV0dXJuIGZvcm1hdFRpbWVSZWxhdGl2ZShkZXBhcnR1cmUpO1xuICAgIH1cbiAgICBjb25zdCBub3cgPSBuZXcgRGF0ZSgpO1xuICAgIGNvbnN0IGRpZmZNcyA9IGRlcGFydHVyZS5wbGFubmVkVGltZS5nZXRUaW1lKCkgLSBub3cuZ2V0VGltZSgpO1xuICAgIGNvbnN0IGRpZmZNaW51dGVzID0gTWF0aC5mbG9vcihkaWZmTXMgLyA2MDAwMCk7XG5cbiAgICBpZiAoZGlmZk1pbnV0ZXMgPCAwKSB7XG4gICAgICByZXR1cm4gXCJub3dcIjtcbiAgICB9IGVsc2UgaWYgKGRpZmZNaW51dGVzIDwgNjApIHtcbiAgICAgIHJldHVybiBgJHtkaWZmTWludXRlc31tYDtcbiAgICB9IGVsc2Uge1xuICAgICAgY29uc3QgaG91cnMgPSBNYXRoLmZsb29yKGRpZmZNaW51dGVzIC8gNjApO1xuICAgICAgY29uc3QgbWlucyA9IGRpZmZNaW51dGVzICUgNjA7XG4gICAgICBpZiAobWlucyA9PT0gMCkge1xuICAgICAgICByZXR1cm4gYCR7aG91cnN9aGA7XG4gICAgICB9XG4gICAgICByZXR1cm4gYCR7aG91cnN9aCR7bWluc31tYDtcbiAgICB9XG4gIH1cblxuICBmdW5jdGlvbiBmb3JtYXRQbGFubmVkVGltZUFic29sdXRlKGRlcGFydHVyZTogYW55KTogc3RyaW5nIHtcbiAgICBpZiAoIWRlcGFydHVyZS5wbGFubmVkVGltZSkge1xuICAgICAgcmV0dXJuIGZvcm1hdFRpbWVBYnNvbHV0ZShkZXBhcnR1cmUpO1xuICAgIH1cbiAgICBjb25zdCBkYXRlID0gbmV3IERhdGUoZGVwYXJ0dXJlLnBsYW5uZWRUaW1lKTtcbiAgICBjb25zdCBob3VycyA9IGRhdGUuZ2V0SG91cnMoKS50b1N0cmluZygpLnBhZFN0YXJ0KDIsIFwiMFwiKTtcbiAgICBjb25zdCBtaW51dGVzID0gZGF0ZS5nZXRNaW51dGVzKCkudG9TdHJpbmcoKS5wYWRTdGFydCgyLCBcIjBcIik7XG4gICAgcmV0dXJuIGAke2hvdXJzfToke21pbnV0ZXN9YDtcbiAgfVxuXG4gIGZ1bmN0aW9uIGdldERlbGF5TWludXRlcyhkZXBhcnR1cmU6IGFueSk6IG51bWJlciB8IG51bGwge1xuICAgIC8vIE1hdGNoIFB5dGhvbiB2ZXJzaW9uOiBoYXNfZGVsYXkgPSBkZXBhcnR1cmUuZGVsYXlfc2Vjb25kcyBpcyBub3QgTm9uZSBhbmQgZGVwYXJ0dXJlLmRlbGF5X3NlY29uZHMgPiA2MFxuICAgIC8vIE9ubHkgZGVsYXlzID4gNjAgc2Vjb25kcyAoMSBtaW51dGUpIGFyZSBjb25zaWRlcmVkIGRlbGF5c1xuICAgIGlmIChkZXBhcnR1cmUuZGVsYXlTZWNvbmRzICE9IG51bGwgJiYgZGVwYXJ0dXJlLmRlbGF5U2Vjb25kcyA+IDYwKSB7XG4gICAgICAvLyBNYXRjaCBQeXRob246IGRlbGF5X21pbnV0ZXMgPSBkZXBhcnR1cmUuZGVsYXlfc2Vjb25kcyAvLyA2MCAoaW50ZWdlciBkaXZpc2lvbilcbiAgICAgIHJldHVybiBNYXRoLmZsb29yKGRlcGFydHVyZS5kZWxheVNlY29uZHMgLyA2MCk7XG4gICAgfVxuICAgIHJldHVybiBudWxsO1xuICB9XG4gIFxuICBmdW5jdGlvbiBoYXNEZWxheShkZXBhcnR1cmU6IGFueSk6IGJvb2xlYW4ge1xuICAgIC8vIE1hdGNoIFB5dGhvbjogaGFzX2RlbGF5ID0gZGVwYXJ0dXJlLmRlbGF5X3NlY29uZHMgaXMgbm90IE5vbmUgYW5kIGRlcGFydHVyZS5kZWxheV9zZWNvbmRzID4gNjBcbiAgICByZXR1cm4gZGVwYXJ0dXJlLmRlbGF5U2Vjb25kcyAhPSBudWxsICYmIGRlcGFydHVyZS5kZWxheVNlY29uZHMgPiA2MDtcbiAgfVxuXG4gIGZ1bmN0aW9uIGZvcm1hdEhlYWRlclRpbWUoZGVwYXJ0dXJlOiBhbnkpOiBzdHJpbmcge1xuICAgIC8vIEZvcm1hdCB0aW1lIGZvciBoZWFkZXI6IFwiKGluIFgrIG1pbilcIiBvciBcIihpbiBYIG1pbilcIlxuICAgIGNvbnN0IG5vdyA9IG5ldyBEYXRlKCk7XG4gICAgY29uc3QgZGlmZk1zID0gZGVwYXJ0dXJlLnRpbWUuZ2V0VGltZSgpIC0gbm93LmdldFRpbWUoKTtcbiAgICBjb25zdCBkaWZmTWludXRlcyA9IE1hdGguZmxvb3IoZGlmZk1zIC8gNjAwMDApO1xuXG4gICAgaWYgKGRpZmZNaW51dGVzIDwgMCkge1xuICAgICAgcmV0dXJuIFwiKG5vdylcIjtcbiAgICB9IGVsc2UgaWYgKGRpZmZNaW51dGVzIDwgNjApIHtcbiAgICAgIHJldHVybiBgKGluICR7ZGlmZk1pbnV0ZXN9KyBtaW4pYDtcbiAgICB9IGVsc2Uge1xuICAgICAgY29uc3QgaG91cnMgPSBNYXRoLmZsb29yKGRpZmZNaW51dGVzIC8gNjApO1xuICAgICAgY29uc3QgbWlucyA9IGRpZmZNaW51dGVzICUgNjA7XG4gICAgICBpZiAobWlucyA9PT0gMCkge1xuICAgICAgICByZXR1cm4gYChpbiAke2hvdXJzfSsgaClgO1xuICAgICAgfVxuICAgICAgcmV0dXJuIGAoaW4gJHtob3Vyc30rIGggJHttaW5zfSsgbWluKWA7XG4gICAgfVxuICB9XG5cbiAgZnVuY3Rpb24gZ2V0SGVhZGVyVGV4dChncm91cDogYW55KTogc3RyaW5nIHtcbiAgICAvLyBGb3JtYXQ6IFwiU3RvcE5hbWUg4oaSIERpcmVjdGlvbk5hbWUgKGluIFgrIG1pbilcIiBpZiB0aGVyZSBhcmUgZGVwYXJ0dXJlc1xuICAgIGNvbnN0IGJhc2VUZXh0ID0gYCR7Z3JvdXAuc3RvcE5hbWV9IOKGkiAke2dyb3VwLmRpcmVjdGlvbk5hbWV9YDtcbiAgICBpZiAoZ3JvdXAuZGVwYXJ0dXJlcyAmJiBncm91cC5kZXBhcnR1cmVzLmxlbmd0aCA+IDApIHtcbiAgICAgIGNvbnN0IGZpcnN0RGVwYXJ0dXJlID0gZ3JvdXAuZGVwYXJ0dXJlc1swXTtcbiAgICAgIGNvbnN0IHRpbWVUZXh0ID0gZm9ybWF0SGVhZGVyVGltZShmaXJzdERlcGFydHVyZSk7XG4gICAgICByZXR1cm4gYCR7YmFzZVRleHR9ICR7dGltZVRleHR9YDtcbiAgICB9XG4gICAgcmV0dXJuIGJhc2VUZXh0O1xuICB9XG5cbiAgZnVuY3Rpb24gZ2V0VHJhbnNwb3J0VHlwZUNzcyh0cmFuc3BvcnRUeXBlOiBzdHJpbmcpOiBzdHJpbmcge1xuICAgIGNvbnN0IG1hcDogUmVjb3JkPHN0cmluZywgc3RyaW5nPiA9IHtcbiAgICAgIFwiVS1CYWhuXCI6IFwidWJhaG5cIixcbiAgICAgIFwiUy1CYWhuXCI6IFwic2JhaG5cIixcbiAgICAgIEJ1czogXCJidXNcIixcbiAgICAgIFRyYW06IFwidHJhbVwiLFxuICAgIH07XG4gICAgcmV0dXJuIG1hcFt0cmFuc3BvcnRUeXBlXSB8fCBcInJlZ2lvbmFsXCI7XG4gIH1cbjwvc2NyaXB0PlxuXG57I2lmIGdyb3VwZWREZXBhcnR1cmVzLmxlbmd0aCA9PT0gMH1cbiAgPGRpdiByb2xlPVwic3RhdHVzXCIgYXJpYS1saXZlPVwicG9saXRlXCIgY2xhc3M9XCJuby1kZXBhcnR1cmVzXCI+XG4gICAgTm8gZGVwYXJ0dXJlcyBhdmFpbGFibGVcbiAgPC9kaXY+XG57OmVsc2V9XG4gIHsjZWFjaCBncm91cGVkRGVwYXJ0dXJlcyBhcyBncm91cCwgZ3JvdXBJbmRleCAoZ3JvdXBJbmRleCl9XG4gICAgPGRpdiBjbGFzcz1cImRpcmVjdGlvbi1ncm91cFwiPlxuICAgICAgPGgyIFxuICAgICAgICBjbGFzcz1cImRpcmVjdGlvbi1oZWFkZXJcIiBcbiAgICAgICAgcm9sZT1cImhlYWRpbmdcIiBcbiAgICAgICAgYXJpYS1sZXZlbD1cIjJcIlxuICAgICAgICBzdHlsZT17Z3JvdXAuaGVhZGVyQ29sb3IgPyBgYmFja2dyb3VuZC1jb2xvcjogJHtncm91cC5oZWFkZXJDb2xvcn07YCA6IHVuZGVmaW5lZH1cbiAgICAgICAgZGF0YS1maWxsLXZlcnRpY2FsLXNwYWNlPXtkaXNwbGF5Py5maWxsVmVydGljYWxTcGFjZSAmJiBncm91cEluZGV4ID09PSAwID8gXCJ0cnVlXCIgOiB1bmRlZmluZWR9XG4gICAgICA+XG4gICAgICAgIHsjaWYgZ3JvdXBJbmRleCA9PT0gMH1cbiAgICAgICAgICA8c3BhbiBjbGFzcz1cImRpcmVjdGlvbi1oZWFkZXItdGV4dFwiPntnZXRIZWFkZXJUZXh0KGdyb3VwKX08L3NwYW4+XG4gICAgICAgICAgPGRpdiBjbGFzcz1cImRpcmVjdGlvbi1oZWFkZXItdGltZSBzdGF0dXMtaGVhZGVyLWl0ZW1cIiBpZD1cImRhdGV0aW1lLWRpc3BsYXlcIiBhcmlhLWxhYmVsPVwiQ3VycmVudCBkYXRlIGFuZCB0aW1lXCI+XG4gICAgICAgICAgICB7bmV3IERhdGUoKS50b0xvY2FsZVN0cmluZyhcImRlLURFXCIpfVxuICAgICAgICAgIDwvZGl2PlxuICAgICAgICB7OmVsc2V9XG4gICAgICAgICAge2dldEhlYWRlclRleHQoZ3JvdXApfVxuICAgICAgICB7L2lmfVxuICAgICAgPC9oMj5cbiAgICAgIDx1bCByb2xlPVwibGlzdFwiIGFyaWEtbGFiZWw9XCJEZXBhcnR1cmVzIGZvciB7Z3JvdXAuZGlyZWN0aW9uTmFtZX1cIj5cbiAgICAgICAgeyNlYWNoIGdyb3VwLmRlcGFydHVyZXMgYXMgZGVwYXJ0dXJlIChkZXBhcnR1cmUubGluZSArIGRlcGFydHVyZS5kZXN0aW5hdGlvbiArIGRlcGFydHVyZS50aW1lLmdldFRpbWUoKSl9XG4gICAgICAgICAgPGxpXG4gICAgICAgICAgICBjbGFzcz1cImRlcGFydHVyZS1yb3cge2RlcGFydHVyZS5pc0NhbmNlbGxlZCA/ICdjYW5jZWxsZWQnIDogJyd9XCJcbiAgICAgICAgICAgIHJvbGU9XCJsaXN0aXRlbVwiXG4gICAgICAgICAgICBhcmlhLWxhYmVsPVwie2RlcGFydHVyZS50cmFuc3BvcnRUeXBlfSB7ZGVwYXJ0dXJlLmxpbmV9IHRvIHtkZXBhcnR1cmUuZGVzdGluYXRpb259LCB7Zm9ybWF0VGltZVJlbGF0aXZlKGRlcGFydHVyZSl9XCJcbiAgICAgICAgICA+XG4gICAgICAgICAgICA8ZGl2IGNsYXNzPVwicm91dGUtY29udGFpbmVyXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICAgICAgICAgIDxzcGFuIGNsYXNzPVwicm91dGUtbnVtYmVyXCI+XG4gICAgICAgICAgICAgICAgPHNwYW4gY2xhc3M9XCJyb3V0ZS1iYWRnZSByb3V0ZS1iYWRnZS17Z2V0VHJhbnNwb3J0VHlwZUNzcyhkZXBhcnR1cmUudHJhbnNwb3J0VHlwZSl9XCI+XG4gICAgICAgICAgICAgICAgICB7ZGVwYXJ0dXJlLmxpbmV9XG4gICAgICAgICAgICAgICAgPC9zcGFuPlxuICAgICAgICAgICAgICA8L3NwYW4+XG4gICAgICAgICAgICAgIDxzcGFuIGNsYXNzPVwiZGVzdGluYXRpb25cIj5cbiAgICAgICAgICAgICAgICA8c3BhbiBjbGFzcz1cImRlc3RpbmF0aW9uLXRleHRcIj57ZGVwYXJ0dXJlLmRlc3RpbmF0aW9ufTwvc3Bhbj5cbiAgICAgICAgICAgICAgPC9zcGFuPlxuICAgICAgICAgICAgPC9kaXY+XG4gICAgICAgICAgICA8ZGl2IFxuICAgICAgICAgICAgICBjbGFzcz1cInRpbWUtY29udGFpbmVyXCIgXG4gICAgICAgICAgICAgIGFyaWEtaGlkZGVuPVwidHJ1ZVwiXG4gICAgICAgICAgICAgIGRhdGEtdGltZS1yZWxhdGl2ZT17ZGlzcGxheT8uc3BsaXRTaG93RGVsYXkgPyBmb3JtYXRQbGFubmVkVGltZVJlbGF0aXZlKGRlcGFydHVyZSkgOiBmb3JtYXRUaW1lUmVsYXRpdmUoZGVwYXJ0dXJlKX1cbiAgICAgICAgICAgICAgZGF0YS10aW1lLWFic29sdXRlPXtkaXNwbGF5Py5zcGxpdFNob3dEZWxheSA/IGZvcm1hdFBsYW5uZWRUaW1lQWJzb2x1dGUoZGVwYXJ0dXJlKSA6IGZvcm1hdFRpbWVBYnNvbHV0ZShkZXBhcnR1cmUpfVxuICAgICAgICAgICAgPlxuICAgICAgICAgICAgICA8c3BhbiBjbGFzcz1cInBsYXRmb3JtXCI+e2RlcGFydHVyZS5wbGF0Zm9ybSB8fCBcIlwifTwvc3Bhbj5cbiAgICAgICAgICAgICAgPHNwYW4gY2xhc3M9XCJ0aW1lIHtoYXNEZWxheShkZXBhcnR1cmUpID8gJ2RlbGF5JyA6ICcnfSB7ZGVwYXJ0dXJlLmlzUmVhbHRpbWUgPyAncmVhbHRpbWUnIDogJyd9XCI+XG4gICAgICAgICAgICAgICAgeyNpZiBkaXNwbGF5Py5zcGxpdFNob3dEZWxheX1cbiAgICAgICAgICAgICAgICAgIDwhLS0gc3BsaXRTaG93RGVsYXk9dHJ1ZTogc2hvdyBwbGFubmVkIHRpbWUgKyBzZXBhcmF0ZSBkZWxheSBpbmRpY2F0b3IgLS0+XG4gICAgICAgICAgICAgICAgICB7Zm9ybWF0UGxhbm5lZFRpbWVSZWxhdGl2ZShkZXBhcnR1cmUpfVxuICAgICAgICAgICAgICAgICAgeyNpZiBnZXREZWxheU1pbnV0ZXMoZGVwYXJ0dXJlKX1cbiAgICAgICAgICAgICAgICAgICAgPHNwYW4gY2xhc3M9XCJkZWxheS1hbW91bnRcIiBhcmlhLWhpZGRlbj1cInRydWVcIj4re2dldERlbGF5TWludXRlcyhkZXBhcnR1cmUpfW08L3NwYW4+XG4gICAgICAgICAgICAgICAgICB7L2lmfVxuICAgICAgICAgICAgICAgIHs6ZWxzZX1cbiAgICAgICAgICAgICAgICAgIDwhLS0gc3BsaXRTaG93RGVsYXk9ZmFsc2UgKGRlZmF1bHQpOiBzaG93IGV4cGVjdGVkIHRpbWUgKGluY2x1ZGVzIGRlbGF5KSAtIE5PIGRlbGF5IGluZGljYXRvciAtLT5cbiAgICAgICAgICAgICAgICAgIHtmb3JtYXRUaW1lUmVsYXRpdmUoZGVwYXJ0dXJlKX1cbiAgICAgICAgICAgICAgICB7L2lmfVxuICAgICAgICAgICAgICA8L3NwYW4+XG4gICAgICAgICAgICA8L2Rpdj5cbiAgICAgICAgICAgIDxzcGFuIGNsYXNzPVwic3Itb25seVwiPlxuICAgICAgICAgICAgICB7ZGVwYXJ0dXJlLnRyYW5zcG9ydFR5cGV9IHtkZXBhcnR1cmUubGluZX0gdG8ge2RlcGFydHVyZS5kZXN0aW5hdGlvbn0sIHtmb3JtYXRUaW1lUmVsYXRpdmUoZGVwYXJ0dXJlKX1cbiAgICAgICAgICAgIDwvc3Bhbj5cbiAgICAgICAgICA8L2xpPlxuICAgICAgICB7L2VhY2h9XG4gICAgICA8L3VsPlxuICAgIDwvZGl2PlxuICB7L2VhY2h9XG57L2lmfVxuXG48c3R5bGU+XG4gIC5uby1kZXBhcnR1cmVzIHtcbiAgICB3aWR0aDogMTAwJTtcbiAgICB0ZXh0LWFsaWduOiBjZW50ZXI7XG4gICAgZm9udC1zaXplOiB2YXIoLS1mb250LXNpemUtbm8tZGVwYXJ0dXJlcywgMi41cmVtKTtcbiAgICBjb2xvcjogIzljYTNhZjtcbiAgICBwYWRkaW5nOiAycmVtIDA7XG4gICAgZm9udC1zdHlsZTogaXRhbGljO1xuICB9XG5cbiAgLmRpcmVjdGlvbi1ncm91cCB7XG4gICAgd2lkdGg6IDEwMCU7XG4gIH1cblxuICAuZGlyZWN0aW9uLWhlYWRlciB7XG4gICAgZm9udC1zaXplOiB2YXIoLS1mb250LXNpemUtZGlyZWN0aW9uLWhlYWRlciwgMi41cmVtKTtcbiAgICBmb250LXdlaWdodDogNzAwO1xuICAgIG1hcmdpbjogMC41cmVtIDAgMC4yNXJlbSAwO1xuICAgIHBhZGRpbmc6IDAuNXJlbSAwLjc1cmVtO1xuICAgIGJvcmRlci1ib3R0b206IDJweCBzb2xpZCByZ2JhKDAsIDAsIDAsIDAuMik7XG4gICAgb3BhY2l0eTogMC44NTtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGp1c3RpZnktY29udGVudDogc3BhY2UtYmV0d2VlbjtcbiAgICBhbGlnbi1pdGVtczogY2VudGVyO1xuICAgIGdhcDogMC41cmVtO1xuICAgIGJhY2tncm91bmQtY29sb3I6IHZhcigtLWJhbm5lci1jb2xvciwgIzA4N0JDNCk7XG4gICAgY29sb3I6IHdoaXRlO1xuICB9XG5cbiAgLmRpcmVjdGlvbi1oZWFkZXItdGV4dCB7XG4gICAgZmxleDogMTtcbiAgICBtaW4td2lkdGg6IDA7XG4gIH1cblxuICAuZGlyZWN0aW9uLWhlYWRlci10aW1lIHtcbiAgICBmbGV4LXNocmluazogMDtcbiAgICBtYXJnaW4tbGVmdDogMWVtO1xuICAgIHdoaXRlLXNwYWNlOiBub3dyYXA7XG4gICAgZGlzcGxheTogZmxleDtcbiAgICBhbGlnbi1pdGVtczogY2VudGVyO1xuICAgIGxpbmUtaGVpZ2h0OiAxO1xuICAgIGZvbnQtc2l6ZTogdmFyKC0tZm9udC1zaXplLXN0YXR1cy1oZWFkZXIsIDEuODc1cmVtKTtcbiAgfVxuXG4gIC5kZXBhcnR1cmUtcm93IHtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAgcGFkZGluZzogMC43NXJlbSAwIDAuNzVyZW0gMC43NXJlbTtcbiAgICBib3JkZXItYm90dG9tOiAxcHggc29saWQgcmdiYSgwLCAwLCAwLCAwLjA4KTtcbiAgICBtaW4taGVpZ2h0OiA0LjVyZW07XG4gICAgd2lkdGg6IDEwMCU7XG4gICAgYm94LXNpemluZzogYm9yZGVyLWJveDtcbiAgfVxuXG4gIC5kZXBhcnR1cmUtcm93LmNhbmNlbGxlZCB7XG4gICAgb3BhY2l0eTogMC41O1xuICAgIHRleHQtZGVjb3JhdGlvbjogbGluZS10aHJvdWdoO1xuICB9XG5cbiAgLnJvdXRlLWNvbnRhaW5lciB7XG4gICAgZmxleDogMSAxIGF1dG87XG4gICAgZGlzcGxheTogZ3JpZDtcbiAgICBncmlkLXRlbXBsYXRlLWNvbHVtbnM6IHZhcigtLXJvdXRlLWNvbHVtbi13aWR0aCwgNi41ZW0pIDFmcjtcbiAgICBhbGlnbi1pdGVtczogY2VudGVyO1xuICAgIGdhcDogMC4zZW07XG4gICAgbWluLXdpZHRoOiAwO1xuICAgIG92ZXJmbG93OiBoaWRkZW47XG4gICAgcGFkZGluZzogMCAwLjc1cmVtIDAgMDtcbiAgfVxuXG4gIC5yb3V0ZS1udW1iZXIge1xuICAgIGZvbnQtd2VpZ2h0OiA3MDA7XG4gICAgZm9udC1zaXplOiB2YXIoLS1mb250LXNpemUtcm91dGUtbnVtYmVyLCA0cmVtKTtcbiAgICB0ZXh0LWFsaWduOiBsZWZ0O1xuICAgIHBhZGRpbmc6IDA7XG4gICAgbWluLXdpZHRoOiAwO1xuICAgIHdoaXRlLXNwYWNlOiBub3dyYXA7XG4gICAganVzdGlmeS1zZWxmOiBzdGFydDtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAgZ2FwOiAwLjNlbTtcbiAgfVxuXG4gIC5yb3V0ZS1iYWRnZSB7XG4gICAgZGlzcGxheTogaW5saW5lLWZsZXg7XG4gICAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjtcbiAgICBwYWRkaW5nOiAwLjFlbSAwLjNlbTtcbiAgICBtaW4td2lkdGg6IDEuNmVtO1xuICAgIGZvbnQtd2VpZ2h0OiA3MDA7XG4gICAgY29sb3I6ICNmZmY7XG4gICAgbGluZS1oZWlnaHQ6IDE7XG4gICAgZm9udC1zaXplOiAwLjllbTtcbiAgfVxuXG4gIC5yb3V0ZS1iYWRnZS11YmFobiB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogIzAwNTA4YztcbiAgICBib3JkZXItcmFkaXVzOiAwLjE1ZW07XG4gIH1cblxuICAucm91dGUtYmFkZ2Utc2JhaG4ge1xuICAgIGJhY2tncm91bmQtY29sb3I6ICMwMDk1NTE7XG4gICAgYm9yZGVyLXJhZGl1czogNTAlO1xuICAgIHBhZGRpbmc6IDAuMTVlbSAwLjM1ZW07XG4gIH1cblxuICAucm91dGUtYmFkZ2UtYnVzIHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjMDA1ZDc5O1xuICAgIGJvcmRlci1yYWRpdXM6IDUwJTtcbiAgICBwYWRkaW5nOiAwLjE1ZW0gMC4zNWVtO1xuICB9XG5cbiAgLnJvdXRlLWJhZGdlLXRyYW0ge1xuICAgIGJhY2tncm91bmQtY29sb3I6ICNkZDBiMmY7XG4gICAgYm9yZGVyLXJhZGl1czogMC4xNWVtO1xuICB9XG5cbiAgLnJvdXRlLWJhZGdlLXJlZ2lvbmFsIHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiAjNmI3MjgwO1xuICAgIGJvcmRlci1yYWRpdXM6IDAuMjVlbTtcbiAgfVxuXG4gIC5kZXN0aW5hdGlvbiB7XG4gICAgb3ZlcmZsb3cteDogaGlkZGVuO1xuICAgIG92ZXJmbG93LXk6IGhpZGRlbjtcbiAgICB3aGl0ZS1zcGFjZTogbm93cmFwO1xuICAgIHBhZGRpbmc6IDA7XG4gICAgbWluLXdpZHRoOiAwO1xuICAgIGZvbnQtc2l6ZTogdmFyKC0tZm9udC1zaXplLWRlc3RpbmF0aW9uLCAzLjVyZW0pO1xuICAgIGZvbnQtd2VpZ2h0OiA1MDA7XG4gICAgdGV4dC1hbGlnbjogbGVmdDtcbiAgICBqdXN0aWZ5LXNlbGY6IHN0YXJ0O1xuICB9XG5cbiAgLnRpbWUtY29udGFpbmVyIHtcbiAgICBmbGV4OiAwIDAgYXV0bztcbiAgICBkaXNwbGF5OiBncmlkO1xuICAgIGdyaWQtdGVtcGxhdGUtY29sdW1uczogdmFyKC0tcGxhdGZvcm0tY29sdW1uLXdpZHRoLCBhdXRvKSB2YXIoLS10aW1lLWNvbHVtbi13aWR0aCwgYXV0byk7XG4gICAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAgICBwYWRkaW5nOiAwIDAuNzVyZW0gMCAwLjc1cmVtO1xuICAgIG1hcmdpbi1yaWdodDogMDtcbiAgICBnYXA6IHZhcigtLXRpbWUtY29udGFpbmVyLWdhcCwgMC43NXJlbSk7XG4gICAgd2lkdGg6IHZhcigtLXRpbWUtY29udGFpbmVyLXdpZHRoLCBhdXRvKTtcbiAgfVxuXG4gIC5wbGF0Zm9ybSB7XG4gICAgZmxleDogMCAwIGF1dG87XG4gICAgZm9udC1zaXplOiB2YXIoLS1mb250LXNpemUtcGxhdGZvcm0sIDIuNXJlbSk7XG4gICAgZm9udC13ZWlnaHQ6IDQwMDtcbiAgICB0ZXh0LWFsaWduOiBsZWZ0O1xuICAgIHBhZGRpbmc6IDA7XG4gICAgd2hpdGUtc3BhY2U6IG5vd3JhcDtcbiAgICBtaW4td2lkdGg6IGZpdC1jb250ZW50O1xuICAgIGNvbG9yOiAjNmI3MjgwO1xuICB9XG5cbiAgLnRpbWUge1xuICAgIHRleHQtYWxpZ246IHJpZ2h0O1xuICAgIGZvbnQtd2VpZ2h0OiA2MDA7XG4gICAgZm9udC1zaXplOiB2YXIoLS1mb250LXNpemUtdGltZSwgNHJlbSk7XG4gICAgd2hpdGUtc3BhY2U6IG5vd3JhcDtcbiAgICBtaW4td2lkdGg6IGZpdC1jb250ZW50O1xuICAgIG92ZXJmbG93OiBoaWRkZW47XG4gICAgdHJhbnNpdGlvbjogb3BhY2l0eSAwLjNzIGVhc2UtaW4tb3V0O1xuICB9XG5cbiAgLnRpbWUuZGVsYXkge1xuICAgIGNvbG9yOiAjZDk3NzA2O1xuICB9XG5cbiAgLnRpbWUucmVhbHRpbWUge1xuICAgIGNvbG9yOiAjMDU5NjY5O1xuICB9XG5cbiAgLmRlbGF5LWFtb3VudCB7XG4gICAgY29sb3I6ICNkYzI2MjY7XG4gICAgZm9udC1zaXplOiB2YXIoLS1mb250LXNpemUtZGVsYXktYW1vdW50LCAycmVtKTtcbiAgICBmb250LXdlaWdodDogNTAwO1xuICAgIG1hcmdpbi1sZWZ0OiAwLjVyZW07XG4gIH1cblxuICAuc3Itb25seSB7XG4gICAgcG9zaXRpb246IGFic29sdXRlO1xuICAgIHdpZHRoOiAxcHg7XG4gICAgaGVpZ2h0OiAxcHg7XG4gICAgcGFkZGluZzogMDtcbiAgICBtYXJnaW46IC0xcHg7XG4gICAgb3ZlcmZsb3c6IGhpZGRlbjtcbiAgICBjbGlwOiByZWN0KDAsIDAsIDAsIDApO1xuICAgIHdoaXRlLXNwYWNlOiBub3dyYXA7XG4gICAgYm9yZGVyLXdpZHRoOiAwO1xuICB9XG48L3N0eWxlPlxuIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7QUFxTUEsRUFBRSw2QkFBYyxDQUFDO0FBQ2pCLElBQUksV0FBVztBQUNmLElBQUksa0JBQWtCO0FBQ3RCLElBQUksaURBQWlEO0FBQ3JELElBQUksY0FBYztBQUNsQixJQUFJLGVBQWU7QUFDbkIsSUFBSSxrQkFBa0I7QUFDdEI7O0FBRUEsRUFBRSwrQkFBZ0IsQ0FBQztBQUNuQixJQUFJLFdBQVc7QUFDZjs7QUFFQSxFQUFFLGdDQUFpQixDQUFDO0FBQ3BCLElBQUksb0RBQW9EO0FBQ3hELElBQUksZ0JBQWdCO0FBQ3BCLElBQUksMEJBQTBCO0FBQzlCLElBQUksdUJBQXVCO0FBQzNCLElBQUksMkNBQTJDO0FBQy9DLElBQUksYUFBYTtBQUNqQixJQUFJLGFBQWE7QUFDakIsSUFBSSw4QkFBOEI7QUFDbEMsSUFBSSxtQkFBbUI7QUFDdkIsSUFBSSxXQUFXO0FBQ2YsSUFBSSw4Q0FBOEM7QUFDbEQsSUFBSSxZQUFZO0FBQ2hCOztBQUVBLEVBQUUscUNBQXNCLENBQUM7QUFDekIsSUFBSSxPQUFPO0FBQ1gsSUFBSSxZQUFZO0FBQ2hCOztBQUVBLEVBQUUscUNBQXNCLENBQUM7QUFDekIsSUFBSSxjQUFjO0FBQ2xCLElBQUksZ0JBQWdCO0FBQ3BCLElBQUksbUJBQW1CO0FBQ3ZCLElBQUksYUFBYTtBQUNqQixJQUFJLG1CQUFtQjtBQUN2QixJQUFJLGNBQWM7QUFDbEIsSUFBSSxtREFBbUQ7QUFDdkQ7O0FBRUEsRUFBRSw2QkFBYyxDQUFDO0FBQ2pCLElBQUksYUFBYTtBQUNqQixJQUFJLG1CQUFtQjtBQUN2QixJQUFJLGtDQUFrQztBQUN0QyxJQUFJLDRDQUE0QztBQUNoRCxJQUFJLGtCQUFrQjtBQUN0QixJQUFJLFdBQVc7QUFDZixJQUFJLHNCQUFzQjtBQUMxQjs7QUFFQSxFQUFFLGNBQWMseUJBQVUsQ0FBQztBQUMzQixJQUFJ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 */'
};

export default function DeparturesList($$anchor, $$props) {
	$.check_target(new.target);
	$.push($$props, true, DeparturesList);
	$.append_styles($$anchor, $$css);

	let groupedDepartures = $.prop($$props, 'groupedDepartures', 19, () => []),
		display = $.prop($$props, 'display', 3, undefined);

	function formatTimeRelative(departure) {
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

			if ($.strict_equals(mins, 0)) {
				return `${hours}h`;
			}

			return `${hours}h${mins}m`;
		}
	}

	function formatTimeAbsolute(departure) {
		const date = new Date(departure.time);
		const hours = date.getHours().toString().padStart(2, "0");
		const minutes = date.getMinutes().toString().padStart(2, "0");

		return `${hours}:${minutes}`;
	}

	function formatPlannedTimeRelative(departure) {
		if (!departure.plannedTime) {
			return formatTimeRelative(departure);
		}

		const now = new Date();
		const diffMs = departure.plannedTime.getTime() - now.getTime();
		const diffMinutes = Math.floor(diffMs / 60000);

		if (diffMinutes < 0) {
			return "now";
		} else if (diffMinutes < 60) {
			return `${diffMinutes}m`;
		} else {
			const hours = Math.floor(diffMinutes / 60);
			const mins = diffMinutes % 60;

			if ($.strict_equals(mins, 0)) {
				return `${hours}h`;
			}

			return `${hours}h${mins}m`;
		}
	}

	function formatPlannedTimeAbsolute(departure) {
		if (!departure.plannedTime) {
			return formatTimeAbsolute(departure);
		}

		const date = new Date(departure.plannedTime);
		const hours = date.getHours().toString().padStart(2, "0");
		const minutes = date.getMinutes().toString().padStart(2, "0");

		return `${hours}:${minutes}`;
	}

	function getDelayMinutes(departure) {
		// Match Python version: has_delay = departure.delay_seconds is not None and departure.delay_seconds > 60
		// Only delays > 60 seconds (1 minute) are considered delays
		if ($.equals(departure.delaySeconds, null, false) && departure.delaySeconds > 60) {
			// Match Python: delay_minutes = departure.delay_seconds // 60 (integer division)
			return Math.floor(departure.delaySeconds / 60);
		}

		return null;
	}

	function hasDelay(departure) {
		// Match Python: has_delay = departure.delay_seconds is not None and departure.delay_seconds > 60
		return $.equals(departure.delaySeconds, null, false) && departure.delaySeconds > 60;
	}

	function formatHeaderTime(departure) {
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

			if ($.strict_equals(mins, 0)) {
				return `(in ${hours}+ h)`;
			}

			return `(in ${hours}+ h ${mins}+ min)`;
		}
	}

	function getHeaderText(group) {
		// Format: "StopName → DirectionName (in X+ min)" if there are departures
		const baseText = `${group.stopName} → ${group.directionName}`;

		if (group.departures && group.departures.length > 0) {
			const firstDeparture = group.departures[0];
			const timeText = formatHeaderTime(firstDeparture);

			return `${baseText} ${timeText}`;
		}

		return baseText;
	}

	function getTransportTypeCss(transportType) {
		const map = {
			"U-Bahn": "ubahn",
			"S-Bahn": "sbahn",
			Bus: "bus",
			Tram: "tram"
		};

		return map[transportType] || "regional";
	}

	var $$exports = { ...$.legacy_api() };
	var fragment = $.comment();
	var node = $.first_child(fragment);

	{
		var consequent = ($$anchor) => {
			var div = root_1();

			$.append($$anchor, div);
		};

		var alternate_2 = ($$anchor) => {
			var fragment_1 = $.comment();
			var node_1 = $.first_child(fragment_1);

			$.add_svelte_meta(
				() => $.each(node_1, 17, groupedDepartures, $.index, ($$anchor, group, groupIndex) => {
					var div_1 = root_3();
					var h2 = $.child(div_1);
					var node_2 = $.child(h2);

					{
						var consequent_1 = ($$anchor) => {
							var fragment_2 = root_4();
							var span = $.first_child(fragment_2);
							var text = $.child(span, true);

							$.reset(span);

							var div_2 = $.sibling(span, 2);
							var text_1 = $.child(div_2, true);

							$.reset(div_2);

							$.template_effect(
								($0, $1) => {
									$.set_text(text, $0);
									$.set_text(text_1, $1);
								},
								[
									() => getHeaderText($.get(group)),
									() => new Date().toLocaleString("de-DE")
								]
							);

							$.append($$anchor, fragment_2);
						};

						var alternate = ($$anchor) => {
							var text_2 = $.text();

							$.template_effect(($0) => $.set_text(text_2, $0), [() => getHeaderText($.get(group))]);
							$.append($$anchor, text_2);
						};

						$.add_svelte_meta(
							() => $.if(node_2, ($$render) => {
								if ($.strict_equals(groupIndex, 0)) $$render(consequent_1); else $$render(alternate, false);
							}),
							'if',
							DeparturesList,
							141,
							8
						);
					}

					$.reset(h2);

					var ul = $.sibling(h2, 2);

					$.validate_each_keys(() => $.get(group).departures, (departure) => departure.line + departure.destination + departure.time.getTime());

					$.add_svelte_meta(
						() => $.each(ul, 21, () => $.get(group).departures, (departure) => departure.line + departure.destination + departure.time.getTime(), ($$anchor, departure) => {
							var li = root_6();
							var div_3 = $.child(li);
							var span_1 = $.child(div_3);
							var span_2 = $.child(span_1);
							var text_3 = $.child(span_2, true);

							$.reset(span_2);
							$.reset(span_1);

							var span_3 = $.sibling(span_1, 2);
							var span_4 = $.child(span_3);
							var text_4 = $.child(span_4, true);

							$.reset(span_4);
							$.reset(span_3);
							$.reset(div_3);

							var div_4 = $.sibling(div_3, 2);
							var span_5 = $.child(div_4);
							var text_5 = $.child(span_5, true);

							$.reset(span_5);

							var span_6 = $.sibling(span_5, 2);
							var node_3 = $.child(span_6);

							{
								var consequent_3 = ($$anchor) => {
									var fragment_4 = root_7();
									var text_6 = $.first_child(fragment_4);
									var node_4 = $.sibling(text_6);

									{
										var consequent_2 = ($$anchor) => {
											var span_7 = root_8();
											var text_7 = $.child(span_7);

											$.reset(span_7);
											$.template_effect(($0) => $.set_text(text_7, `+${$0 ?? ''}m`), [() => getDelayMinutes($.get(departure))]);
											$.append($$anchor, span_7);
										};

										$.add_svelte_meta(
											() => $.if(node_4, ($$render) => {
												if (getDelayMinutes($.get(departure))) $$render(consequent_2);
											}),
											'if',
											DeparturesList,
											178,
											18
										);
									}

									$.template_effect(($0) => $.set_text(text_6, `${$0 ?? ''} `), [() => formatPlannedTimeRelative($.get(departure))]);
									$.append($$anchor, fragment_4);
								};

								var alternate_1 = ($$anchor) => {
									var text_8 = $.text();

									$.template_effect(($0) => $.set_text(text_8, $0), [() => formatTimeRelative($.get(departure))]);
									$.append($$anchor, text_8);
								};

								$.add_svelte_meta(
									() => $.if(node_3, ($$render) => {
										if (display()?.splitShowDelay) $$render(consequent_3); else $$render(alternate_1, false);
									}),
									'if',
									DeparturesList,
									175,
									16
								);
							}

							$.reset(span_6);
							$.reset(div_4);

							var span_8 = $.sibling(div_4, 2);
							var text_9 = $.child(span_8);

							$.reset(span_8);
							$.reset(li);

							$.template_effect(
								($0, $1, $2, $3, $4, $5) => {
									$.set_class(li, 1, `departure-row ${$.get(departure).isCancelled ? 'cancelled' : ''}`, 'svelte-1apnbj7');
									$.set_attribute(li, 'aria-label', `${$.get(departure).transportType ?? ''} ${$.get(departure).line ?? ''} to ${$.get(departure).destination ?? ''}, ${$0 ?? ''}`);
									$.set_class(span_2, 1, `route-badge route-badge-${$1 ?? ''}`, 'svelte-1apnbj7');
									$.set_text(text_3, $.get(departure).line);
									$.set_text(text_4, $.get(departure).destination);
									$.set_attribute(div_4, 'data-time-relative', $2);
									$.set_attribute(div_4, 'data-time-absolute', $3);
									$.set_text(text_5, $.get(departure).platform || "");
									$.set_class(span_6, 1, `time ${$4 ?? ''} ${$.get(departure).isRealtime ? 'realtime' : ''}`, 'svelte-1apnbj7');
									$.set_text(text_9, `${$.get(departure).transportType ?? ''} ${$.get(departure).line ?? ''} to ${$.get(departure).destination ?? ''}, ${$5 ?? ''}`);
								},
								[
									() => formatTimeRelative($.get(departure)),
									() => getTransportTypeCss($.get(departure).transportType),
									() => display()?.splitShowDelay
										? formatPlannedTimeRelative($.get(departure))
										: formatTimeRelative($.get(departure)),

									() => display()?.splitShowDelay
										? formatPlannedTimeAbsolute($.get(departure))
										: formatTimeAbsolute($.get(departure)),
									() => hasDelay($.get(departure)) ? 'delay' : '',
									() => formatTimeRelative($.get(departure))
								]
							);

							$.append($$anchor, li);
						}),
						'each',
						DeparturesList,
						151,
						8
					);

					$.reset(ul);
					$.reset(div_1);

					$.template_effect(() => {
						$.set_style(h2, $.get(group).headerColor
							? `background-color: ${$.get(group).headerColor};`
							: undefined);

						$.set_attribute(h2, 'data-fill-vertical-space', display()?.fillVerticalSpace && $.strict_equals(groupIndex, 0) ? "true" : undefined);
						$.set_attribute(ul, 'aria-label', `Departures for ${$.get(group).directionName ?? ''}`);
					});

					$.append($$anchor, div_1);
				}),
				'each',
				DeparturesList,
				132,
				2
			);

			$.append($$anchor, fragment_1);
		};

		$.add_svelte_meta(
			() => $.if(node, ($$render) => {
				if ($.strict_equals(groupedDepartures().length, 0)) $$render(consequent); else $$render(alternate_2, false);
			}),
			'if',
			DeparturesList,
			127,
			0
		);
	}

	$.append($$anchor, fragment);

	return $.pop($$exports);
}