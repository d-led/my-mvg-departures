"""PyView web adapter for displaying departures."""

from __future__ import annotations

import asyncio
import logging
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

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from mvg_departures.domain.models import Departure


class PyViewWebAdapter(DisplayAdapter):
    """PyView-based web adapter for displaying departures."""

    def __init__(
        self,
        grouping_service: DepartureGroupingService,
        route_configs: list[RouteConfiguration],
        config: AppConfig,
        departure_repository: DepartureRepository,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize the web adapter.

        Args:
            grouping_service: Service for grouping departures.
            route_configs: List of route configurations, each with a path and stops.
            config: Application configuration.
            departure_repository: Repository for fetching raw departures (used for shared caching).
            session: Optional aiohttp session.
        """
        # Runtime usage - these assignments ensure Ruff detects runtime dependency
        if not isinstance(config, AppConfig):
            raise TypeError("config must be an AppConfig instance")
        if not isinstance(route_configs, list) or not all(
            isinstance(rc, RouteConfiguration) for rc in route_configs
        ):
            raise TypeError("route_configs must be a list of RouteConfiguration instances")
        # Protocols can't be checked with isinstance, verify required methods exist
        if not hasattr(grouping_service, "group_departures") or not callable(
            getattr(grouping_service, "group_departures", None)
        ):
            raise TypeError("grouping_service must implement DepartureGroupingService protocol")
        if not hasattr(departure_repository, "get_departures") or not callable(
            getattr(departure_repository, "get_departures", None)
        ):
            raise TypeError("departure_repository must implement DepartureRepository protocol")

        self.grouping_service = grouping_service
        self.route_configs = route_configs
        self.config = config
        self.departure_repository = departure_repository
        self.session = session
        self._update_task: asyncio.Task | None = None
        self._server: Any | None = None
        # Create a state manager for each route
        self.route_states: dict[str, State] = {
            route_config.path: State(
                route_path=route_config.path,
                max_sessions_per_browser=self.config.max_sessions_per_browser,
            )
            for route_config in route_configs
        }
        # Shared cache for raw departures by station_id (to avoid duplicate API calls)
        # Each route will process this cached data according to its own StopConfiguration
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

    def _register_live_views(self, app: Any, presence_tracker: Any) -> None:
        """Register LiveViews for all routes.

        Args:
            app: The PyView application instance.
            presence_tracker: The presence tracker instance.
        """
        for route_config in self.route_configs:
            route_path = route_config.path
            route_state = self.route_states[route_path]
            route_stop_configs = route_config.stop_configs
            route_title = route_config.title
            route_theme = route_config.theme
            fill_vertical_space = route_config.fill_vertical_space
            font_scaling_factor_when_filling = route_config.font_scaling_factor_when_filling
            random_header_colors = route_config.random_header_colors
            header_background_brightness = route_config.header_background_brightness
            random_color_salt = route_config.random_color_salt

            # Generate route-specific favicon if route has custom title
            if route_title:
                self._add_route_favicon(app, route_path, route_title)

            logger.info(
                f"Registering route at path '{route_path}' with {len(route_stop_configs)} stops"
                + (f" and title '{route_title}'" if route_title else "")
                + (f" (fill_vertical_space={fill_vertical_space})" if fill_vertical_space else "")
            )
            live_view_class = create_departures_live_view(
                route_state,
                self.grouping_service,
                route_stop_configs,
                self.config,
                presence_tracker,
                route_title,
                route_theme,
                fill_vertical_space,
                font_scaling_factor_when_filling,
                random_header_colors,
                header_background_brightness,
                random_color_salt,
            )
            app.add_live_view(route_path, live_view_class)
            logger.info(f"Successfully registered route at path '{route_path}'")

    def _setup_admin_endpoints(self, app: Any, presence_tracker: Any) -> None:
        """Set up admin maintenance endpoints.

        Args:
            app: The PyView application instance.
            presence_tracker: The presence tracker instance.
        """
        from starlette.responses import JSONResponse, Response
        from starlette.routing import Route

        async def reset_connections(request: Any) -> Any:
            """Reset server-side connection and presence state."""
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

        app.routes.append(Route("/admin/reset-connections", reset_connections, methods=["POST"]))

        # Health check endpoint
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

            await route_state.start_api_poller(
                self.grouping_service,
                route_stop_configs,
                self.config,
                shared_cache=cache_dict,
                refresh_interval_seconds=route_config.refresh_interval_seconds,
            )
            poller_count += 1

        logger.info(f"Started {poller_count} API poller(s) for {len(self.route_configs)} route(s)")

    def _initialize_reload_request_ids(self) -> None:
        """Initialize reload_request_id for all routes on server start if enabled."""
        import time

        if not self.config.enable_server_start_reload:
            return

        server_start_reload_id = int(time.time())
        for route_path, route_state in self.route_states.items():
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

    async def start(self) -> None:
        """Start the web server."""
        import uvicorn
        from pyview import PyView

        from mvg_departures.adapters.web.rate_limit_middleware import RateLimitMiddleware

        app = PyView()

        # Set up favicon and root template
        self._setup_favicon_and_root_template(app)

        # Get the presence tracker instance (shared across all routes)
        presence_tracker = get_presence_tracker()

        # Register LiveViews for all routes
        self._register_live_views(app, presence_tracker)

        # Set up admin endpoints and health check
        self._setup_admin_endpoints(app, presence_tracker)

        # Register static file routes
        static_file_server = StaticFileServer()
        static_file_server.register_routes(app)

        # Wrap the app with rate limiting middleware
        wrapped_app = RateLimitMiddleware(
            app,
            requests_per_minute=self.config.rate_limit_per_minute,
        )

        # Start the shared fetcher that populates the cache with raw departures
        await self._start_departure_fetcher()

        # Start API pollers for all routes
        cache_dict = self._prepare_cache_dict()
        await self._start_api_pollers(cache_dict)

        # Initialize reload request IDs if enabled
        self._initialize_reload_request_ids()

        # Set up logging filter
        self._setup_logging_filter()

        # Configure and start uvicorn server
        config = uvicorn.Config(
            wrapped_app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)

        await self._server.serve()

    async def _start_departure_fetcher(self) -> None:
        """Start a shared fetcher that populates the cache with raw departures."""
        if self._departure_fetcher is not None:
            logger.warning("Departure fetcher already running")
            return

        # Collect all unique station_ids across all routes
        unique_station_ids: set[str] = set()
        for route_config in self.route_configs:
            for stop_config in route_config.stop_configs:
                unique_station_ids.add(stop_config.station_id)

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
        # Use the departure repository directly (already available)
        departure_repo = self.departure_repository

        async def _fetch_all_stations() -> None:
            """Fetch raw departures for all unique stations."""
            fetch_limit = 50  # Same as in DepartureGroupingService
            sleep_ms = self.config.sleep_ms_between_calls
            station_list = list(unique_station_ids)

            for i, station_id in enumerate(station_list):
                try:
                    departures = await departure_repo.get_departures(station_id, limit=fetch_limit)
                    self._shared_departure_cache.set(station_id, departures)
                    logger.debug(
                        f"Fetched {len(departures)} raw departures for station {station_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to fetch departures for station {station_id}: {e}",
                        exc_info=True,
                    )
                    # Keep cached data if available, otherwise set empty list
                    if not self._shared_departure_cache.get(station_id):
                        self._shared_departure_cache.set(station_id, [])

                # Add delay between calls (except after the last one)
                if sleep_ms > 0 and i < len(station_list) - 1:
                    await asyncio.sleep(sleep_ms / 1000.0)

        # Do initial fetch immediately
        await _fetch_all_stations()

        # Then fetch periodically
        async def _fetch_loop() -> None:
            try:
                while True:
                    await asyncio.sleep(self.config.refresh_interval_seconds)
                    await _fetch_all_stations()
            except asyncio.CancelledError:
                logger.info("Shared fetcher cancelled")
                raise

        self._shared_fetcher_task = asyncio.create_task(_fetch_loop())
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
