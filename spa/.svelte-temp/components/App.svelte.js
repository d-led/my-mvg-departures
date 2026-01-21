import 'svelte/internal/disclose-version';

App[$.FILENAME] = 'src/components/App.svelte';

import * as $ from 'svelte/internal/client';
import { onMount } from "svelte";
import { ConfigParser } from "../adapters/config/config-parser.js";
import { MvgDepartureRepository } from "../adapters/mvg/mvg-departure-repository.js";
import { LocalStorageCache } from "../adapters/storage/local-storage-cache.js";
import { LocalStorageConfigStorage } from "../adapters/storage/local-storage-config-storage.js";
import { DepartureGroupingService } from "../application/services/departure-grouping-service.js";
import { ApiPoller } from "../application/services/api-poller.js";
import ConfigModal from "./ConfigModal.svelte";
import DeparturesList from "./DeparturesList.svelte";
import StatusBar from "./StatusBar.svelte";

var root = $.add_locations($.from_html(`<div class="container svelte-nejbyb"><div class="header-section svelte-nejbyb"><h1 class="svelte-nejbyb"> </h1> <div class="last-update svelte-nejbyb" aria-live="polite" aria-atomic="true"><!></div></div> <div id="departures" role="region" aria-label="Departure information" aria-live="polite" aria-atomic="false" class="svelte-nejbyb"><!></div> <!> <!></div>`), App[$.FILENAME], [[129, 0, [[130, 2, [[131, 4], [132, 4]]], [139, 2]]]]);

const $$css = {
	hash: 'svelte-nejbyb',
	code: '\n  .container.svelte-nejbyb {\n    width: 100vw;\n    max-width: 100vw;\n    height: 100vh;\n    margin: 0;\n    padding: 0;\n    display: flex;\n    flex-direction: column;\n    overflow: hidden;\n    box-sizing: border-box;\n  }\n\n  .header-section.svelte-nejbyb {\n    display: none;\n  }\n\n  h1.svelte-nejbyb {\n    display: none;\n  }\n\n  .last-update.svelte-nejbyb {\n    display: none;\n  }\n\n  #departures.svelte-nejbyb {\n    flex: 1 1 100%;\n    overflow-y: auto;\n    overflow-x: hidden;\n    position: relative;\n    width: 100%;\n    height: 100%;\n    box-sizing: border-box;\n    padding: 0;\n    margin: 0;\n  }\n\n/*# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiQXBwLnN2ZWx0ZSIsInNvdXJjZXMiOlsiQXBwLnN2ZWx0ZSJdLCJzb3VyY2VzQ29udGVudCI6WyI8c2NyaXB0IGxhbmc9XCJ0c1wiPlxuICBpbXBvcnQgeyBvbk1vdW50IH0gZnJvbSBcInN2ZWx0ZVwiO1xuICBpbXBvcnQgeyBDb25maWdQYXJzZXIgfSBmcm9tIFwiLi4vYWRhcHRlcnMvY29uZmlnL2NvbmZpZy1wYXJzZXIuanNcIjtcbiAgaW1wb3J0IHsgTXZnRGVwYXJ0dXJlUmVwb3NpdG9yeSB9IGZyb20gXCIuLi9hZGFwdGVycy9tdmcvbXZnLWRlcGFydHVyZS1yZXBvc2l0b3J5LmpzXCI7XG4gIGltcG9ydCB7IExvY2FsU3RvcmFnZUNhY2hlIH0gZnJvbSBcIi4uL2FkYXB0ZXJzL3N0b3JhZ2UvbG9jYWwtc3RvcmFnZS1jYWNoZS5qc1wiO1xuICBpbXBvcnQgeyBMb2NhbFN0b3JhZ2VDb25maWdTdG9yYWdlIH0gZnJvbSBcIi4uL2FkYXB0ZXJzL3N0b3JhZ2UvbG9jYWwtc3RvcmFnZS1jb25maWctc3RvcmFnZS5qc1wiO1xuICBpbXBvcnQgeyBEZXBhcnR1cmVHcm91cGluZ1NlcnZpY2UgfSBmcm9tIFwiLi4vYXBwbGljYXRpb24vc2VydmljZXMvZGVwYXJ0dXJlLWdyb3VwaW5nLXNlcnZpY2UuanNcIjtcbiAgaW1wb3J0IHsgQXBpUG9sbGVyIH0gZnJvbSBcIi4uL2FwcGxpY2F0aW9uL3NlcnZpY2VzL2FwaS1wb2xsZXIuanNcIjtcbiAgaW1wb3J0IHR5cGUgeyBBcHBDb25maWcsIFJvdXRlQ29uZmlndXJhdGlvbiwgR3JvdXBlZERlcGFydHVyZXMgfSBmcm9tIFwiLi4vZG9tYWluL21vZGVscy9pbmRleC5qc1wiO1xuICBpbXBvcnQgQ29uZmlnTW9kYWwgZnJvbSBcIi4vQ29uZmlnTW9kYWwuc3ZlbHRlXCI7XG4gIGltcG9ydCBEZXBhcnR1cmVzTGlzdCBmcm9tIFwiLi9EZXBhcnR1cmVzTGlzdC5zdmVsdGVcIjtcbiAgaW1wb3J0IFN0YXR1c0JhciBmcm9tIFwiLi9TdGF0dXNCYXIuc3ZlbHRlXCI7XG5cbiAgbGV0IGNvbmZpZyA9ICRzdGF0ZTxBcHBDb25maWcgfCBudWxsPihudWxsKTtcbiAgbGV0IGN1cnJlbnRSb3V0ZSA9ICRzdGF0ZTxSb3V0ZUNvbmZpZ3VyYXRpb24gfCBudWxsPihudWxsKTtcbiAgbGV0IGdyb3VwZWREZXBhcnR1cmVzID0gJHN0YXRlPEdyb3VwZWREZXBhcnR1cmVzW10+KFtdKTtcbiAgbGV0IHNob3dDb25maWdNb2RhbCA9ICRzdGF0ZShmYWxzZSk7XG4gIGxldCBhcGlTdGF0dXMgPSAkc3RhdGU8XCJzdWNjZXNzXCIgfCBcImVycm9yXCIgfCBcImRlZ3JhZGVkXCIgfCBcInVua25vd25cIj4oXCJ1bmtub3duXCIpO1xuICBsZXQgbGFzdFVwZGF0ZVRpbWUgPSAkc3RhdGU8RGF0ZSB8IG51bGw+KG51bGwpO1xuICBsZXQgcG9sbGVyOiBBcGlQb2xsZXIgfCBudWxsID0gbnVsbDtcblxuICBjb25zdCBjb25maWdTdG9yYWdlID0gbmV3IExvY2FsU3RvcmFnZUNvbmZpZ1N0b3JhZ2UoKTtcbiAgY29uc3QgY29uZmlnUGFyc2VyID0gbmV3IENvbmZpZ1BhcnNlcigpO1xuICBjb25zdCBkZXBhcnR1cmVSZXBvc2l0b3J5ID0gbmV3IE12Z0RlcGFydHVyZVJlcG9zaXRvcnkoKTtcbiAgY29uc3QgY2FjaGUgPSBuZXcgTG9jYWxTdG9yYWdlQ2FjaGUoKTtcbiAgY29uc3QgZ3JvdXBpbmdTZXJ2aWNlID0gbmV3IERlcGFydHVyZUdyb3VwaW5nU2VydmljZShkZXBhcnR1cmVSZXBvc2l0b3J5KTtcblxuICBvbk1vdW50KGFzeW5jICgpID0+IHtcbiAgICBhd2FpdCBsb2FkQ29uZmlnKCk7XG4gICAgYXdhaXQgaW5pdGlhbGl6ZVJvdXRlKCk7XG4gIH0pO1xuXG4gIGFzeW5jIGZ1bmN0aW9uIGxvYWRDb25maWcoKSB7XG4gICAgY29uc3Qgc3RvcmVkID0gYXdhaXQgY29uZmlnU3RvcmFnZS5nZXRDb25maWcoKTtcbiAgICBpZiAoc3RvcmVkKSB7XG4gICAgICBjb25maWcgPSBzdG9yZWQ7XG4gICAgfVxuICB9XG5cbiAgYXN5bmMgZnVuY3Rpb24gaW5pdGlhbGl6ZVJvdXRlKCkge1xuICAgIGlmICghY29uZmlnIHx8IGNvbmZpZy5yb3V0ZXMubGVuZ3RoID09PSAwKSB7XG4gICAgICByZXR1cm47XG4gICAgfVxuXG4gICAgLy8gR2V0IGN1cnJlbnQgcm91dGUgZnJvbSBVUkwgb3Igc3RvcmFnZVxuICAgIGNvbnN0IHBhdGggPSB3aW5kb3cubG9jYXRpb24ucGF0aG5hbWUgfHwgXCIvXCI7XG4gICAgY29uc3Qgc3RvcmVkUGF0aCA9IGF3YWl0IGNvbmZpZ1N0b3JhZ2UuZ2V0Q3VycmVudFJvdXRlUGF0aCgpO1xuICAgIGNvbnN0IHJvdXRlUGF0aCA9IHN0b3JlZFBhdGggfHwgcGF0aDtcblxuICAgIGNvbnN0IHJvdXRlID0gY29uZmlnLnJvdXRlcy5maW5kKChyKSA9PiByLnBhdGggPT09IHJvdXRlUGF0aCkgfHwgY29uZmlnLnJvdXRlc1swXTtcbiAgICBpZiAocm91dGUpIHtcbiAgICAgIGF3YWl0IHN3aXRjaFJvdXRlKHJvdXRlKTtcbiAgICB9XG4gIH1cblxuICBhc3luYyBmdW5jdGlvbiBzd2l0Y2hSb3V0ZShyb3V0ZTogUm91dGVDb25maWd1cmF0aW9uKSB7XG4gICAgLy8gU3RvcCBleGlzdGluZyBwb2xsZXJcbiAgICBpZiAocG9sbGVyKSB7XG4gICAgICBwb2xsZXIuc3RvcCgpO1xuICAgICAgcG9sbGVyID0gbnVsbDtcbiAgICB9XG5cbiAgICBjdXJyZW50Um91dGUgPSByb3V0ZTtcbiAgICBhd2FpdCBjb25maWdTdG9yYWdlLnNldEN1cnJlbnRSb3V0ZVBhdGgocm91dGUucGF0aCk7XG4gICAgd2luZG93Lmhpc3RvcnkucHVzaFN0YXRlKHt9LCBcIlwiLCByb3V0ZS5wYXRoKTtcblxuICAgIC8vIFN0YXJ0IHBvbGxpbmcgZm9yIGFsbCBzdG9wcyBpbiByb3V0ZVxuICAgIGlmIChyb3V0ZS5zdG9wcy5sZW5ndGggPiAwKSB7XG4gICAgICAvLyBGb3Igbm93LCBwb2xsIHRoZSBmaXJzdCBzdG9wICh3ZSBjYW4gZXh0ZW5kIHRvIG11bHRpcGxlIHN0b3BzIGxhdGVyKVxuICAgICAgY29uc3Qgc3RvcENvbmZpZyA9IHJvdXRlLnN0b3BzWzBdO1xuICAgICAgY29uc3QgcmVmcmVzaEludGVydmFsID0gcm91dGUucmVmcmVzaEludGVydmFsU2Vjb25kcyA/PyByb3V0ZS5kaXNwbGF5Py5yZWZyZXNoSW50ZXJ2YWxTZWNvbmRzID8/IDIwO1xuXG4gICAgICBwb2xsZXIgPSBuZXcgQXBpUG9sbGVyKFxuICAgICAgICBkZXBhcnR1cmVSZXBvc2l0b3J5LFxuICAgICAgICBjYWNoZSxcbiAgICAgICAgZ3JvdXBpbmdTZXJ2aWNlLFxuICAgICAgICBzdG9wQ29uZmlnLFxuICAgICAgICByZWZyZXNoSW50ZXJ2YWwsXG4gICAgICAgIHtcbiAgICAgICAgICBvblVwZGF0ZTogKGdyb3VwcykgPT4ge1xuICAgICAgICAgICAgZ3JvdXBlZERlcGFydHVyZXMgPSBncm91cHM7XG4gICAgICAgICAgICBhcGlTdGF0dXMgPSBcInN1Y2Nlc3NcIjtcbiAgICAgICAgICAgIGxhc3RVcGRhdGVUaW1lID0gbmV3IERhdGUoKTtcbiAgICAgICAgICB9LFxuICAgICAgICAgIG9uRXJyb3I6IChlcnJvcikgPT4ge1xuICAgICAgICAgICAgY29uc29sZS5lcnJvcihcIkFQSSBwb2xsIGVycm9yOlwiLCBlcnJvcik7XG4gICAgICAgICAgICBhcGlTdGF0dXMgPSBcImVycm9yXCI7XG4gICAgICAgICAgfSxcbiAgICAgICAgfVxuICAgICAgKTtcblxuICAgICAgYXdhaXQgcG9sbGVyLnN0YXJ0KCk7XG4gICAgfVxuICB9XG5cbiAgZnVuY3Rpb24gaGFuZGxlQ29uZmlnU2F2ZSh0b21sQ29uZmlnOiBzdHJpbmcpIHtcbiAgICB0cnkge1xuICAgICAgY29uc3QgcGFyc2VkID0gY29uZmlnUGFyc2VyLnBhcnNlVG9tbCh0b21sQ29uZmlnKTtcbiAgICAgIGNvbmZpZ1N0b3JhZ2Uuc2F2ZUNvbmZpZyhwYXJzZWQpLnRoZW4oKCkgPT4ge1xuICAgICAgICBjb25maWcgPSBwYXJzZWQ7XG4gICAgICAgIHNob3dDb25maWdNb2RhbCA9IGZhbHNlO1xuICAgICAgICBpbml0aWFsaXplUm91dGUoKTtcbiAgICAgIH0pO1xuICAgIH0gY2F0Y2ggKGVycm9yKSB7XG4gICAgICBjb25zb2xlLmVycm9yKFwiRmFpbGVkIHRvIHBhcnNlIGNvbmZpZzpcIiwgZXJyb3IpO1xuICAgICAgYWxlcnQoXCJGYWlsZWQgdG8gcGFyc2UgVE9NTCBjb25maWcuIFBsZWFzZSBjaGVjayB0aGUgZm9ybWF0LlwiKTtcbiAgICB9XG4gIH1cblxuICBmdW5jdGlvbiBoYW5kbGVDb25maWdDYW5jZWwoKSB7XG4gICAgc2hvd0NvbmZpZ01vZGFsID0gZmFsc2U7XG4gIH1cblxuICBmdW5jdGlvbiBvcGVuQ29uZmlnKCkge1xuICAgIHNob3dDb25maWdNb2RhbCA9IHRydWU7XG4gIH1cblxuICBmdW5jdGlvbiBoYW5kbGVSb3V0ZUNoYW5nZShwYXRoOiBzdHJpbmcpIHtcbiAgICBpZiAoIWNvbmZpZykge1xuICAgICAgcmV0dXJuO1xuICAgIH1cbiAgICBjb25zdCByb3V0ZSA9IGNvbmZpZy5yb3V0ZXMuZmluZCgocikgPT4gci5wYXRoID09PSBwYXRoKTtcbiAgICBpZiAocm91dGUpIHtcbiAgICAgIHN3aXRjaFJvdXRlKHJvdXRlKTtcbiAgICB9XG4gIH1cbjwvc2NyaXB0PlxuXG48ZGl2IGNsYXNzPVwiY29udGFpbmVyXCI+XG4gIDxkaXYgY2xhc3M9XCJoZWFkZXItc2VjdGlvblwiPlxuICAgIDxoMT57Y3VycmVudFJvdXRlPy5kaXNwbGF5Py50aXRsZSA/PyBcIk1WRyBEZXBhcnR1cmVzXCJ9PC9oMT5cbiAgICA8ZGl2IGNsYXNzPVwibGFzdC11cGRhdGVcIiBhcmlhLWxpdmU9XCJwb2xpdGVcIiBhcmlhLWF0b21pYz1cInRydWVcIj5cbiAgICAgIHsjaWYgbGFzdFVwZGF0ZVRpbWV9XG4gICAgICAgIExhc3QgdXBkYXRlZDoge2xhc3RVcGRhdGVUaW1lLnRvTG9jYWxlVGltZVN0cmluZygpfVxuICAgICAgey9pZn1cbiAgICA8L2Rpdj5cbiAgPC9kaXY+XG5cbiAgPGRpdiBpZD1cImRlcGFydHVyZXNcIiByb2xlPVwicmVnaW9uXCIgYXJpYS1sYWJlbD1cIkRlcGFydHVyZSBpbmZvcm1hdGlvblwiIGFyaWEtbGl2ZT1cInBvbGl0ZVwiIGFyaWEtYXRvbWljPVwiZmFsc2VcIj5cbiAgICA8RGVwYXJ0dXJlc0xpc3Qge2dyb3VwZWREZXBhcnR1cmVzfSBkaXNwbGF5PXtjdXJyZW50Um91dGU/LmRpc3BsYXl9IC8+XG4gIDwvZGl2PlxuXG4gIDxTdGF0dXNCYXJcbiAgICB7YXBpU3RhdHVzfVxuICAgIHtzaG93Q29uZmlnTW9kYWx9XG4gICAgb25Db25maWdDbGljaz17b3BlbkNvbmZpZ31cbiAgICByb3V0ZXM9e2NvbmZpZz8ucm91dGVzID8/IFtdfVxuICAgIGN1cnJlbnRSb3V0ZVBhdGg9e2N1cnJlbnRSb3V0ZT8ucGF0aCA/PyBudWxsfVxuICAgIG9uUm91dGVDaGFuZ2U9e2hhbmRsZVJvdXRlQ2hhbmdlfVxuICAvPlxuXG4gIHsjaWYgc2hvd0NvbmZpZ01vZGFsfVxuICAgIDxDb25maWdNb2RhbFxuICAgICAgY3VycmVudENvbmZpZz17Y29uZmlnfVxuICAgICAgb25TYXZlPXtoYW5kbGVDb25maWdTYXZlfVxuICAgICAgb25DYW5jZWw9e2hhbmRsZUNvbmZpZ0NhbmNlbH1cbiAgICAvPlxuICB7L2lmfVxuPC9kaXY+XG5cbjxzdHlsZT5cbiAgLmNvbnRhaW5lciB7XG4gICAgd2lkdGg6IDEwMHZ3O1xuICAgIG1heC13aWR0aDogMTAwdnc7XG4gICAgaGVpZ2h0OiAxMDB2aDtcbiAgICBtYXJnaW46IDA7XG4gICAgcGFkZGluZzogMDtcbiAgICBkaXNwbGF5OiBmbGV4O1xuICAgIGZsZXgtZGlyZWN0aW9uOiBjb2x1bW47XG4gICAgb3ZlcmZsb3c6IGhpZGRlbjtcbiAgICBib3gtc2l6aW5nOiBib3JkZXItYm94O1xuICB9XG5cbiAgLmhlYWRlci1zZWN0aW9uIHtcbiAgICBkaXNwbGF5OiBub25lO1xuICB9XG5cbiAgaDEge1xuICAgIGRpc3BsYXk6IG5vbmU7XG4gIH1cblxuICAubGFzdC11cGRhdGUge1xuICAgIGRpc3BsYXk6IG5vbmU7XG4gIH1cblxuICAjZGVwYXJ0dXJlcyB7XG4gICAgZmxleDogMSAxIDEwMCU7XG4gICAgb3ZlcmZsb3cteTogYXV0bztcbiAgICBvdmVyZmxvdy14OiBoaWRkZW47XG4gICAgcG9zaXRpb246IHJlbGF0aXZlO1xuICAgIHdpZHRoOiAxMDAlO1xuICAgIGhlaWdodDogMTAwJTtcbiAgICBib3gtc2l6aW5nOiBib3JkZXItYm94O1xuICAgIHBhZGRpbmc6IDA7XG4gICAgbWFyZ2luOiAwO1xuICB9XG48L3N0eWxlPlxuIl0sIm5hbWVzIjpbXSwibWFwcGluZ3MiOiI7QUFpS0EsRUFBRSx3QkFBVSxDQUFDO0FBQ2IsSUFBSSxZQUFZO0FBQ2hCLElBQUksZ0JBQWdCO0FBQ3BCLElBQUksYUFBYTtBQUNqQixJQUFJLFNBQVM7QUFDYixJQUFJLFVBQVU7QUFDZCxJQUFJLGFBQWE7QUFDakIsSUFBSSxzQkFBc0I7QUFDMUIsSUFBSSxnQkFBZ0I7QUFDcEIsSUFBSSxzQkFBc0I7QUFDMUI7O0FBRUEsRUFBRSw2QkFBZSxDQUFDO0FBQ2xCLElBQUksYUFBYTtBQUNqQjs7QUFFQSxFQUFFLGdCQUFFLENBQUM7QUFDTCxJQUFJLGFBQWE7QUFDakI7O0FBRUEsRUFBRSwwQkFBWSxDQUFDO0FBQ2YsSUFBSSxhQUFhO0FBQ2pCOztBQUVBLEVBQUUseUJBQVcsQ0FBQztBQUNkLElBQUksY0FBYztBQUNsQixJQUFJLGdCQUFnQjtBQUNwQixJQUFJLGtCQUFrQjtBQUN0QixJQUFJLGtCQUFrQjtBQUN0QixJQUFJLFdBQVc7QUFDZixJQUFJLFlBQVk7QUFDaEIsSUFBSSxzQkFBc0I7QUFDMUIsSUFBSSxVQUFVO0FBQ2QsSUFBSSxTQUFTO0FBQ2I7In0= */'
};

export default function App($$anchor, $$props) {
	$.check_target(new.target);
	$.push($$props, true, App);
	$.append_styles($$anchor, $$css);

	let config = $.tag($.state(null), 'config');
	let currentRoute = $.tag($.state(null), 'currentRoute');
	let groupedDepartures = $.tag($.state($.proxy([])), 'groupedDepartures');
	let showConfigModal = $.tag($.state(false), 'showConfigModal');
	let apiStatus = $.tag($.state("unknown"), 'apiStatus');
	let lastUpdateTime = $.tag($.state(null), 'lastUpdateTime');
	let poller = null;
	const configStorage = new LocalStorageConfigStorage();
	const configParser = new ConfigParser();
	const departureRepository = new MvgDepartureRepository();
	const cache = new LocalStorageCache();
	const groupingService = new DepartureGroupingService(departureRepository);

	onMount(async () => {
		(await $.track_reactivity_loss(loadConfig()))();
		(await $.track_reactivity_loss(initializeRoute()))();
	});

	async function loadConfig() {
		const stored = (await $.track_reactivity_loss(configStorage.getConfig()))();

		if (stored) {
			$.set(config, stored, true);
		}
	}

	async function initializeRoute() {
		if (!$.get(config) || $.strict_equals($.get(config).routes.length, 0)) {
			return;
		}

		// Get current route from URL or storage
		const path = window.location.pathname || "/";

		const storedPath = (await $.track_reactivity_loss(configStorage.getCurrentRoutePath()))();
		const routePath = storedPath || path;
		const route = $.get(config).routes.find((r) => $.strict_equals(r.path, routePath)) || $.get(config).routes[0];

		if (route) {
			(await $.track_reactivity_loss(switchRoute(route)))();
		}
	}

	async function switchRoute(route) {
		// Stop existing poller
		if (poller) {
			poller.stop();
			poller = null;
		}

		$.set(currentRoute, route, true);
		(await $.track_reactivity_loss(configStorage.setCurrentRoutePath(route.path)))();
		window.history.pushState({}, "", route.path);

		// Start polling for all stops in route
		if (route.stops.length > 0) {
			// For now, poll the first stop (we can extend to multiple stops later)
			const stopConfig = route.stops[0];

			const refreshInterval = route.refreshIntervalSeconds ?? route.display?.refreshIntervalSeconds ?? 20;

			poller = new ApiPoller(departureRepository, cache, groupingService, stopConfig, refreshInterval, {
				onUpdate: (groups) => {
					$.set(groupedDepartures, groups, true);
					$.set(apiStatus, "success");
					$.set(lastUpdateTime, new Date(), true);
				},

				onError: (error) => {
					console.error(...$.log_if_contains_state('error', "API poll error:", error));
					$.set(apiStatus, "error");
				}
			});

			(await $.track_reactivity_loss(poller.start()))();
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
			switchRoute(route);
		}
	}

	var $$exports = { ...$.legacy_api() };
	var div = root();
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
			133,
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
			140,
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
				onRouteChange: handleRouteChange
			}),
			'component',
			App,
			143,
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
				153,
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
			152,
			2
		);
	}

	$.reset(div);
	$.template_effect(() => $.set_text(text, $.get(currentRoute)?.display?.title ?? "MVG Departures"));
	$.append($$anchor, div);

	return $.pop($$exports);
}