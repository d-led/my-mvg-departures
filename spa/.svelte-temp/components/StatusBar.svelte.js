import 'svelte/internal/disclose-version';

StatusBar[$.FILENAME] = 'src/components/StatusBar.svelte';

import * as $ from 'svelte/internal/client';

var root_1 = $.add_locations($.from_svg(`<svg class="api-status-icon api-success svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`), StatusBar[$.FILENAME], [[43, 6, [[44, 8]]]]);
var root_3 = $.add_locations($.from_svg(`<svg class="api-status-icon api-error svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>`), StatusBar[$.FILENAME], [[47, 6, [[48, 8]]]]);
var root_5 = $.add_locations($.from_svg(`<svg class="api-status-icon api-degraded svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"></path></svg>`), StatusBar[$.FILENAME], [[51, 6, [[52, 8]]]]);
var root_6 = $.add_locations($.from_svg(`<svg class="api-status-icon api-unknown svelte-161y12f" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z"></path></svg>`), StatusBar[$.FILENAME], [[55, 6, [[56, 8]]]]);
var root_9 = $.add_locations($.from_html(`<button role="menuitem" type="button"> </button>`), StatusBar[$.FILENAME], [[119, 12]]);
var root_8 = $.add_locations($.from_html(`<div class="route-selector-dropdown svelte-161y12f" role="menu" aria-label="Available routes"></div>`), StatusBar[$.FILENAME], [[117, 8]]);
var root_7 = $.add_locations($.from_html(`<div class="status-floating-box-item route-selector-container svelte-161y12f"><button class="route-selector-button svelte-161y12f" aria-label="Select view/route" title="Select view/route" type="button" aria-haspopup="true"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true" class="svelte-161y12f"><path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"></path></svg></button> <!></div>`), StatusBar[$.FILENAME], [[98, 4, [[99, 6, [[111, 8, [[112, 10]]]]]]]]);

var root = $.add_locations($.from_html(`<div class="status-floating-box svelte-161y12f" role="status" aria-label="System status indicators"><div class="status-floating-box-item svelte-161y12f" id="api-status-container" role="img" title="MVG API connection status"><!></div> <div class="status-floating-box-item refresh-countdown svelte-161y12f" role="img" aria-label="Refresh countdown timer" title="Time until next data refresh"><svg viewBox="0 0 12 12" width="100%" height="100%" aria-hidden="true" class="svelte-161y12f"><circle cx="6" cy="6" r="5" class="background svelte-161y12f"></circle><circle cx="6" cy="6" r="5" class="progress svelte-161y12f" transform="rotate(-90 6 6)"></circle></svg> <span class="sr-only svelte-161y12f" id="refresh-countdown-sr">Refresh countdown timer</span></div> <button class="status-floating-box-item config-button svelte-161y12f" aria-label="Open configuration" title="Open configuration" type="button"><svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 011.37.49l1.296 2.247a1.125 1.125 0 01-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 010 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 01-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 01-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 01-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 01-1.369-.49l-1.297-2.247a1.125 1.125 0 01.26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 010-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 01-.26-1.43l1.297-2.247a1.125 1.125 0 011.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281z"></path><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path></svg></button> <a href="https://github.com/d-led/my-mvg-departures" target="_blank" rel="noopener noreferrer" class="status-floating-box-github status-floating-box-item svelte-161y12f" aria-label="View repository on GitHub (opens in new tab)" title="View repository on GitHub"><svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.46-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"></path></svg> <span class="sr-only svelte-161y12f">View repository on GitHub</span></a> <!></div>`), StatusBar[$.FILENAME], [
	[
		40,
		0,
		[
			[41, 2],
			[61, 2, [[62, 4, [[63, 6], [64, 6]]], [66, 4]]],
			[69, 2, [[76, 4, [[77, 6], [78, 6]]]]],
			[82, 2, [[90, 4, [[91, 6]]], [93, 4]]]
		]
	]
]);

const $$css = {
	hash: 'svelte-161y12f',
	code: '\n  .status-floating-box.svelte-161y12f {\n    position: fixed;\n    bottom: 0.5rem;\n    left: 50%;\n    transform: translateX(-50%);\n    display: flex;\n    align-items: center;\n    gap: 0.4rem;\n    padding: 0.4rem 0.6rem;\n    background-color: rgba(128, 128, 128, 0.3);\n    backdrop-filter: blur(4px);\n    border-radius: 0.4rem;\n    z-index: 1000;\n  }\n\n  /* (unused) [data-theme="light"] .status-floating-box {\n    background-color: rgba(128, 128, 128, 0.2);\n  }*/\n\n  /* (unused) [data-theme="dark"] .status-floating-box {\n    background-color: rgba(128, 128, 128, 0.4);\n  }*/\n\n  .status-floating-box-item.svelte-161y12f {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 1em;\n    height: 1em;\n    min-width: 1em;\n    min-height: 1em;\n    flex-shrink: 0;\n  }\n\n  .config-button.svelte-161y12f {\n    background: none;\n    border: none;\n    cursor: pointer;\n    padding: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    color: inherit;\n    transition: opacity 0.2s;\n  }\n\n  .config-button.svelte-161y12f:hover {\n    opacity: 0.8;\n  }\n\n  .api-status-icon.svelte-161y12f {\n    width: 100%;\n    height: 100%;\n    display: block;\n  }\n\n  .api-status-icon.api-success.svelte-161y12f {\n    color: #059669;\n  }\n\n  .api-status-icon.api-error.svelte-161y12f {\n    color: #dc2626;\n  }\n\n  .api-status-icon.api-unknown.svelte-161y12f {\n    color: rgba(255, 255, 255, 0.5);\n  }\n\n  .api-status-icon.api-degraded.svelte-161y12f {\n    color: #d97706;\n  }\n\n  .refresh-countdown.svelte-161y12f svg:where(.svelte-161y12f) {\n    width: 100%;\n    height: 100%;\n    display: block;\n  }\n\n  .refresh-countdown.svelte-161y12f circle:where(.svelte-161y12f) {\n    fill: none;\n    stroke-width: 2;\n    transition: stroke-dashoffset 0.1s linear;\n  }\n\n  /* (unused) [data-theme="light"] .refresh-countdown circle {\n    stroke: rgba(0, 0, 0, 0.3);\n  }*/\n\n  /* (unused) [data-theme="light"] .refresh-countdown circle.progress {\n    stroke: rgba(0, 0, 0, 0.8);\n  }*/\n\n  /* (unused) [data-theme="dark"] .refresh-countdown circle {\n    stroke: rgba(255, 255, 255, 0.3);\n  }*/\n\n  /* (unused) [data-theme="dark"] .refresh-countdown circle.progress {\n    stroke: rgba(255, 255, 255, 0.8);\n  }*/\n\n  .status-floating-box-github.svelte-161y12f {\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    width: 1em;\n    height: 1em;\n    min-width: 1em;\n    min-height: 1em;\n    flex-shrink: 0;\n    text-decoration: none;\n    transition: opacity 0.2s;\n  }\n\n  .status-floating-box-github.svelte-161y12f:hover {\n    opacity: 0.8;\n  }\n\n  .sr-only.svelte-161y12f {\n    position: absolute;\n    width: 1px;\n    height: 1px;\n    padding: 0;\n    margin: -1px;\n    overflow: hidden;\n    clip: rect(0, 0, 0, 0);\n    white-space: nowrap;\n    border-width: 0;\n  }\n\n  .route-selector-container.svelte-161y12f {\n    position: relative;\n  }\n\n  .route-selector-button.svelte-161y12f {\n    background: none;\n    border: none;\n    cursor: pointer;\n    padding: 0;\n    display: flex;\n    align-items: center;\n    justify-content: center;\n    color: inherit;\n    transition: opacity 0.2s;\n    width: 1em;\n    height: 1em;\n    min-width: 1em;\n    min-height: 1em;\n  }\n\n  .route-selector-button.svelte-161y12f:hover {\n    opacity: 0.8;\n  }\n\n  .route-selector-button.svelte-161y12f svg:where(.svelte-161y12f) {\n    width: 100%;\n    height: 100%;\n    display: block;\n  }\n\n  .route-selector-dropdown.svelte-161y12f {\n    position: absolute;\n    bottom: calc(100% + 0.5rem);\n    right: 0;\n    background: white;\n    border-radius: 0.375rem;\n    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);\n    min-width: 150px;\n    z-index: 1000;\n    overflow: hidden;\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-dropdown {\n    background: #1d232a;\n    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.2);\n  }*/\n\n  .route-selector-item.svelte-161y12f {\n    display: block;\n    width: 100%;\n    padding: 0.5rem 0.75rem;\n    text-align: left;\n    background: none;\n    border: none;\n    cursor: pointer;\n    color: #111827;\n    font-size: 0.875rem;\n    transition: background-color 0.2s;\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-item {\n    color: #f9fafb;\n  }*/\n\n  .route-selector-item.svelte-161y12f:hover {\n    background-color: rgba(0, 0, 0, 0.05);\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-item:hover {\n    background-color: rgba(255, 255, 255, 0.1);\n  }*/\n\n  .route-selector-item.active.svelte-161y12f {\n    background-color: rgba(8, 123, 196, 0.1);\n    font-weight: 600;\n  }\n\n  /* (unused) [data-theme="dark"] .route-selector-item.active {\n    background-color: rgba(8, 123, 196, 0.2);\n  }*/\n\n/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiU3RhdHVzQmFyLnN2ZWx0ZSIsInNvdXJjZXMiOlsiU3RhdHVzQmFyLnN2ZWx0ZSJdLCJzb3VyY2VzQ29udGVudCI6WyI8c2NyaXB0IGxhbmc9XCJ0c1wiPlxuICBpbXBvcnQgdHlwZSB7IFJvdXRlQ29uZmlndXJhdGlvbiB9IGZyb20gXCIuLi9kb21haW4vbW9kZWxzL2luZGV4LmpzXCI7XG5cbiAgbGV0IHtcbiAgICBhcGlTdGF0dXMsXG4gICAgc2hvd0NvbmZpZ01vZGFsLFxuICAgIG9uQ29uZmlnQ2xpY2ssXG4gICAgcm91dGVzID0gW10sXG4gICAgY3VycmVudFJvdXRlUGF0aCA9IG51bGwsXG4gICAgb25Sb3V0ZUNoYW5nZSA9ICgpID0+IHt9LFxuICB9OiB7XG4gICAgYXBpU3RhdHVzOiBcInN1Y2Nlc3NcIiB8IFwiZXJyb3JcIiB8IFwiZGVncmFkZWRcIiB8IFwidW5rbm93blwiO1xuICAgIHNob3dDb25maWdNb2RhbDogYm9vbGVhbjtcbiAgICBvbkNvbmZpZ0NsaWNrOiAoKSA9PiB2b2lkO1xuICAgIHJvdXRlcz86IFJvdXRlQ29uZmlndXJhdGlvbltdO1xuICAgIGN1cnJlbnRSb3V0ZVBhdGg/OiBzdHJpbmcgfCBudWxsO1xuICAgIG9uUm91dGVDaGFuZ2U/OiAocGF0aDogc3RyaW5nKSA9PiB2b2lkO1xuICB9ID0gJHByb3BzKCk7XG4gIFxuICBsZXQgc2hvd1JvdXRlU2VsZWN0b3IgPSAkc3RhdGUoZmFsc2UpO1xuXG4gIGZ1bmN0aW9uIHRvZ2dsZVJvdXRlU2VsZWN0b3IoKSB7XG4gICAgc2hvd1JvdXRlU2VsZWN0b3IgPSAhc2hvd1JvdXRlU2VsZWN0b3I7XG4gIH1cblxuICBmdW5jdGlvbiBzZWxlY3RSb3V0ZShwYXRoOiBzdHJpbmcpIHtcbiAgICBvblJvdXRlQ2hhbmdlKHBhdGgpO1xuICAgIHNob3dSb3V0ZVNlbGVjdG9yID0gZmFsc2U7XG4gIH1cblxuPC9zY3JpcHQ+XG5cbjxzdmVsdGU6d2luZG93IG9uY2xpY2s9eyhlKSA9PiB7XG4gIGNvbnN0IHRhcmdldCA9IGUudGFyZ2V0IGFzIEhUTUxFbGVtZW50O1xuICBpZiAoc2hvd1JvdXRlU2VsZWN0b3IgJiYgIXRhcmdldC5jbG9zZXN0KFwiLnJvdXRlLXNlbGVjdG9yLWNvbnRhaW5lclwiKSkge1xuICAgIHNob3dSb3V0ZVNlbGVjdG9yID0gZmFsc2U7XG4gIH1cbn19IC8+XG5cbjxkaXYgY2xhc3M9XCJzdGF0dXMtZmxvYXRpbmctYm94XCIgcm9sZT1cInN0YXR1c1wiIGFyaWEtbGFiZWw9XCJTeXN0ZW0gc3RhdHVzIGluZGljYXRvcnNcIj5cbiAgPGRpdiBjbGFzcz1cInN0YXR1cy1mbG9hdGluZy1ib3gtaXRlbVwiIGlkPVwiYXBpLXN0YXR1cy1jb250YWluZXJcIiByb2xlPVwiaW1nXCIgYXJpYS1sYWJlbD1cIkFQSSBzdGF0dXM6IHthcGlTdGF0dXN9XCIgdGl0bGU9XCJNVkcgQVBJIGNvbm5lY3Rpb24gc3RhdHVzXCI+XG4gICAgeyNpZiBhcGlTdGF0dXMgPT09IFwic3VjY2Vzc1wifVxuICAgICAgPHN2ZyBjbGFzcz1cImFwaS1zdGF0dXMtaWNvbiBhcGktc3VjY2Vzc1wiIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiBmaWxsPVwibm9uZVwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBzdHJva2Utd2lkdGg9XCIyXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICAgIDxwYXRoIHN0cm9rZS1saW5lY2FwPVwicm91bmRcIiBzdHJva2UtbGluZWpvaW49XCJyb3VuZFwiIGQ9XCJNOSAxMi43NUwxMS4yNSAxNSAxNSA5Ljc1TTIxIDEyYTkgOSAwIDExLTE4IDAgOSA5IDAgMDExOCAwelwiIC8+XG4gICAgICA8L3N2Zz5cbiAgICB7OmVsc2UgaWYgYXBpU3RhdHVzID09PSBcImVycm9yXCJ9XG4gICAgICA8c3ZnIGNsYXNzPVwiYXBpLXN0YXR1cy1pY29uIGFwaS1lcnJvclwiIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiBmaWxsPVwibm9uZVwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBzdHJva2Utd2lkdGg9XCIyXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICAgIDxwYXRoIHN0cm9rZS1saW5lY2FwPVwicm91bmRcIiBzdHJva2UtbGluZWpvaW49XCJyb3VuZFwiIGQ9XCJNOS43NSA5Ljc1bDQuNSA0LjVtMC00LjVsLTQuNSA0LjVNMjEgMTJhOSA5IDAgMTEtMTggMCA5IDkgMCAwMTE4IDB6XCIgLz5cbiAgICAgIDwvc3ZnPlxuICAgIHs6ZWxzZSBpZiBhcGlTdGF0dXMgPT09IFwiZGVncmFkZWRcIn1cbiAgICAgIDxzdmcgY2xhc3M9XCJhcGktc3RhdHVzLWljb24gYXBpLWRlZ3JhZGVkXCIgeG1sbnM9XCJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2Z1wiIGZpbGw9XCJub25lXCIgdmlld0JveD1cIjAgMCAyNCAyNFwiIHN0cm9rZS13aWR0aD1cIjJcIiBzdHJva2U9XCJjdXJyZW50Q29sb3JcIiBhcmlhLWhpZGRlbj1cInRydWVcIj5cbiAgICAgICAgPHBhdGggc3Ryb2tlLWxpbmVjYXA9XCJyb3VuZFwiIHN0cm9rZS1saW5lam9pbj1cInJvdW5kXCIgZD1cIk0xMiA5djMuNzVtLTkuMzAzIDMuMzc2Yy0uODY2IDEuNS4yMTcgMy4zNzQgMS45NDggMy4zNzRoMTQuNzFjMS43MyAwIDIuODEzLTEuODc0IDEuOTQ4LTMuMzc0TDEzLjk0OSAzLjM3OGMtLjg2Ni0xLjUtMy4wMzItMS41LTMuODk4IDBMMi42OTcgMTYuMTI2ek0xMiAxNS43NWguMDA3di4wMDhIMTJ2LS4wMDh6XCIgLz5cbiAgICAgIDwvc3ZnPlxuICAgIHs6ZWxzZX1cbiAgICAgIDxzdmcgY2xhc3M9XCJhcGktc3RhdHVzLWljb24gYXBpLXVua25vd25cIiB4bWxucz1cImh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnXCIgZmlsbD1cIm5vbmVcIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgc3Ryb2tlLXdpZHRoPVwiMlwiIHN0cm9rZT1cImN1cnJlbnRDb2xvclwiIGFyaWEtaGlkZGVuPVwidHJ1ZVwiPlxuICAgICAgICA8cGF0aCBzdHJva2UtbGluZWNhcD1cInJvdW5kXCIgc3Ryb2tlLWxpbmVqb2luPVwicm91bmRcIiBkPVwiTTkuODc5IDcuNTE5YzEuMTcxLTEuMDI1IDMuMDcxLTEuMDI1IDQuMjQyIDAgMS4xNzIgMS4wMjUgMS4xNzIgMi42ODcgMCAzLjcxMi0uMjAzLjE3OS0uNDMuMzI2LS42Ny40NDItLjc0NS4zNjEtMS40NS45OTktMS40NSAxLjgyN3YuNzVNMjEgMTJhOSA5IDAgMTEtMTggMCA5IDkgMCAwMTE4IDB6bS05IDUuMjVoLjAwOHYuMDA4SDEydi0uMDA4elwiIC8+XG4gICAgICA8L3N2Zz5cbiAgICB7L2lmfVxuICA8L2Rpdj5cblxuICA8ZGl2IGNsYXNzPVwic3RhdHVzLWZsb2F0aW5nLWJveC1pdGVtIHJlZnJlc2gtY291bnRkb3duXCIgcm9sZT1cImltZ1wiIGFyaWEtbGFiZWw9XCJSZWZyZXNoIGNvdW50ZG93biB0aW1lclwiIHRpdGxlPVwiVGltZSB1bnRpbCBuZXh0IGRhdGEgcmVmcmVzaFwiPlxuICAgIDxzdmcgdmlld0JveD1cIjAgMCAxMiAxMlwiIHdpZHRoPVwiMTAwJVwiIGhlaWdodD1cIjEwMCVcIiBhcmlhLWhpZGRlbj1cInRydWVcIj5cbiAgICAgIDxjaXJjbGUgY3g9XCI2XCIgY3k9XCI2XCIgcj1cIjVcIiBjbGFzcz1cImJhY2tncm91bmRcIj48L2NpcmNsZT5cbiAgICAgIDxjaXJjbGUgY3g9XCI2XCIgY3k9XCI2XCIgcj1cIjVcIiBjbGFzcz1cInByb2dyZXNzXCIgdHJhbnNmb3JtPVwicm90YXRlKC05MCA2IDYpXCI+PC9jaXJjbGU+XG4gICAgPC9zdmc+XG4gICAgPHNwYW4gY2xhc3M9XCJzci1vbmx5XCIgaWQ9XCJyZWZyZXNoLWNvdW50ZG93bi1zclwiPlJlZnJlc2ggY291bnRkb3duIHRpbWVyPC9zcGFuPlxuICA8L2Rpdj5cblxuICA8YnV0dG9uXG4gICAgY2xhc3M9XCJzdGF0dXMtZmxvYXRpbmctYm94LWl0ZW0gY29uZmlnLWJ1dHRvblwiXG4gICAgb25jbGljaz17b25Db25maWdDbGlja31cbiAgICBhcmlhLWxhYmVsPVwiT3BlbiBjb25maWd1cmF0aW9uXCJcbiAgICB0aXRsZT1cIk9wZW4gY29uZmlndXJhdGlvblwiXG4gICAgdHlwZT1cImJ1dHRvblwiXG4gID5cbiAgICA8c3ZnIHhtbG5zPVwiaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmdcIiBmaWxsPVwibm9uZVwiIHZpZXdCb3g9XCIwIDAgMjQgMjRcIiBzdHJva2Utd2lkdGg9XCIyXCIgc3Ryb2tlPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICA8cGF0aCBzdHJva2UtbGluZWNhcD1cInJvdW5kXCIgc3Ryb2tlLWxpbmVqb2luPVwicm91bmRcIiBkPVwiTTkuNTk0IDMuOTRjLjA5LS41NDIuNTYtLjk0IDEuMTEtLjk0aDIuNTkzYy41NSAwIDEuMDIuMzk4IDEuMTEuOTRsLjIxMyAxLjI4MWMuMDYzLjM3NC4zMTMuNjg2LjY0NS44Ny4wNzQuMDQuMTQ3LjA4My4yMi4xMjcuMzI0LjE5Ni43Mi4yNTcgMS4wNzUuMTI0bDEuMjE3LS40NTZhMS4xMjUgMS4xMjUgMCAwMTEuMzcuNDlsMS4yOTYgMi4yNDdhMS4xMjUgMS4xMjUgMCAwMS0uMjYgMS40MzFsLTEuMDAzLjgyN2MtLjI5My4yNC0uNDM4LjYxMy0uNDMxLjk5MmE2Ljc1OSA2Ljc1OSAwIDAxMCAuMjU1Yy0uMDA3LjM3OC4xMzguNzUuNDMuOTlsMS4wMDUuODI4Yy40MjQuMzUuNTM0Ljk1NC4yNiAxLjQzbC0xLjI5OCAyLjI0N2ExLjEyNSAxLjEyNSAwIDAxLTEuMzY5LjQ5MWwtMS4yMTctLjQ1NmMtLjM1NS0uMTMzLS43NS0uMDcyLTEuMDc2LjEyNGE2LjU3IDYuNTcgMCAwMS0uMjIuMTI4Yy0uMzMxLjE4My0uNTgxLjQ5NS0uNjQ0Ljg2OWwtLjIxMyAxLjI4Yy0uMDkuNTQzLS41Ni45NDEtMS4xMS45NDFoLTIuNTk0Yy0uNTUgMC0xLjAyLS4zOTgtMS4xMS0uOTRsLS4yMTMtMS4yODFjLS4wNjItLjM3NC0uMzEyLS42ODYtLjY0NC0uODdhNi41MiA2LjUyIDAgMDEtLjIyLS4xMjdjLS4zMjUtLjE5Ni0uNzItLjI1Ny0xLjA3Ni0uMTI0bC0xLjIxNy40NTZhMS4xMjUgMS4xMjUgMCAwMS0xLjM2OS0uNDlsLTEuMjk3LTIuMjQ3YTEuMTI1IDEuMTI1IDAgMDEuMjYtMS40MzFsMS4wMDQtLjgyN2MuMjkyLS4yNC40MzctLjYxMy40My0uOTkyYTYuOTMyIDYuOTMyIDAgMDEwLS4yNTVjLjAwNy0uMzc4LS4xMzgtLjc1LS40My0uOTlsLTEuMDA0LS44MjhhMS4xMjUgMS4xMjUgMCAwMS0uMjYtMS40M2wxLjI5Ny0yLjI0N2ExLjEyNSAxLjEyNSAwIDAxMS4zNy0uNDkxbDEuMjE2LjQ1NmMuMzU2LjEzMy43NTEuMDcyIDEuMDc2LS4xMjQuMDcyLS4wNDQuMTQ2LS4wODcuMjItLjEyOC4zMzItLjE4My41ODItLjQ5NS42NDQtLjg2OWwuMjE0LTEuMjgxelwiIC8+XG4gICAgICA8cGF0aCBzdHJva2UtbGluZWNhcD1cInJvdW5kXCIgc3Ryb2tlLWxpbmVqb2luPVwicm91bmRcIiBkPVwiTTE1IDEyYTMgMyAwIDExLTYgMCAzIDMgMCAwMTYgMHpcIiAvPlxuICAgIDwvc3ZnPlxuICA8L2J1dHRvbj5cblxuICA8YVxuICAgIGhyZWY9XCJodHRwczovL2dpdGh1Yi5jb20vZC1sZWQvbXktbXZnLWRlcGFydHVyZXNcIlxuICAgIHRhcmdldD1cIl9ibGFua1wiXG4gICAgcmVsPVwibm9vcGVuZXIgbm9yZWZlcnJlclwiXG4gICAgY2xhc3M9XCJzdGF0dXMtZmxvYXRpbmctYm94LWdpdGh1YiBzdGF0dXMtZmxvYXRpbmctYm94LWl0ZW1cIlxuICAgIGFyaWEtbGFiZWw9XCJWaWV3IHJlcG9zaXRvcnkgb24gR2l0SHViIChvcGVucyBpbiBuZXcgdGFiKVwiXG4gICAgdGl0bGU9XCJWaWV3IHJlcG9zaXRvcnkgb24gR2l0SHViXCJcbiAgPlxuICAgIDxzdmcgeG1sbnM9XCJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2Z1wiIHdpZHRoPVwiMTZcIiBoZWlnaHQ9XCIxNlwiIHZpZXdCb3g9XCIwIDAgMTYgMTZcIiBmaWxsPVwiY3VycmVudENvbG9yXCIgYXJpYS1oaWRkZW49XCJ0cnVlXCI+XG4gICAgICA8cGF0aCBkPVwiTTggMGM0LjQyIDAgOCAzLjU4IDggOGE4LjAxMyA4LjAxMyAwIDAgMS01LjQ1IDcuNTljLS40LjA4LS41NS0uMTctLjU1LS4zOCAwLS4yNy4wMS0xLjEzLjAxLTIuMiAwLS43NS0uMjUtMS4yMy0uNTQtMS40OCAxLjc4LS4yIDMuNjUtLjg4IDMuNjUtMy45NSAwLS44OC0uMzEtMS41OS0uODItMi4xNS4wOC0uMi4zNi0xLjAyLS4wOC0yLjEyIDAgMC0uNjctLjIyLTIuMi44Mi0uNjQtLjE4LTEuMzItLjI3LTItLjI3LS42OCAwLTEuMzYuMDktMiAuMjctMS41My0xLjAzLTIuMi0uODItMi4yLS44Mi0uNDQgMS4xLS4xNiAxLjkyLS4wOCAyLjEyLS41MS41Ni0uODIgMS4yOC0uODIgMi4xNSAwIDMuMDYgMS44NiAzLjc1IDMuNjQgMy45NS0uMjMuMi0uNDQuNTUtLjUxIDEuMDctLjQ2LjIxLTEuNjEuNTUtMi4zMy0uNjYtLjE1LS4yNC0uNi0uODMtMS4yMy0uODItLjY3LjAxLS4yNy4zOC4wMS41My4zNC4xOS43My45LjgyIDEuMTMuMTYuNDUuNjggMS4zMSAyLjY5Ljk0IDAgLjY3LjAxIDEuMy4wMSAxLjQ5IDAgLjIxLS4xNS40Ni0uNTUuMzhBNy45OTUgNy45OTUgMCAwIDEgMCA4YzAtNC40MiAzLjU4LTggOC04WlwiLz5cbiAgICA8L3N2Zz5cbiAgICA8c3BhbiBjbGFzcz1cInNyLW9ubHlcIj5WaWV3IHJlcG9zaXRvcnkgb24gR2l0SHViPC9zcGFuPlxuICA8L2E+XG4gIFxuICA8IS0tIFJvdXRlIHNlbGVjdG9yIChyZXBsYWNlcyBwcmVzZW5jZSBjb3VudGVyKSAtLT5cbiAgeyNpZiByb3V0ZXMubGVuZ3RoID4gMX1cbiAgICA8ZGl2IGNsYXNzPVwic3RhdHVzLWZsb2F0aW5nLWJveC1pdGVtIHJvdXRlLXNlbGVjdG9yLWNvbnRhaW5lclwiPlxuICAgICAgPGJ1dHRvblxuICAgICAgICBjbGFzcz1cInJvdXRlLXNlbGVjdG9yLWJ1dHRvblwiXG4gICAgICAgIG9uY2xpY2s9eyhlKSA9PiB7XG4gICAgICAgICAgZS5zdG9wUHJvcGFnYXRpb24oKTtcbiAgICAgICAgICB0b2dnbGVSb3V0ZVNlbGVjdG9yKCk7XG4gICAgICAgIH19XG4gICAgICAgIGFyaWEtbGFiZWw9XCJTZWxlY3Qgdmlldy9yb3V0ZVwiXG4gICAgICAgIHRpdGxlPVwiU2VsZWN0IHZpZXcvcm91dGVcIlxuICAgICAgICB0eXBlPVwiYnV0dG9uXCJcbiAgICAgICAgYXJpYS1leHBhbmRlZD17c2hvd1JvdXRlU2VsZWN0b3J9XG4gICAgICAgIGFyaWEtaGFzcG9wdXA9XCJ0cnVlXCJcbiAgICAgID5cbiAgICAgICAgPHN2ZyB4bWxucz1cImh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnXCIgZmlsbD1cIm5vbmVcIiB2aWV3Qm94PVwiMCAwIDI0IDI0XCIgc3Ryb2tlLXdpZHRoPVwiMlwiIHN0cm9rZT1cImN1cnJlbnRDb2xvclwiIGFyaWEtaGlkZGVuPVwidHJ1ZVwiPlxuICAgICAgICAgIDxwYXRoIHN0cm9rZS1saW5lY2FwPVwicm91bmRcIiBzdHJva2UtbGluZWpvaW49XCJyb3VuZFwiIGQ9XCJNMy43NSA2Ljc1aDE2LjVNMy43NSAxMmgxNi41bS0xNi41IDUuMjVoMTYuNVwiIC8+XG4gICAgICAgIDwvc3ZnPlxuICAgICAgPC9idXR0b24+XG4gICAgICBcbiAgICAgIHsjaWYgc2hvd1JvdXRlU2VsZWN0b3J9XG4gICAgICAgIDxkaXYgY2xhc3M9XCJyb3V0ZS1zZWxlY3Rvci1kcm9wZG93blwiIHJvbGU9XCJtZW51XCIgYXJpYS1sYWJlbD1cIkF2YWlsYWJsZSByb3V0ZXNcIiBvbmNsaWNrPXsoZSkgPT4gZS5zdG9wUHJvcGFnYXRpb24oKX0+XG4gICAgICAgICAgeyNlYWNoIHJvdXRlcyBhcyByb3V0ZX1cbiAgICAgICAgICAgIDxidXR0b25cbiAgICAgICAgICAgICAgY2xhc3M9XCJyb3V0ZS1zZWxlY3Rvci1pdGVtIHtjdXJyZW50Um91dGVQYXRoID09PSByb3V0ZS5wYXRoID8gJ2FjdGl2ZScgOiAnJ31cIlxuICAgICAgICAgICAgICBvbmNsaWNrPXsoKSA9PiBzZWxlY3RSb3V0ZShyb3V0ZS5wYXRoKX1cbiAgICAgICAgICAgICAgcm9sZT1cIm1lbnVpdGVtXCJcbiAgICAgICAgICAgICAgdHlwZT1cImJ1dHRvblwiXG4gICAgICAgICAgICA+XG4gICAgICAgICAgICAgIHtyb3V0ZS5kaXNwbGF5Py50aXRsZSB8fCByb3V0ZS5wYXRoIHx8IFwiRGVmYXVsdFwifVxuICAgICAgICAgICAgPC9idXR0b24+XG4gICAgICAgICAgey9lYWNofVxuICAgICAgICA8L2Rpdj5cbiAgICAgIHsvaWZ9XG4gICAgPC9kaXY+XG4gIHsvaWZ9XG48L2Rpdj5cblxuPHN0eWxlPlxuICAuc3RhdHVzLWZsb2F0aW5nLWJveCB7XG4gICAgcG9zaXRpb246IGZpeGVkO1xuICAgIGJvdHRvbTogMC41cmVtO1xuICAgIGxlZnQ6IDUwJTtcbiAgICB0cmFuc2Zvcm06IHRyYW5zbGF0ZVgoLTUwJSk7XG4gICAgZGlzcGxheTogZmxleDtcbiAgICBhbGlnbi1pdGVtczogY2VudGVyO1xuICAgIGdhcDogMC40cmVtO1xuICAgIHBhZGRpbmc6IDAuNHJlbSAwLjZyZW07XG4gICAgYmFja2dyb3VuZC1jb2xvcjogcmdiYSgxMjgsIDEyOCwgMTI4LCAwLjMpO1xuICAgIGJhY2tkcm9wLWZpbHRlcjogYmx1cig0cHgpO1xuICAgIGJvcmRlci1yYWRpdXM6IDAuNHJlbTtcbiAgICB6LWluZGV4OiAxMDAwO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJsaWdodFwiXSAuc3RhdHVzLWZsb2F0aW5nLWJveCB7XG4gICAgYmFja2dyb3VuZC1jb2xvcjogcmdiYSgxMjgsIDEyOCwgMTI4LCAwLjIpO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5zdGF0dXMtZmxvYXRpbmctYm94IHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiByZ2JhKDEyOCwgMTI4LCAxMjgsIDAuNCk7XG4gIH1cblxuICAuc3RhdHVzLWZsb2F0aW5nLWJveC1pdGVtIHtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7XG4gICAgd2lkdGg6IDFlbTtcbiAgICBoZWlnaHQ6IDFlbTtcbiAgICBtaW4td2lkdGg6IDFlbTtcbiAgICBtaW4taGVpZ2h0OiAxZW07XG4gICAgZmxleC1zaHJpbms6IDA7XG4gIH1cblxuICAuY29uZmlnLWJ1dHRvbiB7XG4gICAgYmFja2dyb3VuZDogbm9uZTtcbiAgICBib3JkZXI6IG5vbmU7XG4gICAgY3Vyc29yOiBwb2ludGVyO1xuICAgIHBhZGRpbmc6IDA7XG4gICAgZGlzcGxheTogZmxleDtcbiAgICBhbGlnbi1pdGVtczogY2VudGVyO1xuICAgIGp1c3RpZnktY29udGVudDogY2VudGVyO1xuICAgIGNvbG9yOiBpbmhlcml0O1xuICAgIHRyYW5zaXRpb246IG9wYWNpdHkgMC4ycztcbiAgfVxuXG4gIC5jb25maWctYnV0dG9uOmhvdmVyIHtcbiAgICBvcGFjaXR5OiAwLjg7XG4gIH1cblxuICAuYXBpLXN0YXR1cy1pY29uIHtcbiAgICB3aWR0aDogMTAwJTtcbiAgICBoZWlnaHQ6IDEwMCU7XG4gICAgZGlzcGxheTogYmxvY2s7XG4gIH1cblxuICAuYXBpLXN0YXR1cy1pY29uLmFwaS1zdWNjZXNzIHtcbiAgICBjb2xvcjogIzA1OTY2OTtcbiAgfVxuXG4gIC5hcGktc3RhdHVzLWljb24uYXBpLWVycm9yIHtcbiAgICBjb2xvcjogI2RjMjYyNjtcbiAgfVxuXG4gIC5hcGktc3RhdHVzLWljb24uYXBpLXVua25vd24ge1xuICAgIGNvbG9yOiByZ2JhKDI1NSwgMjU1LCAyNTUsIDAuNSk7XG4gIH1cblxuICAuYXBpLXN0YXR1cy1pY29uLmFwaS1kZWdyYWRlZCB7XG4gICAgY29sb3I6ICNkOTc3MDY7XG4gIH1cblxuICAucmVmcmVzaC1jb3VudGRvd24gc3ZnIHtcbiAgICB3aWR0aDogMTAwJTtcbiAgICBoZWlnaHQ6IDEwMCU7XG4gICAgZGlzcGxheTogYmxvY2s7XG4gIH1cblxuICAucmVmcmVzaC1jb3VudGRvd24gY2lyY2xlIHtcbiAgICBmaWxsOiBub25lO1xuICAgIHN0cm9rZS13aWR0aDogMjtcbiAgICB0cmFuc2l0aW9uOiBzdHJva2UtZGFzaG9mZnNldCAwLjFzIGxpbmVhcjtcbiAgfVxuXG4gIFtkYXRhLXRoZW1lPVwibGlnaHRcIl0gLnJlZnJlc2gtY291bnRkb3duIGNpcmNsZSB7XG4gICAgc3Ryb2tlOiByZ2JhKDAsIDAsIDAsIDAuMyk7XG4gIH1cblxuICBbZGF0YS10aGVtZT1cImxpZ2h0XCJdIC5yZWZyZXNoLWNvdW50ZG93biBjaXJjbGUucHJvZ3Jlc3Mge1xuICAgIHN0cm9rZTogcmdiYSgwLCAwLCAwLCAwLjgpO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5yZWZyZXNoLWNvdW50ZG93biBjaXJjbGUge1xuICAgIHN0cm9rZTogcmdiYSgyNTUsIDI1NSwgMjU1LCAwLjMpO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5yZWZyZXNoLWNvdW50ZG93biBjaXJjbGUucHJvZ3Jlc3Mge1xuICAgIHN0cm9rZTogcmdiYSgyNTUsIDI1NSwgMjU1LCAwLjgpO1xuICB9XG5cbiAgLnN0YXR1cy1mbG9hdGluZy1ib3gtZ2l0aHViIHtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGFsaWduLWl0ZW1zOiBjZW50ZXI7XG4gICAganVzdGlmeS1jb250ZW50OiBjZW50ZXI7XG4gICAgd2lkdGg6IDFlbTtcbiAgICBoZWlnaHQ6IDFlbTtcbiAgICBtaW4td2lkdGg6IDFlbTtcbiAgICBtaW4taGVpZ2h0OiAxZW07XG4gICAgZmxleC1zaHJpbms6IDA7XG4gICAgdGV4dC1kZWNvcmF0aW9uOiBub25lO1xuICAgIHRyYW5zaXRpb246IG9wYWNpdHkgMC4ycztcbiAgfVxuXG4gIC5zdGF0dXMtZmxvYXRpbmctYm94LWdpdGh1Yjpob3ZlciB7XG4gICAgb3BhY2l0eTogMC44O1xuICB9XG5cbiAgLnNyLW9ubHkge1xuICAgIHBvc2l0aW9uOiBhYnNvbHV0ZTtcbiAgICB3aWR0aDogMXB4O1xuICAgIGhlaWdodDogMXB4O1xuICAgIHBhZGRpbmc6IDA7XG4gICAgbWFyZ2luOiAtMXB4O1xuICAgIG92ZXJmbG93OiBoaWRkZW47XG4gICAgY2xpcDogcmVjdCgwLCAwLCAwLCAwKTtcbiAgICB3aGl0ZS1zcGFjZTogbm93cmFwO1xuICAgIGJvcmRlci13aWR0aDogMDtcbiAgfVxuXG4gIC5yb3V0ZS1zZWxlY3Rvci1jb250YWluZXIge1xuICAgIHBvc2l0aW9uOiByZWxhdGl2ZTtcbiAgfVxuXG4gIC5yb3V0ZS1zZWxlY3Rvci1idXR0b24ge1xuICAgIGJhY2tncm91bmQ6IG5vbmU7XG4gICAgYm9yZGVyOiBub25lO1xuICAgIGN1cnNvcjogcG9pbnRlcjtcbiAgICBwYWRkaW5nOiAwO1xuICAgIGRpc3BsYXk6IGZsZXg7XG4gICAgYWxpZ24taXRlbXM6IGNlbnRlcjtcbiAgICBqdXN0aWZ5LWNvbnRlbnQ6IGNlbnRlcjtcbiAgICBjb2xvcjogaW5oZXJpdDtcbiAgICB0cmFuc2l0aW9uOiBvcGFjaXR5IDAuMnM7XG4gICAgd2lkdGg6IDFlbTtcbiAgICBoZWlnaHQ6IDFlbTtcbiAgICBtaW4td2lkdGg6IDFlbTtcbiAgICBtaW4taGVpZ2h0OiAxZW07XG4gIH1cblxuICAucm91dGUtc2VsZWN0b3ItYnV0dG9uOmhvdmVyIHtcbiAgICBvcGFjaXR5OiAwLjg7XG4gIH1cblxuICAucm91dGUtc2VsZWN0b3ItYnV0dG9uIHN2ZyB7XG4gICAgd2lkdGg6IDEwMCU7XG4gICAgaGVpZ2h0OiAxMDAlO1xuICAgIGRpc3BsYXk6IGJsb2NrO1xuICB9XG5cbiAgLnJvdXRlLXNlbGVjdG9yLWRyb3Bkb3duIHtcbiAgICBwb3NpdGlvbjogYWJzb2x1dGU7XG4gICAgYm90dG9tOiBjYWxjKDEwMCUgKyAwLjVyZW0pO1xuICAgIHJpZ2h0OiAwO1xuICAgIGJhY2tncm91bmQ6IHdoaXRlO1xuICAgIGJvcmRlci1yYWRpdXM6IDAuMzc1cmVtO1xuICAgIGJveC1zaGFkb3c6IDAgMTBweCAxNXB4IC0zcHggcmdiYSgwLCAwLCAwLCAwLjEpLCAwIDRweCA2cHggLTJweCByZ2JhKDAsIDAsIDAsIDAuMDUpO1xuICAgIG1pbi13aWR0aDogMTUwcHg7XG4gICAgei1pbmRleDogMTAwMDtcbiAgICBvdmVyZmxvdzogaGlkZGVuO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5yb3V0ZS1zZWxlY3Rvci1kcm9wZG93biB7XG4gICAgYmFja2dyb3VuZDogIzFkMjMyYTtcbiAgICBib3gtc2hhZG93OiAwIDEwcHggMTVweCAtM3B4IHJnYmEoMCwgMCwgMCwgMC4zKSwgMCA0cHggNnB4IC0ycHggcmdiYSgwLCAwLCAwLCAwLjIpO1xuICB9XG5cbiAgLnJvdXRlLXNlbGVjdG9yLWl0ZW0ge1xuICAgIGRpc3BsYXk6IGJsb2NrO1xuICAgIHdpZHRoOiAxMDAlO1xuICAgIHBhZGRpbmc6IDAuNXJlbSAwLjc1cmVtO1xuICAgIHRleHQtYWxpZ246IGxlZnQ7XG4gICAgYmFja2dyb3VuZDogbm9uZTtcbiAgICBib3JkZXI6IG5vbmU7XG4gICAgY3Vyc29yOiBwb2ludGVyO1xuICAgIGNvbG9yOiAjMTExODI3O1xuICAgIGZvbnQtc2l6ZTogMC44NzVyZW07XG4gICAgdHJhbnNpdGlvbjogYmFja2dyb3VuZC1jb2xvciAwLjJzO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5yb3V0ZS1zZWxlY3Rvci1pdGVtIHtcbiAgICBjb2xvcjogI2Y5ZmFmYjtcbiAgfVxuXG4gIC5yb3V0ZS1zZWxlY3Rvci1pdGVtOmhvdmVyIHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiByZ2JhKDAsIDAsIDAsIDAuMDUpO1xuICB9XG5cbiAgW2RhdGEtdGhlbWU9XCJkYXJrXCJdIC5yb3V0ZS1zZWxlY3Rvci1pdGVtOmhvdmVyIHtcbiAgICBiYWNrZ3JvdW5kLWNvbG9yOiByZ2JhKDI1NSwgMjU1LCAyNTUsIDAuMSk7XG4gIH1cblxuICAucm91dGUtc2VsZWN0b3ItaXRlbS5hY3RpdmUge1xuICAgIGJhY2tncm91bmQtY29sb3I6IHJnYmEoOCwgMTIzLCAxOTYsIDAuMSk7XG4gICAgZm9udC13ZWlnaHQ6IDYwMDtcbiAgfVxuXG4gIFtkYXRhLXRoZW1lPVwiZGFya1wiXSAucm91dGUtc2VsZWN0b3ItaXRlbS5hY3RpdmUge1xuICAgIGJhY2tncm91bmQtY29sb3I6IHJnYmEoOCwgMTIzLCAxOTYsIDAuMik7XG4gIH1cbjwvc3R5bGU+XG4iXSwibmFtZXMiOltdLCJtYXBwaW5ncyI6IjtBQXNJQSxFQUFFLG1DQUFvQixDQUFDO0FBQ3ZCLElBQUksZUFBZTtBQUNuQixJQUFJLGNBQWM7QUFDbEIsSUFBSSxTQUFTO0FBQ2IsSUFBSSwyQkFBMkI7QUFDL0IsSUFBSSxhQUFhO0FBQ2pCLElBQUksbUJBQW1CO0FBQ3ZCLElBQUksV0FBVztBQUNmLElBQUksc0JBQXNCO0FBQzFCLElBQUksMENBQTBDO0FBQzlDLElBQUksMEJBQTBCO0FBQzlCLElBQUkscUJBQXFCO0FBQ3pCLElBQUksYUFBYTtBQUNqQjs7QUFFQSxjQUFFO0FBQ0Y7QUFDQTs7QUFFQSxjQUFFO0FBQ0Y7QUFDQTs7QUFFQSxFQUFFLHdDQUF5QixDQUFDO0FBQzVCLElBQUksYUFBYTtBQUNqQixJQUFJLG1CQUFtQjtBQUN2QixJQUFJLHVCQUF1QjtBQUMzQixJQUFJLFVBQVU7QUFDZCxJQUFJLFdBQVc7QUFDZixJQUFJLGNBQWM7QUFDbEIsSUFBSSxlQUFlO0FBQ25CLElBQUksY0FBYztBQUNsQjs7QUFFQSxFQUFFLDZCQUFjLENBQUM7QUFDakIsSUFBSSxnQkFBZ0I7QUFDcEIsSUFB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 */'
};

export default function StatusBar($$anchor, $$props) {
	$.check_target(new.target);
	$.push($$props, true, StatusBar);
	$.append_styles($$anchor, $$css);

	let routes = $.prop($$props, 'routes', 19, () => []),
		currentRoutePath = $.prop($$props, 'currentRoutePath', 3, null),
		onRouteChange = $.prop($$props, 'onRouteChange', 3, () => {});

	let showRouteSelector = $.tag($.state(false), 'showRouteSelector');

	function toggleRouteSelector() {
		$.set(showRouteSelector, !$.get(showRouteSelector));
	}

	function selectRoute(path) {
		onRouteChange()(path);
		$.set(showRouteSelector, false);
	}

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
							50,
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
					46,
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
			42,
			4
		);
	}

	$.reset(div_1);

	var button = $.sibling(div_1, 4);

	button.__click = function (...$$args) {
		$.apply(() => $$props.onConfigClick, this, $$args, StatusBar, [71, 13]);
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
						118,
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
					116,
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
			97,
			2
		);
	}

	$.reset(div);
	$.template_effect(() => $.set_attribute(div_1, 'aria-label', `API status: ${$$props.apiStatus ?? ''}`));
	$.append($$anchor, div);

	return $.pop($$exports);
}

$.delegate(['click']);