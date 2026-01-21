import 'svelte/internal/disclose-version';

StatusBar[$.FILENAME] = 'src/components/StatusBar.svelte';

import * as $ from 'svelte/internal/client';
import { onMount, onDestroy } from "svelte";

var root_1 = $.add_locations($.from_svg(`<svg class="api-status-icon api-success svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`), StatusBar[$.FILENAME], [[125, 6, [[126, 8]]]]);
var root_3 = $.add_locations($.from_svg(`<svg class="api-status-icon api-error svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`), StatusBar[$.FILENAME], [[129, 6, [[130, 8]]]]);
var root_5 = $.add_locations($.from_svg(`<svg class="api-status-icon api-degraded svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"></path></svg>`), StatusBar[$.FILENAME], [[133, 6, [[134, 8]]]]);
var root_6 = $.add_locations($.from_svg(`<svg class="api-status-icon api-unknown svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z"></path></svg>`), StatusBar[$.FILENAME], [[137, 6, [[138, 8]]]]);
var root_9 = $.add_locations($.from_html(`<button role="menuitem" type="button"> </button>`), StatusBar[$.FILENAME], [[202, 12]]);
var root_8 = $.add_locations($.from_html(`<div class="route-selector-dropdown svelte-161y12f" role="menu" aria-label="Available routes"></div>`), StatusBar[$.FILENAME], [[200, 8]]);
var root_7 = $.add_locations($.from_html(`<div class="route-selector-container svelte-161y12f"><button class="route-selector-button svelte-161y12f" aria-label="Select view/route" title="Select view/route" type="button" aria-haspopup="true"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true" class="svelte-161y12f"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"></path></svg></button> <!></div>`), StatusBar[$.FILENAME], [[181, 4, [[182, 6, [[194, 8, [[195, 10]]]]]]]]);

var root = $.add_locations($.from_html(`<div class="status-floating-box svelte-161y12f" role="status" aria-label="System status indicators"><div class="status-floating-box-item svelte-161y12f" id="api-status-container" role="img" title="MVG API connection status"><!></div> <div class="status-floating-box-item refresh-countdown svelte-161y12f" role="img" aria-label="Refresh countdown timer" title="Time until next data refresh"><svg viewBox="0 0 12 12" width="100%" height="100%" aria-hidden="true" class="svelte-161y12f"><circle cx="6" cy="6" r="5" class="background svelte-161y12f"></circle><circle cx="6" cy="6" r="5" class="progress svelte-161y12f" transform="rotate(-90 6 6)"></circle></svg> <span class="sr-only svelte-161y12f" id="refresh-countdown-sr">Refresh countdown timer</span></div> <button class="status-floating-box-item config-button svelte-161y12f" aria-label="Open configuration" title="Open configuration" type="button"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"></path><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg></button> <a href="https://github.com/d-led/my-mvg-departures" target="_blank" rel="noopener noreferrer" class="status-floating-box-github status-floating-box-item svelte-161y12f" aria-label="View repository on GitHub (opens in new tab)" title="View repository on GitHub"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.46-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path></svg> <span class="sr-only svelte-161y12f">View repository on GitHub</span></a>  <!></div>`), StatusBar[$.FILENAME], [
	[
		122,
		0,
		[
			[123, 2],
			[143, 2, [[144, 4, [[145, 6], [146, 6]]], [148, 4]]],
			[151, 2, [[158, 4, [[159, 6], [160, 6]]]]],
			[164, 2, [[172, 4, [[173, 6]]], [175, 4]]]
		]
	]
]);

const $$css = {
	hash: 'svelte-161y12f',
	code: '\n  .status-floating-box.svelte-161y12f {\n    position: fixed;\n    bottom: 0.5rem;\n    left: 50%;\n    transform: translateX(-50%);\n    display: flex;\n    align-items: center;\n    gap: 0.4rem;\n    padding: 0.4rem 0.6rem;\n    background-color: rgba(128, 128, 128, 0.3);\n    backdrop-filter: blur(4px);\n    border-radius: 0.4rem;\n    z-index: 1000;\n  }\n\n  /* (unused) [data-theme="light"] .status-floating-box {\n    background-color: rgba(128, 128, 128, 0.2);\n  }*/\n\n  /* (unused) [data-theme="dark"] .status-floating-box {\n    background-color: rgba(128, 128, 128, 0.4);\n  }*/\n\n  .status-floating-box-item.svelte-161y12f {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 1em;\n    height: 1em;\n    min-width: 1em;\n    min-height: 1em;\n    flex-shrink: 0;\n  }\n\n  .config-button.svelte-161y12f {\n    background: none;\n    border: none;\n    cursor: pointer;\n    padding: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    color: inherit;\n    transition: opacity 0.2s;\n  }\n\n  .config-button.svelte-161y12f:hover {\n    opacity: 0.8;\n  }\n\n  .api-status-icon.svelte-161y12f {\n    width: 100%;\n    height: 100%;\n    display: block;\n  }\n\n  .api-status-icon.api-success.svelte-161y12f {\n    color: #059669;\n  }\n\n  .api-status-icon.api-error.svelte-161y12f {\n    color: #dc2626;\n  }\n\n  .api-status-icon.api-unknown.svelte-161y12f {\n    color: rgba(255, 255, 255, 0.5);\n  }\n\n  .api-status-icon.api-degraded.svelte-161y12f {\n    color: #d97706;\n  }\n\n  .refresh-countdown.svelte-161y12f svg:where(.svelte-161y12f) {\n    width: 100%;\n    height: 100%;\n    display: block;\n  }\n\n  .refresh-countdown.svelte-161y12f circle:where(.svelte-161y12f) {\n    fill: none;\n    stroke-width: 2;\n    transition: stroke-dashoffset 0.1s linear;\n  }\n\n  /* (unused) [data-theme="light"] .refresh-countdown circle {\n    stroke: rgba(0, 0, 0, 0.3);\n  }*/\n\n  /* (unused) [data-theme="light"] .refresh-countdown circle.progress {\n    stroke: rgba(0, 0, 0, 0.8);\n  }*/\n\n  /* (unused) [data-theme="dark"] .refresh-countdown circle {\n    stroke: rgba(255, 255, 255, 0.3);\n  }*/\n\n  /* (unused) [data-theme="dark"] .refresh-countdown circle.progress {\n    stroke: rgba(255, 255, 255, 0.8);\n  }*/\n\n  .status-floating-box-github.svelte-161y12f {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 1em;\n    height: 1em;\n    min-width: 1em;\n    min-height: 1em;\n    flex-shrink: 0;\n    text-decoration: none;\n    transition: opacity 0.2s;\n  }\n\n  .status-floating-box-github.svelte-161y12f:hover {\n    opacity: 0.8;\n  }\n\n  .sr-only.svelte-161y12f {\n    position: absolute;\n    width: 1px;\n    height: 1px;\n    padding: 0;\n    margin: -1px;\n    overflow: hidden;\n    clip: rect(0, 0, 0, 0);\n    white-space: nowrap;\n    border-width: 0;\n  }\n\n  .route-selector-container.svelte-161y12f {\n    position: relative;\n    width: 1.2em !important;\n    height: 1.2em !important;\n    min-width: 1.2em !important;\n    min-height: 1.2em !important;\n  }\n\n  .route-selector-button.svelte-161y12f {\n    background: none;\n    border: none;\n    cursor: pointer;\n    padding: 0.1em;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    color: inherit;\n    transition: opacity 0.2s;\n    width: 1.2em;\n    height: 1.2em;\n    min-width: 1.2em;\n    min-height: 1.2em;\n    opacity: 0.9;\n  }\n\n  .route-selector-button.svelte-161y12f:hover {\n    opacity: 0.8;\n  }\n\n  .route-selector-button.svelte-161y12f svg:where(.svelte-161y12f) {\n    width: 100%;\n    height: 100%;\n    display: block;\n  }\n\n  .route-selector-dropdown.svelte-161y12f {\n    position: absolute;\n    bottom: calc(100% + 0.5rem);\n    right: 0;\n    background: white;\n    border-radius: 0.375rem;\n    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);\n    min-width: 150px;\n    z-index: 1000;\n    overflow: hidden;\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-dropdown {\n    background: #1d232a;\n    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);\n  }*/\n\n  .route-selector-item.svelte-161y12f {\n    display: block;\n    width: 100%;\n    padding: 0.5rem 0.75rem;\n    text-align: left;\n    background: none;\n    border: none;\n    cursor: pointer;\n    color: #111827;\n    font-size: 0.875rem;\n    transition: background-color 0.2s;\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-item {\n    color: #f9fafb;\n  }*/\n\n  .route-selector-item.svelte-161y12f:hover {\n    background-color: rgba(0, 0, 0, 0.05);\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-item:hover {\n    background-color: rgba(255, 255, 255, 0.1);\n  }*/\n\n  .route-selector-item.active.svelte-161y12f {\n    background-color: rgba(8, 123, 196, 0.1);\n    font-weight: 600;\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-item.active {\n    background-color: rgba(8, 123, 196, 0.2);\n  }*/\n\n/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiU3RhdHVzQmFyLnN2ZWx0ZSIsInNvdXJjZXMiOlsiU3RhdHVzQmFyLnN2ZWx0ZSJdLCJzb3VyY2VzQ29udGVudCI6WyI8c2NyaXB0IGxhbmc9XCJ0c1wiPlxuICBpbXBvcnQgeyBvbk1vdW50LCBvbkRlc3Ryb3kgfSBmcm9tIFwic3ZlbHRlXCI7XG4gIGltcG9ydCB0eXBlIHsgUm91dGVDb25maWd1cmF0aW9uIH0gZnJvbSBcIi4uL2RvbWFpbi9tb2RlbHMvaW5kZXguanNcIjtcblxuICBsZXQge1xuICAgIGFwaVN0YXR1cyxcbiAgICBzaG93Q29uZmlnTW9kYWwsXG4gICAgb25Db25maWdDbGljayxcbiAgICByb3V0ZXMgPSBbXSxcbiAgICBjdXJyZW50Um91dGVQYXRoID0gbnVsbCxcbiAgICBvblJvdXRlQ2hhbmdlID0gKCkgPT4ge30sXG4gICAgcmVmcmVzaEludGVydmFsU2Vjb25kcyA9IDIwLFxuICB9OiB7XG4gICAgYXBpU3RhdHVzOiBcInN1Y2Nlc3NcIiB8IFwiZXJyb3JcIiB8IFwiZGVncmFkZWRcIiB8IFwidW5rbm93blwiO1xuICAgIHNob3dDb25maWdNb2RhbDogYm9vbGVhbjtcbiAgICBvbkNvbmZpZ0NsaWNrOiAoKSA9PiB2b2lkO1xuICAgIHJvdXRlcz86IFJvdXRlQ29uZmlndXJhdGlvbltdO1xuICAgIGN1cnJlbnRSb3V0ZVBhdGg/OiBzdHJpbmcgfCBudWxsO1xuICAgIG9uUm91dGVDaGFuZ2U/OiAocGF0aDogc3RyaW5nKSA9PiB2b2lkO1xuICAgIHJlZnJlc2hJbnRlcnZhbFNlY29uZHM/OiBudW1iZXI7XG4gIH0gPSAkcHJvcHMoKTtcbiAgXG4gIGxldCBzaG93Um91dGVTZWxlY3RvciA9ICRzdGF0ZShmYWxzZSk7XG4gIGxldCBjb3VudGRvd25FbGFwc2VkID0gJHN0YXRlKDApO1xuICBsZXQgY291bnRkb3duSW50ZXJ2YWw6IG51bWJlciB8IG51bGwgPSBudWxsO1xuICBsZXQgY291bnRkb3duQ2lyY2xlOiBTVkdFbGVtZW50IHwgbnVsbCA9IG51bGw7XG4gIGNvbnN0IHJhZGl1cyA9IDU7XG4gIGNvbnN0IGNpcmN1bWZlcmVuY2UgPSAyICogTWF0aC5QSSAqIHJhZGl1cztcblxuICBmdW5jdGlvbiB0b2dnbGVSb3V0ZVNlbGVjdG9yKCkge1xuICAgIHNob3dSb3V0ZVNlbGVjdG9yID0gIXNob3dSb3V0ZVNlbGVjdG9yO1xuICB9XG5cbiAgZnVuY3Rpb24gc2VsZWN0Um91dGUocGF0aDogc3RyaW5nKSB7XG4gICAgb25Sb3V0ZUNoYW5nZShwYXRoKTtcbiAgICBzaG93Um91dGVTZWxlY3RvciA9IGZhbHNlO1xuICB9XG5cbiAgZnVuY3Rpb24gc3RhcnRDb3VudGRvd24oKSB7XG4gICAgLy8gQ2xlYXIgYW55IGV4aXN0aW5nIGludGVydmFsXG4gICAgaWYgKGNvdW50ZG93bkludGVydmFsICE9PSBudWxsKSB7XG4gICAgICBjbGVhckludGVydmFsKGNvdW50ZG93bkludGVydmFsKTtcbiAgICAgIGNvdW50ZG93bkludGVydmFsID0gbnVsbDtcbiAgICB9XG5cbiAgICAvLyBGaW5kIHRoZSBjb3VudGRvd24gY2lyY2xlXG4gICAgY29uc3QgY2lyY2xlRWwgPSBkb2N1bWVudC5xdWVyeVNlbGVjdG9yKFwiLnJlZnJlc2gtY291bnRkb3duIGNpcmNsZS5wcm9ncmVzc1wiKSBhcyBTVkdFbGVtZW50O1xuICAgIGlmICghY2lyY2xlRWwpIHtcbiAgICAgIC8vIFJldHJ5IGFmdGVyIGEgc2hvcnQgZGVsYXkgaWYgZWxlbWVudCBub3QgZm91bmRcbiAgICAgIHNldFRpbWVvdXQoc3RhcnRDb3VudGRvd24sIDEwMCk7XG4gICAgICByZXR1cm47XG4gICAgfVxuICAgIGNvdW50ZG93bkNpcmNsZSA9IGNpcmNsZUVsO1xuXG4gICAgLy8gU2V0IHVwIHRoZSBjaXJjbGVcbiAgICBjaXJjbGVFbC5zZXRBdHRyaWJ1dGUoXCJzdHJva2UtZGFzaGFycmF5XCIsIGNpcmN1bWZlcmVuY2UudG9TdHJpbmcoKSk7XG4gICAgY291bnRkb3duRWxhcHNlZCA9IDA7XG4gICAgY2lyY2xlRWwuc2V0QXR0cmlidXRlKFwic3Ryb2tlLWRhc2hvZmZzZXRcIiwgXCIwXCIpO1xuXG4gICAgY29uc3QgdXBkYXRlSW50ZXJ2YWwgPSAxMDA7IC8vIFVwZGF0ZSBldmVyeSAxMDBtcyBmb3Igc21vb3RoIGFuaW1hdGlvblxuXG4gICAgZnVuY3Rpb24gdXBkYXRlQ291bnRkb3duKCkge1xuICAgICAgaWYgKCFjb3VudGRvd25DaXJjbGUpIHJldHVybjtcblxuICAgICAgY291bnRkb3duRWxhcHNlZCArPSB1cGRhdGVJbnRlcnZhbDtcbiAgICAgIGNvbnN0IHByb2dyZXNzID0gY291bnRkb3duRWxhcHNlZCAvIChyZWZyZXNoSW50ZXJ2YWxTZWNvbmRzICogMTAwMCk7XG4gICAgICBjb25zdCBvZmZzZXQgPSBjaXJjdW1mZXJlbmNlICogKDEgLSBwcm9ncmVzcyk7XG4gICAgICBjb3VudGRvd25DaXJjbGUuc2V0QXR0cmlidXRlKFwic3Ryb2tlLWRhc2hvZmZzZXRcIiwgb2Zmc2V0LnRvU3RyaW5nKCkpO1xuXG4gICAgICAvLyBVcGRhdGUgc2NyZWVuIHJlYWRlciB0ZXh0IHdpdGggcmVtYWluaW5nIHRpbWVcbiAgICAgIGNvbnN0IHJlbWFpbmluZ1NlY29uZHMgPSBNYXRoLmNlaWwoKHJlZnJlc2hJbnRlcnZhbFNlY29uZHMgKiAxMDAwIC0gY291bnRkb3duRWxhcHNlZCkgLyAxMDAwKTtcbiAgICAgIGNvbnN0IHNyVGV4dCA9IGRvY3VtZW50LmdldEVsZW1lbnRCeUlkKFwicmVmcmVzaC1jb3VudGRvd24tc3JcIik7XG4gICAgICBpZiAoc3JUZXh0ICYmIHJlbWFpbmluZ1NlY29uZHMgPiAwKSB7XG4gICAgICAgIHNyVGV4dC50ZXh0Q29udGVudCA9IGBSZWZyZXNoIGNvdW50ZG93bjogJHtyZW1haW5pbmdTZWNvbmRzfSBzZWNvbmRzIHJlbWFpbmluZ2A7XG4gICAgICB9XG5cbiAgICAgIC8vIFdoZW4gY291bnRkb3duIHJlYWNoZXMgdGhlIGVuZCwgcmVzZXRcbiAgICAgIGlmIChjb3VudGRvd25FbGFwc2VkID49IHJlZnJlc2hJbnRlcnZhbFNlY29uZHMgKiAxMDAwKSB7XG4gICAgICAgIGNvdW50ZG93bkVsYXBzZWQgPSAwO1xuICAgICAgICBpZiAoc3JUZXh0KSB7XG4gICAgICAgICAgc3JUZXh0LnRleHRDb250ZW50ID0gXCJSZWZyZXNoIGNvdW50ZG93bjogdXBkYXRpbmdcIjtcbiAgICAgICAgfVxuICAgICAgfVxuICAgIH1cblxuICAgIGNvdW50ZG93bkludGVydmFsID0gd2luZG93LnNldEludGVydmFsKHVwZGF0ZUNvdW50ZG93biwgdXBkYXRlSW50ZXJ2YWwpO1xuICB9XG5cbiAgb25Nb3VudCgoKSA9PiB7XG4gICAgLy8gU3RhcnQgY291bnRkb3duIHdoZW4gY29tcG9uZW50IG1vdW50c1xuICAgIHN0YXJ0Q291bnRkb3duKCk7XG4gIH0pO1xuXG4gIG9uRGVzdHJveSgoKSA9PiB7XG4gICAgLy8gQ2xlYW4gdXAgaW50ZXJ2YWwgb24gY29tcG9uZW50IGRlc3Ryb3lcbiAgICBpZiAoY291bnRkb3duSW50ZXJ2YWwgIT09IG51bGwpIHtcbiAgICAgIGNsZWFySW50ZXJ2YWwoY291bnRkb3duSW50ZXJ2YWwpO1xuICAgICAgY291bnRkb3duSW50ZXJ2YWwgPSBudWxsO1xuICAgIH1cbiAgfSk7XG5cbiAgLy8gUmVzdGFydCBjb3VudGRvd24gd2hlbiByZWZyZXNoIGludGVydmFsIGNoYW5nZXMgb3Igd2hlbiBBUEkgc3RhdHVzIGNoYW5nZXMgKG5ldyB1cGRhdGUpXG4gICRlZmZlY3QoKCkgPT4ge1xuICAgIC8vIEFjY2VzcyByZWFjdGl2ZSB2YWx1ZXMgdG8gdHJpZ2dlciBlZmZlY3RcbiAgICBjb25zdCBfID0gcmVmcmVzaEludGVydmFsU2Vjb25kcztcbiAgICBjb25zdCBfXyA9IGFwaVN0YXR1cztcbiAgICBcbiAgICAvLyBSZXN0YXJ0IGNvdW50ZG93biB3aGVuIGludGVydmFsIGNoYW5nZXMgb3Igb24gc3VjY2Vzc2Z1bCB1cGRhdGVcbiAgICBpZiAoYXBpU3RhdHVzID09PSBcInN1Y2Nlc3NcIikge1xuICAgICAgc3RhcnRDb3VudGRvd24oKTtcbiAgICB9XG4gIH0pO1xuPC9zY3JpcHQ+XG5cbjxzdmVsdGU6d2luZG93IG9uY2xpY2s9eyhlKSA9PiB7XG4gIGNvbnN0IHRhcmdldCA9IGUudGFyZ2V0IGFzIEhUTUxFbGVtZW50O1xuICBpZiAoc2hvd1JvdXRlU2VsZWN0b3IgJiYgIXRhcmdldC5jbG9zZXN0KFwiLnJvdXRlLXNlbGVjdG9yLWNvbnRhaW5lclwiKSkge1xuICAgIHNob3dSb3V0ZVNlbGVjdG9yID0gZmFsc2U7XG4gIH1cbn19IC8+XG5cbjxkaXYgY2xhc3M9XCJzdGF0dXMtZmxvYXRpbmctYm94XCIgcm9sZT1cInN0YXR1c1wiIGFyaWEtbGFiZWw9XCJTeXN0ZW0gc3RhdHVzIGluZGljYXRvcnNcIj5cbiAgPGRpdiBjbGFzcz1cInN0YXR1cy1mbG9hdGluZy1ib3gtaXRlbVwiIGlkPVwiYXBpLXN0YXR1cy1jb250YWluZXJcIiByb2xlPVwiaW1nXCIgYXJpYS1sYWJlbD1cIkFQSSBzdGF0dXM6IHthcGlTdGF0dXN9XCIgdGl0bGU9XCJNVkcgQVBJIGNvbm5lY3Rpb24gc3RhdHVzXCI+XG4gICAgeyNpZiBhcGlTdGF0dXMgPT09IFwic3VjY2Vzc1wifVxuICAgICAgPHN2ZyBjbGFzcz1cImFwaS1zdGF0dXMtaWNvbiBhcGktc3VjY2Vzc1wiIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiBmaWxsPVwibm9uZVwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBzdHJva2Utd2lkdGg9XCIyXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICAgIDxwYXRoIHN0cm9rZS1saW5lY2FwPVwicm91bmRcIiBzdHJva2UtbGluZWpvaW49XCJyb3VuZFwiIGQ9XCJNOSAxMi43NUwxMS4yNSAxNSAxNSA5Ljc1TTIxIDEyYTkgOSAwIDExLTE4IDAgOSA5IDAgMDExOCAwelwiIC8+XG4gICAgICA8L3N2Zz5cbiAgICB7OmVsc2UgaWYgYXBpU3RhdHVzID09PSBcImVycm9yXCJ9XG4gICAgICA8c3ZnIGNsYXNzPVwiYXBpLXN0YXR1cy1pY29uIGFwaS1lcnJvclwiIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiBmaWxsPVwibm9uZVwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBzdHJva2Utd2lkdGg9XCIyXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICAgIDxwYXRoIHN0cm9rZS1saW5lY2FwPVwicm91bmRcIiBzdHJva2UtbGluZWpvaW49XCJyb3VuZFwiIGQ9XCJNOS43NSA5Ljc1bDQuNSA0LjVtMC00LjVsLTQuNSA0LjVNMjEgMTJhOSA5IDAgMTEtMTggMCA5IDkgMCAwMTE4IDB6XCIgLz5cbiAgICAgIDwvc3ZnPlxuICAgIHs6ZWxzZSBpZiBhcGlTdGF0dXMgPT09IFwiZGVncmFkZWRcIn1cbiAgICAgIDxzdmcgY2xhc3M9XCJhcGktc3RhdHVzLWljb24gYXBpLWRlZ3JhZGVkXCIgeG1sbnM9XCJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2Z1wiIGZpbGw9XCJub25lXCIgdmlld0JveD1cIjAgMCAyNCAyNFwiIHN0cm9rZS13aWR0aD1cIjJcIiBzdHJva2U9XCJjdXJyZW50Q29sb3JcIiBhcmlhLWhpZGRlbj1cInRydWVcIj5cbiAgICAgICAgPHBhdGggc3Ryb2tlLWxpbmVjYXA9XCJyb3VuZFwiIHN0cm9rZS1saW5lam9pbj1cInJvdW5kXCIgZD1cIk0xMiA5djMuNzVtLTkuMzAzIDMuMzc2Yy0uODY2IDEuNS4yMTcgMy4zNzQgMS45NDggMy4zNzRoMTQuNzFjMS43MyAwIDIuODEzLTEuODc0IDEuOTQ4LTMuMzc0TDEzLjk0OSAzLjM3OGMtLjg2Ni0xLjUtMy4wMzItMS41LTMuODk4IDBMMi42OTcgMTYuMTI2ek0xMiAxNS43NWguMDA3di4wMDhIMTJ2LS4wMDh6XCIgLz5cbiAgICAgIDwvc3ZnPlxuICAgIHs6ZWxzZX1cbiAgICAgIDxzdmcgY2xhc3M9XCJhcGktc3RhdHVzLWljb24gYXBpLXVua25vd25cIiB4bWxucz1cImh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnXCIgZmlsbD1cIm5vbmVcIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgc3Ryb2tlLXdpZHRoPVwiMlwiIHN0cm9rZT1cImN1cnJlbnRDb2xvclwiIGFyaWEtaGlkZGVuPVwidHJ1ZVwiPlxuICAgICAgICA8cGF0aCBzdHJva2UtbGluZWNhcD1cInJvdW5kXCIgc3Ryb2tlLWxpbmVqb2luPVwicm91bmRcIiBkPVwiTTkuODc5IDcuNTE5YzEuMTcxLTEuMDI1IDMuMDcxLTEuMDI1IDQuMjQyIDAgMS4xNzIgMS4wMjUgMS4xNzIgMi42ODcgMCAzLjcxMi0uMjAzLjE3OS0uNDMuMzI2LS42Ny40NDItLjc0NS4zNjEtMS40NS45OTktMS40NSAxLjgyN3YuNzVNMjEgMTJhOSA5IDAgMTEtMTggMCA5IDkgMCAwMTE4IDB6bS05IDUuMjVoLjAwOHYuMDA4SDEydi0uMDA4elwiIC8+XG4gICAgICA8L3N2Zz5cbiAgICB7L2lmfVxuICA8L2Rpdj5cblxuICA8ZGl2IGNsYXNzPVwic3RhdHVzLWZsb2F0aW5nLWJveC1pdGVtIHJlZnJlc2gtY291bnRkb3duXCIgcm9sZT1cImltZ1wiIGFyaWEtbGFiZWw9XCJSZWZyZXNoIGNvdW50ZG93biB0aW1lclwiIHRpdGxlPVwiVGltZSB1bnRpbCBuZXh0IGRhdGEgcmVmcmVzaFwiPlxuICAgIDxzdmcgdmlld0JveD1cIjAgMCAxMiAxMlwiIHdpZHRoPVwiMTAwJVwiIGhlaWdodD1cIjEwMCVcIiBhcmlhLWhpZGRlbj1cInRydWVcIj5cbiAgICAgIDxjaXJjbGUgY3g9XCI2XCIgY3k9XCI2XCIgcj1cIjVcIiBjbGFzcz1cImJhY2tncm91bmRcIj48L2NpcmNsZT5cbiAgICAgIDxjaXJjbGUgY3g9XCI2XCIgY3k9XCI2XCIgcj1cIjVcIiBjbGFzcz1cInByb2dyZXNzXCIgdHJhbnNmb3JtPVwicm90YXRlKC05MCA2IDYpXCI+PC9jaXJjbGU+XG4gICAgPC9zdmc+XG4gICAgPHNwYW4gY2xhc3M9XCJzci1vbmx5XCIgaWQ9XCJyZWZyZXNoLWNvdW50ZG93bi1zclwiPlJlZnJlc2ggY291bnRkb3duIHRpbWVyPC9zcGFuPlxuICA8L2Rpdj5cblxuICA8YnV0dG9uXG4gICAgY2xhc3M9XCJzdGF0dXMtZmxvYXRpbmctYm94LWl0ZW0gY29uZmlnLWJ1dHRvblwiXG4gICAgb25jbGljaz17b25Db25maWdDbGlja31cbiAgICBhcmlhLWxhYmVsPVwiT3BlbiBjb25maWd1cmF0aW9uXCJcbiAgICB0aXRsZT1cIk9wZW4gY29uZmlndXJhdGlvblwiXG4gICAgdHlwZT1cImJ1dHRvblwiXG4gID5cbiAgICA8c3ZnIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiBmaWxsPVwibm9uZVwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBzdHJva2Utd2lkdGg9XCIyXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICA8cGF0aCBzdHJva2UtbGluZWNhcD1cInJvdW5kXCIgc3Ryb2tlLWxpbmVqb2luPVwicm91bmRcIiBkPVwiTTkuNTk0IDMuOTRjLjA5LS41NDIuNTYtLjk0IDEuMTEtLjk0aDIuNTkzYy41NSAwIDEuMDIuMzk4IDEuMTEuOTRsLjIxMyAxLjI4MWMuMDYzLjM3NC4zMTMuNjg2LjY0NS44Ny4wNzQuMDQuMTQ3LjA4My4yMi4xMjcuMzI0LjE5Ni43Mi4yNTcgMS4wNzUuMTI0bDEuMjE3LS40NTZhMS4xMjUgMS4xMjUgMCAwMTEuMzcuNDlsMS4yOTYgMi4yNDdhMS4xMjUgMS4xMjUgMCAwMS0uMjYgMS40MzFsLTEuMDAzLjgyN2MtLjI5My4yNC0uNDM4LjYxMy0uNDMxLjk5MmE2Ljc1OSA2Ljc1OSAwIDAxMCAuMjU1Yy0uMDA3LjM3OC4xMzguNzUuNDMuOTlsMS4wMDUuODI4Yy40MjQuMzUuNTM0Ljk1NC4yNiAxLjQzbC0xLjI5OCAyLjI0N2ExLjEyNSAxLjEyNSAwIDAxLTEuMzY5LjQ5MWwtMS4yMTctLjQ1NmMtLjM1NS0uMTMzLS43NS0uMDcyLTEuMDc2LjEyNGE2LjU3IDYuNTcgMCAwMS0uMjIuMTI4Yy0uMzMxLjE4My0uNTgxLjQ5NS0uNjQ0Ljg2OWwtLjIxMyAxLjI4Yy0uMDkuNTQzLS41Ni45NDEtMS4xMS45NDFoLTIuNTk0Yy0uNTUgMC0xLjAyLS4zOTgtMS4xMS0uOTRsLS4yMTMtMS4yODFjLS4wNjItLjM3NC0uMzEyLS42ODYtLjY0NC0uODdhNi41MiA2LjUyIDAgMDEtLjIyLS4xMjdjLS4zMjUtLjE5Ni0uNzItLjI1Ny0xLjA3Ni0uMTI0bC0xLjIxNy40NTZhMS4xMjUgMS4xMjUgMCAwMS0xLjM2OS0uNDlsLTEuMjk3LTIuMjQ3YTEuMTI1IDEuMTI1IDAgMDEuMjYtMS40MzFsMS4wMDQtLjgyN2MuMjkyLS4yNC40MzctLjYxMy40My0uOTkyYTYuOTMyIDYuOTMyIDAgMDEwLS4yNTVjLjAwNy0uMzc4LS4xMzgtLjc1LS40My0uOTlsLTEuMDA0LS44MjhhMS4xMjUgMS4xMjUgMCAwMS0uMjYtMS40M2wxLjI5Ny0yLjI0N2ExLjEyNSAxLjEyNSAwIDAxMS4zNy0uNDkxbDEuMjE2LjQ1NmMuMzU2LjEzMy43NTEuMDcyIDEuMDc2LS4xMjQuMDcyLS4wNDQuMTQ2LS4wODcuMjItLjEyOC4zMzItLjE4My41ODItLjQ5NS42NDQtLjg2OWwuMjE0LTEuMjgxelwiIC8+XG4gICAgICA8cGF0aCBzdHJva2UtbGluZWNhcD1cInJvdW5kXCIgc3Ryb2tlLWxpbmVqb2luPVwicm91bmRcIiBkPVwiTTE1IDEyYTMgMyAwIDExLTYgMCAzIDMgMCAwMTYgMHpcIiAvPlxuICAgIDwvc3ZnPlxuICA8L2J1dHRvbj5cblxuICA8YVxuICAgIGhyZWY9XCJodHRwczovL2dpdGh1Yi5jb20vZC1sZWQvbXktbXZnLWRlcGFydHVyZXNcIlxuICAgIHRhcmdldD1cIl9ibGFua1wiXG4gICAgcmVsPVwibm9vcGVuZXIgbm9yZWZlcnJlclwiXG4gICAgY2xhc3M9XCJzdGF0dXMtZmxvYXRpbmctYm94LWdpdGh1YiBzdGF0dXMtZmxvYXRpbmctYm94LWl0ZW1cIlxuICAgIGFyaWEtbGFiZWw9XCJWaWV3IHJlcG9zaXRvcnkgb24gR2l0SHViIChvcGVucyBpbiBuZXcgdGFiKVwiXG4gICAgdGl0bGU9XCJWaWV3IHJlcG9zaXRvcnkgb24gR2l0SHViXCJcbiAgPlxuICAgIDxzdmcgeG1sbnM9XCJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2Z1wiIHdpZHRoPVwiMTZcIiBoZWlnaHQ9XCIxNlwiIHZpZXdCb3g9XCIwIDAgMTYgMTZcIiBmaWxsPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICA8cGF0aCBkPVwiTTggMGM0LjQyIDAgOCAzLjU4IDggOGE4LjAxMyA4LjAxMyAwIDAgMS01LjQ1IDcuNTljLS40LjA4LS41NS0uMTctLjU1LS4zOCAwLS4yNy4wMS0xLjEzLjAxLTIuMiAwLS43NS0uMjUtMS4yMy0uNTQtMS40OCAxLjc4LS4yIDMuNjUtLjg4IDMuNjUtMy45NSAwLS44OC0uMzEtMS41OS0uODItMi4xNS4wOC0uMi4zNi0xLjAyLS4wOC0yLjEyIDAgMC0uNjctLjIyLTIuMi44Mi0uNjQtLjE4LTEuMzItLjI3LTItLjI3LS42OCAwLTEuMzYuMDktMiAuMjctMS41My0xLjAzLTIuMi0uODItMi4yLS44Mi0uNDQgMS4xLS4xNiAxLjkyLS4wOCAyLjEyLS41MS41Ni0uODIgMS4yOC0uODIgMi4xNSAwIDMuMDYgMS44NiAzLjc1IDMuNjQgMy45NS0uMjMuMi0uNDQuNTUtLjUxIDEuMDctLjQ2LjIxLTEuNjEuNTUtMi4zMy0uNjYtLjE1LS4yNC0uNi0uODMtMS4yMy0uODItLjY3LjAxLS4yNy4zOC4wMS41My4zNC4xOS43My45LjgyIDEuMTMuMTYuNDUuNjggMS4zMSAyLjY5Ljk0IDAgLjY3LjAxIDEuMy4wMSAxLjQ5IDAgLjIxLS4xNS40Ni0uNTUuMzhBNy45OTUgNy45OTUgMCAwIDEgMCA4YzAtNC40MiAzLjU4LTggOC04WlwiLz5cbiAgICA8L3N2Zz5cbiAgICA8c3BhbiBjbGFzcz1cInNyLW9ubHlcIj5WaWV3IHJlcG9zaXRvcnkgb24gR2l0SHViPC9zcGFuPlxuICA8L2E+XG4gIFxuICA8IS0tIFJvdXRlIHNlbGVjdG9yIChyZXBsYWNlcyBwcmVzZW5jZSBjb3VudGVyKSAtLT5cbiAgPCEtLSBEZWJ1Zzogcm91dGVzLmxlbmd0aCA9IHtyb3V0ZXMubGVuZ3RofSwgY3VycmVudFJvdXRlUGF0aCA9IHtjdXJyZW50Um91dGVQYXRofSAtLT5cbiAgeyNpZiByb3V0ZXMubGVuZ3RoID4gMX1cbiAgICA8ZGl2IGNsYXNzPVwicm91dGUtc2VsZWN0b3ItY29udGFpbmVyXCI+XG4gICAgICA8YnV0dG9uXG4gICAgICAgIGNsYXNzPVwicm91dGUtc2VsZWN0b3ItYnV0dG9uXCJcbiAgICAgICAgb25jbGljaz17KGUpID0+IHtcbiAgICAgICAgICBlLnN0b3BQcm9wYWdhdGlvbigpO1xuICAgICAgICAgIHRvZ2dsZVJvdXRlU2VsZWN0b3IoKTtcbiAgICAgICAgfX1cbiAgICAgICAgYXJpYS1sYWJlbD1cIlNlbGVjdCB2aWV3L3JvdXRlXCJcbiAgICAgICAgdGl0bGU9XCJTZWxlY3Qgdmlldy9yb3V0ZVwiXG4gICAgICAgIHR5cGU9XCJidXR0b25cIlxuICAgICAgICBhcmlhLWV4cGFuZGVkPXtzaG93Um91dGVTZWxlY3Rvcn1cbiAgICAgICAgYXJpYS1oYXNwb3B1cD1cInRydWVcIlxuICAgICAgPlxuICAgICAgICA8c3ZnIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiBmaWxsPVwibm9uZVwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBzdHJva2Utd2lkdGg9XCIyXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICAgICAgPHBhdGggc3Ryb2tlLWxpbmVjYXA9XCJyb3VuZFwiIHN0cm9rZS1saW5lam9pbj1cInJvdW5kXCIgZD1cIk0zLjc1IDYuNzVoMTYuNU0zLjc1IDEyaDE2LjVtLTE2LjUgNS4yNWgxNi41XCIgLz5cbiAgICAgICAgPC9zdmc+XG4gICAgICA8L2J1dHRvbj5cbiAgICAgIFxuICAgICAgeyNpZiBzaG93Um91dGVTZWxlY3Rvcn1cbiAgICAgICAgPGRpdiBjbGFzcz1cInJvdXRlLXNlbGVjdG9yLWRyb3Bkb3duXCIgcm9sZT1cIm1lbnVcIiBhcmlhLWxhYmVsPVwiQXZhaWxhYmxlIHJvdXRlc1wiIG9uY2xpY2s9eyhlKSA9PiBlLnN0b3BQcm9wYWdhdGlvbigpfT5cbiAgICAgICAgICB7I2VhY2ggcm91dGVzIGFzIHJvdXRlfVxuICAgICAgICAgICAgPGJ1dHRvblxuICAgICAgICAgICAgICBjbGFzcz1cInJvdXRlLXNlbGVjdG9yLWl0ZW0ge2N1cnJlbnRSb3V0ZVBhdGggPT09IHJvdXRlLnBhdGggPyAnYWN0aXZlJyA6ICcnfVwiXG4gICAgICAgICAgICAgIG9uY2xpY2s9eygpID0+IHNlbGVjdFJvdXRlKHJvdXRlLnBhdGgpfVxuICAgICAgICAgICAgICByb2xlPVwibWVudWl0ZW1cIlxuICAgICAgICAgICAgICB0eXBlPVwiYnV0dG9uXCJcbiAgICAgICAgICAgID5cbiAgICAgICAgICAgICAge3JvdXRlLmRpc3BsYXk/LnRpdGxlIHx8IHJvdXRlLnBhdGggfHwgXCJEZWZhdWx0XCJ9XG4gICAgICAgICAgICA8L2J1dHRvbj5cbiAgICAgICAgICB7L2VhY2h9XG4gICAgICAgIDwvZGl2PlxuICAgICAgey9pZn1cbiAgICA8L2Rpdj5cbiAgey9pZn1cbjwvZGl2PlxuXG48c3R5bGU+XG4gIC5zdGF0dXMtZmxvYXRpbmctYm94IHtcbiAgICBwb3NpdGlvbjogZml4ZWQ7XG4gICAgYm90dG9tOiAwLjVyZW07XG4gICAgbGVmdDogNTAlO1xuICAgIHRyYW5zZm9ybTogdHJhbnNsYXRlWCgtNTAlKTtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAgZ2FwOiAwLjRyZW07XG4gICAgcGFkZGluZzogMC40cmVtIDAuNnJlbTtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiByZ2JhKDEyOCwgMTI4LCAxMjgsIDAuMyk7XG4gICAgYmFja2Ryb3AtZmlsdGVyOiBibHVyKDRweCk7XG4gICAgYm9yZGVyLXJhZGl1czogMC40cmVtO1xuICAgIHotaW5kZXg6IDEwMDA7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImxpZ2h0XCJdIC5zdGF0dXMtZmxvYXRpbmctYm94IHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiByZ2JhKDEyOCwgMTI4LCAxMjgsIDAuMik7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImRhcmtcIl0gLnN0YXR1cy1mbG9hdGluZy1ib3gge1xuICAgIGJhY2tncm91bmQtY29sb3I6IHJnYmEoMTI4LCAxMjgsIDEyOCwgMC40KTtcbiAgfVxuXG4gIC5zdGF0dXMtZmxvYXRpbmctYm94LWl0ZW0ge1xuICAgIGRpc3BsYXk6IGZsZXg7XG4gICAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjtcbiAgICB3aWR0aDogMWVtO1xuICAgIGhlaWdodDogMWVtO1xuICAgIG1pbi13aWR0aDogMWVtO1xuICAgIG1pbi1oZWlnaHQ6IDFlbTtcbiAgICBmbGV4LXNocmluazogMDtcbiAgfVxuXG4gIC5jb25maWctYnV0dG9uIHtcbiAgICBiYWNrZ3JvdW5kOiBub25lO1xuICAgIGJvcmRlcjogbm9uZTtcbiAgICBjdXJzb3I6IHBvaW50ZXI7XG4gICAgcGFkZGluZzogMDtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7XG4gICAgY29sb3I6IGluaGVyaXQ7XG4gICAgdHJhbnNpdGlvbjogb3BhY2l0eSAwLjJzO1xuICB9XG5cbiAgLmNvbmZpZy1idXR0b246aG92ZXIge1xuICAgIG9wYWNpdHk6IDAuODtcbiAgfVxuXG4gIC5hcGktc3RhdHVzLWljb24ge1xuICAgIHdpZHRoOiAxMDAlO1xuICAgIGhlaWdodDogMTAwJTtcbiAgICBkaXNwbGF5OiBibG9jaztcbiAgfVxuXG4gIC5hcGktc3RhdHVzLWljb24uYXBpLXN1Y2Nlc3Mge1xuICAgIGNvbG9yOiAjMDU5NjY5O1xuICB9XG5cbiAgLmFwaS1zdGF0dXMtaWNvbi5hcGktZXJyb3Ige1xuICAgIGNvbG9yOiAjZGMyNjI2O1xuICB9XG5cbiAgLmFwaS1zdGF0dXMtaWNvbi5hcGktdW5rbm93biB7XG4gICAgY29sb3I6IHJnYmEoMjU1LCAyNTUsIDI1NSwgMC41KTtcbiAgfVxuXG4gIC5hcGktc3RhdHVzLWljb24uYXBpLWRlZ3JhZGVkIHtcbiAgICBjb2xvcjogI2Q5NzcwNjtcbiAgfVxuXG4gIC5yZWZyZXNoLWNvdW50ZG93biBzdmcge1xuICAgIHdpZHRoOiAxMDAlO1xuICAgIGhlaWdodDogMTAwJTtcbiAgICBkaXNwbGF5OiBibG9jaztcbiAgfVxuXG4gIC5yZWZyZXNoLWNvdW50ZG93biBjaXJjbGUge1xuICAgIGZpbGw6IG5vbmU7XG4gICAgc3Ryb2tlLXdpZHRoOiAyO1xuICAgIHRyYW5zaXRpb246IHN0cm9rZS1kYXNob2Zmc2V0IDAuMXMgbGluZWFyO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJsaWdodFwiXSAucmVmcmVzaC1jb3VudGRvd24gY2lyY2xlIHtcbiAgICBzdHJva2U6IHJnYmEoMCwgMCwgMCwgMC4zKTtcbiAgfVxuXG4gIFtkYXRhLXRoZW1lPVwibGlnaHRcIl0gLnJlZnJlc2gtY291bnRkb3duIGNpcmNsZS5wcm9ncmVzcyB7XG4gICAgc3Ryb2tlOiByZ2JhKDAsIDAsIDAsIDAuOCk7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImRhcmtcIl0gLnJlZnJlc2gtY291bnRkb3duIGNpcmNsZSB7XG4gICAgc3Ryb2tlOiByZ2JhKDI1NSwgMjU1LCAyNTUsIDAuMyk7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImRhcmtcIl0gLnJlZnJlc2gtY291bnRkb3duIGNpcmNsZS5wcm9ncmVzcyB7XG4gICAgc3Ryb2tlOiByZ2JhKDI1NSwgMjU1LCAyNTUsIDAuOCk7XG4gIH1cblxuICAuc3RhdHVzLWZsb2F0aW5nLWJveC1naXRodWIge1xuICAgIGRpc3BsYXk6IGZsZXg7XG4gICAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjtcbiAgICB3aWR0aDogMWVtO1xuICAgIGhlaWdodDogMWVtO1xuICAgIG1pbi13aWR0aDogMWVtO1xuICAgIG1pbi1oZWlnaHQ6IDFlbTtcbiAgICBmbGV4LXNocmluazogMDtcbiAgICB0ZXh0LWRlY29yYXRpb246IG5vbmU7XG4gICAgdHJhbnNpdGlvbjogb3BhY2l0eSAwLjJzO1xuICB9XG5cbiAgLnN0YXR1cy1mbG9hdGluZy1ib3gtZ2l0aHViOmhvdmVyIHtcbiAgICBvcGFjaXR5OiAwLjg7XG4gIH1cblxuICAuc3Itb25seSB7XG4gICAgcG9zaXRpb246IGFic29sdXRlO1xuICAgIHdpZHRoOiAxcHg7XG4gICAgaGVpZ2h0OiAxcHg7XG4gICAgcGFkZGluZzogMDtcbiAgICBtYXJnaW46IC0xcHg7XG4gICAgb3ZlcmZsb3c6IGhpZGRlbjtcbiAgICBjbGlwOiByZWN0KDAsIDAsIDAsIDApO1xuICAgIHdoaXRlLXNwYWNlOiBub3dyYXA7XG4gICAgYm9yZGVyLXdpZHRoOiAwO1xuICB9XG5cbiAgLnJvdXRlLXNlbGVjdG9yLWNvbnRhaW5lciB7XG4gICAgcG9zaXRpb246IHJlbGF0aXZlO1xuICAgIHdpZHRoOiAxLjJlbSAhaW1wb3J0YW50O1xuICAgIGhlaWdodDogMS4yZW0gIWltcG9ydGFudDtcbiAgICBtaW4td2lkdGg6IDEuMmVtICFpbXBvcnRhbnQ7XG4gICAgbWluLWhlaWdodDogMS4yZW0gIWltcG9ydGFudDtcbiAgfVxuXG4gIC5yb3V0ZS1zZWxlY3Rvci1idXR0b24ge1xuICAgIGJhY2tncm91bmQ6IG5vbmU7XG4gICAgYm9yZGVyOiBub25lO1xuICAgIGN1cnNvcjogcG9pbnRlcjtcbiAgICBwYWRkaW5nOiAwLjFlbTtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7XG4gICAgY29sb3I6IGluaGVyaXQ7XG4gICAgdHJhbnNpdGlvbjogb3BhY2l0eSAwLjJzO1xuICAgIHdpZHRoOiAxLjJlbTtcbiAgICBoZWlnaHQ6IDEuMmVtO1xuICAgIG1pbi13aWR0aDogMS4yZW07XG4gICAgbWluLWhlaWdodDogMS4yZW07XG4gICAgb3BhY2l0eTogMC45O1xuICB9XG5cbiAgLnJvdXRlLXNlbGVjdG9yLWJ1dHRvbjpob3ZlciB7XG4gICAgb3BhY2l0eTogMC44O1xuICB9XG5cbiAgLnJvdXRlLXNlbGVjdG9yLWJ1dHRvbiBzdmcge1xuICAgIHdpZHRoOiAxMDAlO1xuICAgIGhlaWdodDogMTAwJTtcbiAgICBkaXNwbGF5OiBibG9jaztcbiAgfVxuXG4gIC5yb3V0ZS1zZWxlY3Rvci1kcm9wZG93biB7XG4gICAgcG9zaXRpb246IGFic29sdXRlO1xuICAgIGJvdHRvbTogY2FsYygxMDAlICsgMC41cmVtKTtcbiAgICByaWdodDogMDtcbiAgICBiYWNrZ3JvdW5kOiB3aGl0ZTtcbiAgICBib3JkZXItcmFkaXVzOiAwLjM3NXJlbTtcbiAgICBib3gtc2hhZG93OiAwIDEwcHggMTVweCAtM3B4IHJnYmEoMCwgMCwgMCwgMC4xKSwgMCA0cHggNnB4IC0ycHggcmdiYSgwLCAwLCAwLCAwLjA1KTtcbiAgICBtaW4td2lkdGg6IDE1MHB4O1xuICAgIHotaW5kZXg6IDEwMDA7XG4gICAgb3ZlcmZsb3c6IGhpZGRlbjtcbiAgfVxuXG4gIFtkYXRhLXRoZW1lPVwiZGFya1wiXSAucm91dGUtc2VsZWN0b3ItZHJvcGRvd24ge1xuICAgIGJhY2tncm91bmQ6ICMxZDIzMmE7XG4gICAgYm94LXNoYWRvdzogMCAxMHB4IDE1cHggLTNweCByZ2JhKDAsIDAsIDAsIDAuMyksIDAgNHB4IDZweCAtMnB4IHJnYmEoMCwgMCwgMCwgMC4yKTtcbiAgfVxuXG4gIC5yb3V0ZS1zZWxlY3Rvci1pdGVtIHtcbiAgICBkaXNwbGF5OiBibG9jaztcbiAgICB3aWR0aDogMTAwJTtcbiAgICBwYWRkaW5nOiAwLjVyZW0gMC43NXJlbTtcbiAgICB0ZXh0LWFsaWduOiBsZWZ0O1xuICAgIGJhY2tncm91bmQ6IG5vbmU7XG4gICAgYm9yZGVyOiBub25lO1xuICAgIGN1cnNvcjogcG9pbnRlcjtcbiAgICBjb2xvcjogIzExMTgyNztcbiAgICBmb250LXNpemU6IDAuODc1cmVtO1xuICAgIHRyYW5zaXRpb246IGJhY2tncm91bmQtY29sb3IgMC4ycztcbiAgfVxuXG4gIFtkYXRhLXRoZW1lPVwiZGFya1wiXSAucm91dGUtc2VsZWN0b3ItaXRlbSB7XG4gICAgY29sb3I6ICNmOWZhZmI7XG4gIH1cblxuICAucm91dGUtc2VsZWN0b3ItaXRlbTpob3ZlciB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogcmdiYSgwLCAwLCAwLCAwLjA1KTtcbiAgfVxuXG4gIFtkYXRhLXRoZW1lPVwiZGFya1wiXSAucm91dGUtc2VsZWN0b3ItaXRlbTpob3ZlciB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogcmdiYSgyNTUsIDI1NSwgMjU1LCAwLjEpO1xuICB9XG5cbiAgLnJvdXRlLXNlbGVjdG9yLWl0ZW0uYWN0aXZlIHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiByZ2JhKDgsIDEyMywgMTk2LCAwLjEpO1xuICAgIGZvbnQtd2VpZ2h0OiA2MDA7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImRhcmtcIl0gLnJvdXRlLXNlbGVjdG9yLWl0ZW0uYWN0aXZlIHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiByZ2JhKDgsIDEyMywgMTk2LCAwLjIpO1xuICB9XG48L3N0eWxlPlxuIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7QUF5TkEsRUFBRSxtQ0FBb0IsQ0FBQztBQUN2QixJQUFJLGVBQWU7QUFDbkIsSUFBSSxjQUFjO0FBQ2xCLElBQUksU0FBUztBQUNiLElBQUksMkJBQTJCO0FBQy9CLElBQUksYUFBYTtBQUNqQixJQUFJLG1CQUFtQjtBQUN2QixJQUFJLFdBQVc7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 */'
};

export default function StatusBar($$anchor, $$props) {
	$.check_target(new.target);
	$.push($$props, true, StatusBar);
	$.append_styles($$anchor, $$css);

	let routes = $.prop($$props, 'routes', 19, () => []),
		currentRoutePath = $.prop($$props, 'currentRoutePath', 3, null),
		onRouteChange = $.prop($$props, 'onRouteChange', 3, () => {}),
		refreshIntervalSeconds = $.prop($$props, 'refreshIntervalSeconds', 3, 20);

	let showRouteSelector = $.tag($.state(false), 'showRouteSelector');
	let countdownElapsed = $.tag($.state(0), 'countdownElapsed');
	let countdownInterval = null;
	let countdownCircle = null;
	const radius = 5;
	const circumference = 2 * Math.PI * radius;

	function toggleRouteSelector() {
		$.set(showRouteSelector, !$.get(showRouteSelector));
	}

	function selectRoute(path) {
		onRouteChange()(path);
		$.set(showRouteSelector, false);
	}

	function startCountdown() {
		// Clear any existing interval
		if ($.strict_equals(countdownInterval, null, false)) {
			clearInterval(countdownInterval);
			countdownInterval = null;
		}

		// Find the countdown circle
		const circleEl = document.querySelector(".refresh-countdown circle.progress");

		if (!circleEl) {
			// Retry after a short delay if element not found
			setTimeout(startCountdown, 100);

			return;
		}

		countdownCircle = circleEl;

		// Set up the circle
		circleEl.setAttribute("stroke-dasharray", circumference.toString());

		$.set(countdownElapsed, 0);
		circleEl.setAttribute("stroke-dashoffset", "0");

		const updateInterval = 100; // Update every 100ms for smooth animation

		function updateCountdown() {
			if (!countdownCircle) return;

			$.set(countdownElapsed, $.get(countdownElapsed) + updateInterval);

			const progress = $.get(countdownElapsed) / (refreshIntervalSeconds() * 1000);
			const offset = circumference * (1 - progress);

			countdownCircle.setAttribute("stroke-dashoffset", offset.toString());

			// Update screen reader text with remaining time
			const remainingSeconds = Math.ceil((refreshIntervalSeconds() * 1000 - $.get(countdownElapsed)) / 1000);

			const srText = document.getElementById("refresh-countdown-sr");

			if (srText && remainingSeconds > 0) {
				srText.textContent = `Refresh countdown: ${remainingSeconds} seconds remaining`;
			}

			// When countdown reaches the end, reset
			if ($.get(countdownElapsed) >= refreshIntervalSeconds() * 1000) {
				$.set(countdownElapsed, 0);

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
		if ($.strict_equals(countdownInterval, null, false)) {
			clearInterval(countdownInterval);
			countdownInterval = null;
		}
	});

	// Restart countdown when refresh interval changes or when API status changes (new update)
	$.user_effect(() => {
		// Access reactive values to trigger effect
		const _ = refreshIntervalSeconds();

		const __ = $$props.apiStatus;

		// Restart countdown when interval changes or on successful update
		if ($.strict_equals($$props.apiStatus, "success")) {
			startCountdown();
		}
	});

	var $$exports = { ...$.legacy_api() };
	var div = root();

	$.event('click', $.window, (e) => {
		const target = e.target;

		if ($.get(showRouteSelector) && !target.closest(".route-selector-container")) {
			$.set(showRouteSelector, false);
		}
	});

	var div_1 = $.child(div);
	var node = $.child(div_1);

	{
		var consequent = ($$anchor) => {
			var svg = root_1();

			$.append($$anchor, svg);
		};

		var alternate_2 = ($$anchor) => {
			var fragment = $.comment();
			var node_1 = $.first_child(fragment);

			{
				var consequent_1 = ($$anchor) => {
					var svg_1 = root_3();

					$.append($$anchor, svg_1);
				};

				var alternate_1 = ($$anchor) => {
					var fragment_1 = $.comment();
					var node_2 = $.first_child(fragment_1);

					{
						var consequent_2 = ($$anchor) => {
							var svg_2 = root_5();

							$.append($$anchor, svg_2);
						};

						var alternate = ($$anchor) => {
							var svg_3 = root_6();

							$.append($$anchor, svg_3);
						};

						$.add_svelte_meta(
							() => $.if(
								node_2,
								($$render) => {
									if ($.strict_equals($$props.apiStatus, "degraded")) $$render(consequent_2); else $$render(alternate, false);
								},
								true
							),
							'if',
							StatusBar,
							132,
							4
						);
					}

					$.append($$anchor, fragment_1);
				};

				$.add_svelte_meta(
					() => $.if(
						node_1,
						($$render) => {
							if ($.strict_equals($$props.apiStatus, "error")) $$render(consequent_1); else $$render(alternate_1, false);
						},
						true
					),
					'if',
					StatusBar,
					128,
					4
				);
			}

			$.append($$anchor, fragment);
		};

		$.add_svelte_meta(
			() => $.if(node, ($$render) => {
				if ($.strict_equals($$props.apiStatus, "success")) $$render(consequent); else $$render(alternate_2, false);
			}),
			'if',
			StatusBar,
			124,
			4
		);
	}

	$.reset(div_1);

	var button = $.sibling(div_1, 4);

	button.__click = function (...$$args) {
		$.apply(() => $$props.onConfigClick, this, $$args, StatusBar, [153, 13]);
	};

	var node_3 = $.sibling(button, 4);

	{
		var consequent_4 = ($$anchor) => {
			var div_2 = root_7();
			var button_1 = $.child(div_2);

			button_1.__click = (e) => {
				e.stopPropagation();
				toggleRouteSelector();
			};

			var node_4 = $.sibling(button_1, 2);

			{
				var consequent_3 = ($$anchor) => {
					var div_3 = root_8();

					div_3.__click = (e) => e.stopPropagation();

					$.add_svelte_meta(
						() => $.each(div_3, 21, routes, $.index, ($$anchor, route) => {
							var button_2 = root_9();

							button_2.__click = () => selectRoute($.get(route).path);

							var text = $.child(button_2, true);

							$.reset(button_2);

							$.template_effect(() => {
								$.set_class(button_2, 1, `route-selector-item ${$.strict_equals(currentRoutePath(), $.get(route).path) ? 'active' : ''}`, 'svelte-161y12f');
								$.set_text(text, $.get(route).display?.title || $.get(route).path || "Default");
							});

							$.append($$anchor, button_2);
						}),
						'each',
						StatusBar,
						201,
						10
					);

					$.reset(div_3);
					$.append($$anchor, div_3);
				};

				$.add_svelte_meta(
					() => $.if(node_4, ($$render) => {
						if ($.get(showRouteSelector)) $$render(consequent_3);
					}),
					'if',
					StatusBar,
					199,
					6
				);
			}

			$.reset(div_2);
			$.template_effect(() => $.set_attribute(button_1, 'aria-expanded', $.get(showRouteSelector)));
			$.append($$anchor, div_2);
		};

		$.add_svelte_meta(
			() => $.if(node_3, ($$render) => {
				if (routes().length > 1) $$render(consequent_4);
			}),
			'if',
			StatusBar,
			180,
			2
		);
	}

	$.reset(div);
	$.template_effect(() => $.set_attribute(div_1, 'aria-label', `API status: ${$$props.apiStatus ?? ''}`));
	$.append($$anchor, div);

	return $.pop($$exports);
}

$.delegate(['click']);