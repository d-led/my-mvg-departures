"""PyView web adapter for displaying departures."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any

from mvg_departures.adapters.config import AppConfig
from mvg_departures.domain.models import (
    GroupedDepartures,
    RouteConfiguration,
)
from mvg_departures.domain.ports import (
    DepartureGroupingService,
    DepartureRepository,
    DisplayAdapter,
)

from .cache import SharedDepartureCache
from .fetchers import DepartureFetcher
from .presence import get_presence_tracker
from .servers import StaticFileServer
from .state import State
from .views.departures import create_departures_live_view
from .views.departures.departures import (
    DisplayConfiguration,
    LiveViewConfiguration,
    LiveViewDependencies,
    RouteDisplaySettings,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from mvg_departures.domain.models import Departure


@dataclass(frozen=True)
class PyViewWebAdapterConfig:
    """Configuration for PyViewWebAdapter initialization."""

    grouping_service: DepartureGroupingService
    route_configs: list[RouteConfiguration]
    config: AppConfig
    departure_repository: DepartureRepository
    session: ClientSession | None = None


class PyViewWebAdapter(DisplayAdapter):
    """PyView-based web adapter for displaying departures."""

    def _validate_init_parameters(
        self,
        grouping_service: DepartureGroupingService,
        route_configs: list[RouteConfiguration],
        config: AppConfig,
        departure_repository: DepartureRepository,
    ) -> None:
        """Validate initialization parameters."""
        if not isinstance(config, AppConfig):
            raise TypeError("config must be an AppConfig instance")
        if not isinstance(route_configs, list) or not all(
            isinstance(rc, RouteConfiguration) for rc in route_configs
        ):
            raise TypeError("route_configs must be a list of RouteConfiguration instances")
        if not hasattr(grouping_service, "group_departures") or not callable(
            getattr(grouping_service, "group_departures", None)
        ):
            raise TypeError("grouping_service must implement DepartureGroupingService protocol")
        if not hasattr(departure_repository, "get_departures") or not callable(
            getattr(departure_repository, "get_departures", None)
        ):
            raise TypeError("departure_repository must implement DepartureRepository protocol")

    def _initialize_route_states(self, route_configs: list[RouteConfiguration]) -> dict[str, State]:
        """Initialize state managers for each route."""
        return {
            route_config.path: State(
                route_path=route_config.path,
                max_sessions_per_browser=self.config.max_sessions_per_browser,
            )
            for route_config in route_configs
        }

    def __init__(self, adapter_config: PyViewWebAdapterConfig) -> None:
        """Initialize the web adapter.

        Args:
            adapter_config: Complete configuration for the adapter including services,
                           route configurations, and optional session.
        """
        self._validate_init_parameters(
            adapter_config.grouping_service,
            adapter_config.route_configs,
            adapter_config.config,
            adapter_config.departure_repository,
        )

        self.grouping_service = adapter_config.grouping_service
        self.route_configs = adapter_config.route_configs
        self.config = adapter_config.config
        self.departure_repository = adapter_config.departure_repository
        self.session = adapter_config.session
        self._update_task: asyncio.Task | None = None
        self._server: Any | None = None
        self.route_states = self._initialize_route_states(adapter_config.route_configs)
        self._shared_departure_cache = SharedDepartureCache()
        self._departure_fetcher: DepartureFetcher | None = None

    async def display_departures(self, direction_groups: list[GroupedDepartures]) -> None:
        """Display grouped departures (not used directly, handled by LiveView)."""
        # This is handled by the LiveView's periodic updates

    def _setup_favicon_and_root_template(self, app: Any) -> None:
        """Set up default favicon and root template for the app.

        Args:
            app: The PyView application instance.
        """
        from markupsafe import Markup
        from pyview.playground.favicon import generate_favicon_svg
        from pyview.template import defaultRootTemplate
        from starlette.responses import Response
        from starlette.routing import Route

        # Generate default favicon SVG from global title using banner color from config
        default_favicon_svg = generate_favicon_svg(
            self.config.title,
            bg_color=self.config.banner_color or "#087BC4",
            text_color="#FFFFFF",
        )

        # Add default favicon route
        async def default_favicon_route(_request: Any) -> Response:
            response = Response(content=default_favicon_svg, media_type="image/svg+xml")
            response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
            return response

        app.routes.append(Route("/favicon.svg", default_favicon_route, methods=["GET"]))

        # Add default favicon link to CSS/head content
        favicon_link = Markup('<link rel="icon" href="/favicon.svg" type="image/svg+xml">')

        # Set rootTemplate with default title
        app.rootTemplate = defaultRootTemplate(
            title=self.config.title,
            title_suffix="",
            css=favicon_link,
        )

    def _add_route_favicon(self, app: Any, route_path: str, route_title: str) -> None:
        """Add route-specific favicon if route has custom title.

        Args:
            app: The PyView application instance.
            route_path: The route path.
            route_title: The route-specific title.
        """
        from pyview.playground.favicon import generate_favicon_svg
        from starlette.responses import Response
        from starlette.routing import Route

        route_favicon_svg = generate_favicon_svg(
            route_title,
            bg_color=self.config.banner_color or "#087BC4",
            text_color="#FFFFFF",
        )

        def create_favicon_handler(svg_content: str) -> Any:
            async def favicon_handler(_request: Any) -> Response:
                response = Response(content=svg_content, media_type="image/svg+xml")
                response.headers["Cache-Control"] = "public, max-age=60, must-revalidate"
                return response

            return favicon_handler

        favicon_path = route_path.rstrip("/") + "/favicon.svg"
        route_favicon_handler = create_favicon_handler(route_favicon_svg)
        app.routes.append(Route(favicon_path, route_favicon_handler, methods=["GET"]))
        logger.info(f"Added route-specific favicon at {favicon_path} for '{route_title}'")

    def _build_live_view_config(
        self, route_config: RouteConfiguration, presence_tracker: Any
    ) -> LiveViewConfiguration:
        """Build LiveViewConfiguration for a route."""
        route_state = self.route_states[route_config.path]
        dependencies = LiveViewDependencies(
            state_manager=route_state,
            grouping_service=self.grouping_service,
            stop_configs=route_config.stop_configs,
            config=self.config,
            presence_tracker=presence_tracker,
        )
        route_display = RouteDisplaySettings(title=route_config.title, theme=route_config.theme)
        display_config = DisplayConfiguration(
            fill_vertical_space=route_config.fill_vertical_space,
            font_scaling_factor_when_filling=route_config.font_scaling_factor_when_filling,
            random_header_colors=route_config.random_header_colors,
            header_background_brightness=route_config.header_background_brightness,
            random_color_salt=route_config.random_color_salt,
            split_show_delay=route_config.split_show_delay,
        )
        return LiveViewConfiguration(
            dependencies=dependencies,
            route_display=route_display,
            display_config=display_config,
        )

    def _log_route_registration(self, route_config: RouteConfiguration) -> None:
        """Log route registration details."""
        parts = [
            f"Registering route at path '{route_config.path}' with {len(route_config.stop_configs)} stops"
        ]
        if route_config.title:
            parts.append(f" and title '{route_config.title}'")
        if route_config.fill_vertical_space:
            parts.append(f" (fill_vertical_space={route_config.fill_vertical_space})")
        logger.info("".join(parts))

    def _register_live_views(self, app: Any, presence_tracker: Any) -> None:
        """Register LiveViews for all routes."""
        for route_config in self.route_configs:
            if route_config.title:
                self._add_route_favicon(app, route_config.path, route_config.title)

            self._log_route_registration(route_config)
            live_view_config = self._build_live_view_config(route_config, presence_tracker)
            live_view_class = create_departures_live_view(live_view_config)
            app.add_live_view(route_config.path, live_view_class)
            logger.info(f"Successfully registered route at path '{route_config.path}'")

    async def _handle_reset_connections(self, request: Any, presence_tracker: Any) -> Any:
        """Handle reset connections admin endpoint."""
        from starlette.responses import JSONResponse

        expected_token = self.config.admin_command_token
        if not expected_token:
            return JSONResponse(
                {"error": "admin endpoint disabled - ADMIN_COMMAND_TOKEN not configured"},
                status_code=503,
            )

        provided_token = request.headers.get("X-Admin-Token", "")
        if provided_token != expected_token:
            logger.warning("Unauthorized attempt to call reset_connections admin endpoint")
            return JSONResponse({"error": "forbidden"}, status_code=403)

        total_disconnected = self._reset_all_route_sockets()
        sync_result = presence_tracker.sync_with_registered_sockets({})
        added, removed = sync_result.added_count, sync_result.removed_count

        await self._broadcast_reload_updates()

        logger.info(
            "Admin reset_connections completed: "
            f"disconnected_sockets={total_disconnected}, "
            f"presence_added={added}, presence_removed={removed}"
        )

        return JSONResponse(
            {
                "status": "ok",
                "disconnected_sockets": total_disconnected,
                "presence_added": added,
                "presence_removed": removed,
            }
        )

    def _setup_admin_endpoints(self, app: Any, presence_tracker: Any) -> None:
        """Set up admin maintenance endpoints.

        Args:
            app: The PyView application instance.
            presence_tracker: The presence tracker instance.
        """
        from starlette.responses import Response
        from starlette.routing import Route

        async def reset_connections(request: Any) -> Any:
            return await self._handle_reset_connections(request, presence_tracker)

        app.routes.append(Route("/admin/reset-connections", reset_connections, methods=["POST"]))

        async def healthz(_request: Any) -> Response:
            """Health check endpoint for load balancers and monitoring."""
            return Response(content="Ok", media_type="text/plain")

        app.routes.append(Route("/healthz", healthz, methods=["GET"]))

    def _reset_all_route_sockets(self) -> int:
        """Unregister all sockets from all route states and bump reload_request_id.

        Returns:
            Total number of sockets disconnected.
        """
        total_disconnected = 0

        for route_path, route_state in self.route_states.items():
            sockets_to_unregister = list(route_state.connected_sockets)
            if not sockets_to_unregister:
                continue

            logger.info(
                f"Admin reset_connections: unregistering {len(sockets_to_unregister)} "
                f"sockets for route '{route_path}'"
            )
            for socket in sockets_to_unregister:
                route_state.unregister_socket(socket)
                total_disconnected += 1

            # Bump reload_request_id for this route
            try:
                route_state.departures_state.reload_request_id += 1
            except Exception:
                logger.exception("Failed to increment reload_request_id for route '%s'", route_path)

        return total_disconnected

    async def _broadcast_reload_updates(self) -> None:
        """Broadcast state updates to all routes for reload_request_id changes."""
        from .broadcasters import StateBroadcaster

        state_broadcaster = StateBroadcaster()
        for route_path, route_state in self.route_states.items():
            try:
                await state_broadcaster.broadcast_update(route_state.broadcast_topic)
            except Exception:
                logger.exception("Failed to broadcast reload update for route '%s'", route_path)

    def _setup_logging_filter(self) -> None:
        """Set up logging filter to exclude /healthz from access logs."""

        class HealthzFilter(logging.Filter):
            """Filter to exclude /healthz requests from access logs."""

            def filter(self, record: logging.LogRecord) -> bool:
                message = record.getMessage()
                return "/healthz" not in message

        access_logger = logging.getLogger("uvicorn.access")
        access_logger.addFilter(HealthzFilter())

    def _prepare_cache_dict(self) -> dict[str, list[Departure]]:
        """Convert shared departure cache to dict format for API poller.

        Returns:
            Dictionary mapping station_id to list of departures.
        """
        cache_dict: dict[str, list[Departure]] = {}
        station_ids: set[str] = self._shared_departure_cache.get_all_station_ids()
        for station_id in station_ids:
            cache_dict[station_id] = self._shared_departure_cache.get(station_id)
        return cache_dict

    async def _start_api_pollers(self, cache_dict: dict[str, list[Departure]]) -> None:
        """Start API pollers for all routes.

        Args:
            cache_dict: Dictionary mapping station_id to list of departures.
        """
        poller_count = 0
        for route_config in self.route_configs:
            route_path = route_config.path
            route_state = self.route_states[route_path]
            route_stop_configs = route_config.stop_configs
            interval = (
                route_config.refresh_interval_seconds
                if route_config.refresh_interval_seconds is not None
                else self.config.refresh_interval_seconds
            )
            stop_names = [stop.station_name for stop in route_stop_configs]
            logger.info(
                f"Starting API poller for route '{route_path}' "
                f"(stops: {', '.join(stop_names)}, interval: {interval}s)"
            )

            from mvg_departures.adapters.web.state.state import ApiPollerStartConfig

            start_config = ApiPollerStartConfig(
                grouping_service=self.grouping_service,
                stop_configs=route_stop_configs,
                config=self.config,
                shared_cache=cache_dict,
                refresh_interval_seconds=route_config.refresh_interval_seconds,
            )
            await route_state.start_api_poller(start_config)
            poller_count += 1

        logger.info(f"Started {poller_count} API poller(s) for {len(self.route_configs)} route(s)")

    def _initialize_route_reload_id(
        self, route_path: str, route_state: State, server_start_reload_id: int
    ) -> None:
        """Initialize reload_request_id for a single route."""
        try:
            if getattr(route_state.departures_state, "reload_request_id", 0) == 0:
                route_state.departures_state.reload_request_id = server_start_reload_id
                logger.info(
                    "Initialized reload_request_id=%s for route '%s' on server start",
                    server_start_reload_id,
                    route_path,
                )
        except Exception:
            logger.exception(
                "Failed to initialize reload_request_id for route '%s' on server start",
                route_path,
            )

    def _initialize_reload_request_ids(self) -> None:
        """Initialize reload_request_id for all routes on server start if enabled."""
        import time

        if not self.config.enable_server_start_reload:
            return

        server_start_reload_id = int(time.time())
        for route_path, route_state in self.route_states.items():
            self._initialize_route_reload_id(route_path, route_state, server_start_reload_id)

    def _configure_uvicorn_server(self, wrapped_app: Any) -> Any:
        """Configure and create uvicorn server instance."""
        import uvicorn

        config = uvicorn.Config(
            wrapped_app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
        return uvicorn.Server(config)

    async def _setup_application(self, app: Any) -> Any:
        """Set up application with all routes and middleware."""
        from mvg_departures.adapters.web.rate_limit_middleware import RateLimitMiddleware

        presence_tracker = get_presence_tracker()
        self._register_live_views(app, presence_tracker)
        self._setup_admin_endpoints(app, presence_tracker)

        static_file_server = StaticFileServer()
        static_file_server.register_routes(app)

        return RateLimitMiddleware(
            app,
            requests_per_minute=self.config.rate_limit_per_minute,
        )

    async def start(self) -> None:
        """Start the web server."""
        from pyview import PyView

        app = PyView()
        self._setup_favicon_and_root_template(app)

        wrapped_app = await self._setup_application(app)

        await self._start_departure_fetcher()
        cache_dict = self._prepare_cache_dict()
        await self._start_api_pollers(cache_dict)

        self._initialize_reload_request_ids()
        self._setup_logging_filter()

        self._server = self._configure_uvicorn_server(wrapped_app)
        await self._server.serve()

    def _collect_unique_station_ids(self) -> set[str]:
        """Collect all unique station IDs across all routes."""
        unique_station_ids: set[str] = set()
        for route_config in self.route_configs:
            for stop_config in route_config.stop_configs:
                unique_station_ids.add(stop_config.station_id)
        return unique_station_ids

    def _filter_and_mark_stale(self, departures: list[Departure]) -> list[Departure]:
        """Mark all departures as stale (not realtime) without filtering.

        Keep ALL departures including past ones - users can extrapolate from old data.
        Stale data is only purged when fresh API data arrives (which replaces cache).
        """
        # Keep ALL departures, just mark as stale
        return [replace(dep, is_realtime=False) for dep in departures]

    async def _fetch_single_station(self, station_id: str, fetch_limit: int) -> None:
        """Fetch departures for a single station."""
        departures = await self.departure_repository.get_departures(station_id, limit=fetch_limit)
        self._shared_departure_cache.set(station_id, departures)
        logger.debug(f"Fetched {len(departures)} raw departures for station {station_id}")

    def _handle_fetch_error(self, station_id: str, error: Exception) -> None:
        """Handle error when fetching departures for a station."""
        logger.error(
            f"Failed to fetch departures for station {station_id}: {error}",
            exc_info=True,
        )
        # Keep ALL stale cached data (even past departures) - mark as non-realtime
        # Users can extrapolate from old data. Stale data purges automatically when
        # fresh API data arrives (cache.set() with new data replaces stale data)
        cached = self._shared_departure_cache.get(station_id)
        if cached:
            stale_departures = self._filter_and_mark_stale(cached)
            self._shared_departure_cache.set(station_id, stale_departures)
            logger.info(
                f"Keeping {len(stale_departures)} stale departures for station {station_id} "
                f"until API recovers (marked as non-realtime)"
            )
        # If no cached data at all, leave cache empty

    async def _fetch_all_stations(self, unique_station_ids: set[str]) -> None:
        """Fetch raw departures for all unique stations."""
        fetch_limit = 50  # Same as in DepartureGroupingService
        sleep_ms = self.config.sleep_ms_between_calls
        station_list = list(unique_station_ids)

        for i, station_id in enumerate(station_list):
            try:
                await self._fetch_single_station(station_id, fetch_limit)
            except Exception as e:
                self._handle_fetch_error(station_id, e)

            # Add delay between calls (except after the last one)
            if sleep_ms > 0 and i < len(station_list) - 1:
                await asyncio.sleep(sleep_ms / 1000.0)

    def _create_fetch_loop(self, unique_station_ids: set[str]) -> asyncio.Task:
        """Create and return a task that periodically fetches departures."""

        async def _fetch_loop() -> None:
            try:
                while True:
                    await asyncio.sleep(self.config.refresh_interval_seconds)
                    await self._fetch_all_stations(unique_station_ids)
            except asyncio.CancelledError:
                logger.info("Shared fetcher cancelled")
                raise

        return asyncio.create_task(_fetch_loop())

    async def _start_departure_fetcher(self) -> None:
        """Start a shared fetcher that populates the cache with raw departures."""
        if self._departure_fetcher is not None:
            logger.warning("Departure fetcher already running")
            return

        unique_station_ids = self._collect_unique_station_ids()
        logger.info(
            f"Departure fetcher: {len(unique_station_ids)} unique station(s) across {len(self.route_configs)} route(s)"
        )

        # Create and start the fetcher
        self._departure_fetcher = DepartureFetcher(
            departure_repository=self.departure_repository,
            cache=self._shared_departure_cache,
            station_ids=unique_station_ids,
            config=self.config,
        )
        await self._departure_fetcher.start()

        # Do initial fetch immediately
        await self._fetch_all_stations(unique_station_ids)

        # Then fetch periodically
        self._shared_fetcher_task = self._create_fetch_loop(unique_station_ids)
        logger.info("Started shared departure fetcher")

    async def stop(self) -> None:
        """Stop the web server."""
        # Stop the departure fetcher
        if self._departure_fetcher is not None:
            await self._departure_fetcher.stop()
            self._departure_fetcher = None

        # Stop the API poller tasks for all routes
        for route_state in self.route_states.values():
            await route_state.stop_api_poller()

        if self._server:
            self._server.should_exit = True
