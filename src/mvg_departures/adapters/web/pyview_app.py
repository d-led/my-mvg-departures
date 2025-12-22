"""PyView web adapter for displaying departures."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import asyncio

from mvg_departures.adapters.config import AppConfig
from mvg_departures.domain.models import RouteConfiguration
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
            route_config.path: State(route_path=route_config.path) for route_config in route_configs
        }
        # Shared cache for raw departures by station_id (to avoid duplicate API calls)
        # Each route will process this cached data according to its own StopConfiguration
        self._shared_departure_cache = SharedDepartureCache()
        self._departure_fetcher: DepartureFetcher | None = None

    async def display_departures(self, direction_groups: list[tuple[str, list[Departure]]]) -> None:
        """Display grouped departures (not used directly, handled by LiveView)."""
        # This is handled by the LiveView's periodic updates

    async def start(self) -> None:
        """Start the web server."""
        import uvicorn
        from markupsafe import Markup
        from pyview import PyView
        from pyview.playground.favicon import generate_favicon_svg
        from pyview.template import defaultRootTemplate
        from starlette.responses import Response
        from starlette.routing import Route

        app = PyView()

        # Generate default favicon SVG from global title using banner color from config
        default_favicon_svg = generate_favicon_svg(
            self.config.title,
            bg_color=self.config.banner_color or "#087BC4",  # Use banner color from config
            text_color="#FFFFFF",  # White text for contrast
        )

        # Add default favicon route
        async def default_favicon_route(_request: Any) -> Response:
            return Response(content=default_favicon_svg, media_type="image/svg+xml")

        app.routes.append(Route("/favicon.svg", default_favicon_route, methods=["GET"]))

        # Add default favicon link to CSS/head content
        favicon_link = Markup('<link rel="icon" href="/favicon.svg" type="image/svg+xml">')

        # Set rootTemplate with default title (LiveView template data will override via JavaScript)
        app.rootTemplate = defaultRootTemplate(
            title=self.config.title,  # Default title for main page
            title_suffix="",  # Empty suffix to prevent " | LiveView" from appearing
            css=favicon_link,  # Add default favicon link to head
        )

        # Get the presence tracker instance (shared across all routes)
        presence_tracker = get_presence_tracker()

        # Create a LiveView for each route using the factory function
        for route_config in self.route_configs:
            route_path = route_config.path
            route_state = self.route_states[route_path]
            route_stop_configs = route_config.stop_configs
            route_title = route_config.title

            # Generate route-specific favicon if route has custom title
            if route_title:
                route_favicon_svg = generate_favicon_svg(
                    route_title,
                    bg_color=self.config.banner_color or "#087BC4",
                    text_color="#FFFFFF",
                )

                # Create favicon route handler (capture SVG in closure)
                def create_favicon_handler(svg_content: str) -> Any:
                    async def favicon_handler(_request: Any) -> Response:
                        return Response(content=svg_content, media_type="image/svg+xml")

                    return favicon_handler

                # Normalize path for favicon route
                favicon_path = route_path.rstrip("/") + "/favicon.svg"

                route_favicon_handler = create_favicon_handler(route_favicon_svg)
                app.routes.append(Route(favicon_path, route_favicon_handler, methods=["GET"]))
                logger.info(f"Added route-specific favicon at {favicon_path} for '{route_title}'")

            logger.info(
                f"Registering route at path '{route_path}' with {len(route_stop_configs)} stops"
                + (f" and title '{route_title}'" if route_title else "")
            )
            live_view_class = create_departures_live_view(
                route_state,
                self.grouping_service,
                route_stop_configs,
                self.config,
                presence_tracker,
                route_title,
            )
            app.add_live_view(route_path, live_view_class)
            logger.info(f"Successfully registered route at path '{route_path}'")

        # Register static file routes
        static_file_server = StaticFileServer()
        static_file_server.register_routes(app)

        # Add rate limiting middleware
        # PyView is built on Starlette, so we wrap it with middleware
        from .rate_limit_middleware import RateLimitMiddleware

        # Wrap the app with rate limiting middleware
        wrapped_app = RateLimitMiddleware(
            app,
            requests_per_minute=self.config.rate_limit_per_minute,
        )

        # Start the shared fetcher that populates the cache with raw departures
        await self._start_departure_fetcher()

        # Start the API poller for each route immediately when server starts
        # Each route will process cached raw departures according to its own StopConfiguration
        # Convert cache to dict for API poller (it expects a dict)
        # TODO: Refactor ApiPoller to use DepartureCacheProtocol instead
        cache_dict: dict[str, list[Departure]] = {}
        station_ids: set[str] = self._shared_departure_cache.get_all_station_ids()
        for station_id in station_ids:
            cache_dict[station_id] = self._shared_departure_cache.get(station_id)

        for route_config in self.route_configs:
            route_path = route_config.path
            route_state = self.route_states[route_path]
            route_stop_configs = route_config.stop_configs

            await route_state.start_api_poller(
                self.grouping_service,
                route_stop_configs,
                self.config,
                shared_cache=cache_dict,
            )

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
