"""PyView web adapter for displaying departures."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import TYPE_CHECKING, Any

from mvg_departures.adapters.config import AppConfig
from mvg_departures.domain.models import RouteConfiguration
from mvg_departures.domain.ports import (
    DepartureGroupingService,
    DepartureRepository,
    DisplayAdapter,
)

from .presence import get_presence_tracker
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
        self._shared_departure_cache: dict[str, list[Departure]] = {}
        self._shared_fetcher_task: asyncio.Task | None = None

    async def display_departures(self, direction_groups: list[tuple[str, list[Departure]]]) -> None:
        """Display grouped departures (not used directly, handled by LiveView)."""
        # This is handled by the LiveView's periodic updates

    async def start(self) -> None:
        """Start the web server."""
        import uvicorn
        from pyview import PyView

        app = PyView()

        # Get the presence tracker instance (shared across all routes)
        presence_tracker = get_presence_tracker()

        # Create a LiveView for each route using the factory function
        for route_config in self.route_configs:
            route_path = route_config.path
            route_state = self.route_states[route_path]
            route_stop_configs = route_config.stop_configs

            logger.info(
                f"Registering route at path '{route_path}' with {len(route_stop_configs)} stops"
            )
            live_view_class = create_departures_live_view(
                route_state,
                self.grouping_service,
                route_stop_configs,
                self.config,
                presence_tracker,
            )
            app.add_live_view(route_path, live_view_class)
            logger.info(f"Successfully registered route at path '{route_path}'")

        # Serve pyview's client JavaScript and static assets
        from pathlib import Path

        from starlette.responses import FileResponse, Response
        from starlette.routing import Route

        async def static_app_js(_request: Any) -> Any:
            """Serve pyview's client JavaScript."""
            try:
                # Get pyview package path
                import pyview

                pyview_path = Path(pyview.__file__).parent
                client_js_path = pyview_path / "static" / "assets" / "app.js"

                if client_js_path.exists():
                    return FileResponse(str(client_js_path), media_type="application/javascript")
                # Fallback: try alternative path
                alt_path = pyview_path / "assets" / "js" / "app.js"
                if alt_path.exists():
                    return FileResponse(str(alt_path), media_type="application/javascript")
                logger.error(f"Could not find pyview client JS at {client_js_path} or {alt_path}")
                return Response(
                    content="// PyView client not found",
                    media_type="application/javascript",
                    status_code=404,
                )
            except Exception as e:
                logger.error(f"Error serving pyview client JS: {e}", exc_info=True)
                return Response(
                    content="// Error loading client",
                    media_type="application/javascript",
                    status_code=500,
                )

        async def static_github_icon(_request: Any) -> Any:
            """Serve GitHub octicon SVG."""
            try:
                # Try multiple possible locations for the static file
                # 1. Relative to working directory (Docker: /app/static/)
                # 2. Relative to source file (development: project_root/static/)
                possible_paths = [
                    Path.cwd() / "static" / "assets" / "github-mark.svg",
                    Path(__file__).parent.parent.parent.parent.parent
                    / "static"
                    / "assets"
                    / "github-mark.svg",
                ]

                for github_icon_path in possible_paths:
                    if github_icon_path.exists():
                        return FileResponse(str(github_icon_path), media_type="image/svg+xml")

                logger.error(
                    f"Could not find GitHub icon at any of: {[str(p) for p in possible_paths]}"
                )
                return Response(
                    content="<!-- GitHub icon not found -->",
                    media_type="image/svg+xml",
                    status_code=404,
                )
            except Exception as e:
                logger.error(f"Error serving GitHub icon: {e}", exc_info=True)
                return Response(
                    content="<!-- Error loading icon -->",
                    media_type="image/svg+xml",
                    status_code=500,
                )

        # Add route to serve pyview's client JavaScript (before wrapping with middleware)
        app.routes.append(Route("/static/assets/app.js", static_app_js))
        # Add route to serve GitHub icon
        app.routes.append(Route("/static/assets/github-mark.svg", static_github_icon))

        # Add rate limiting middleware
        # PyView is built on Starlette, so we wrap it with middleware
        from .rate_limit_middleware import RateLimitMiddleware

        # Wrap the app with rate limiting middleware
        wrapped_app = RateLimitMiddleware(
            app,
            requests_per_minute=self.config.rate_limit_per_minute,
        )

        # Start the shared fetcher that populates the cache with raw departures
        await self._start_shared_fetcher()

        # Start the API poller for each route immediately when server starts
        # Each route will process cached raw departures according to its own StopConfiguration
        for route_config in self.route_configs:
            route_path = route_config.path
            route_state = self.route_states[route_path]
            route_stop_configs = route_config.stop_configs

            await route_state.start_api_poller(
                self.grouping_service,
                route_stop_configs,
                self.config,
                shared_cache=self._shared_departure_cache,
            )

        config = uvicorn.Config(
            wrapped_app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)

        await self._server.serve()

    async def _start_shared_fetcher(self) -> None:
        """Start a shared fetcher that populates the cache with raw departures."""
        if self._shared_fetcher_task is not None and not self._shared_fetcher_task.done():
            logger.warning("Shared fetcher already running")
            return

        # Collect all unique station_ids across all routes
        unique_station_ids: set[str] = set()
        for route_config in self.route_configs:
            for stop_config in route_config.stop_configs:
                unique_station_ids.add(stop_config.station_id)

        logger.info(
            f"Shared fetcher: {len(unique_station_ids)} unique station(s) across {len(self.route_configs)} route(s)"
        )

        # Use the departure repository passed to the adapter
        departure_repo = self.departure_repository

        async def _fetch_all_stations() -> None:
            """Fetch raw departures for all unique stations."""
            fetch_limit = 50  # Same as in DepartureGroupingService
            sleep_ms = self.config.sleep_ms_between_calls
            station_list = list(unique_station_ids)

            for i, station_id in enumerate(station_list):
                try:
                    departures = await departure_repo.get_departures(station_id, limit=fetch_limit)
                    self._shared_departure_cache[station_id] = departures
                    logger.debug(
                        f"Fetched {len(departures)} raw departures for station {station_id}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to fetch departures for station {station_id}: {e}",
                        exc_info=True,
                    )
                    # Keep cached data if available, otherwise set empty list
                    if station_id not in self._shared_departure_cache:
                        self._shared_departure_cache[station_id] = []

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
        # Stop the shared fetcher
        if self._shared_fetcher_task and not self._shared_fetcher_task.done():
            self._shared_fetcher_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._shared_fetcher_task
            logger.info("Stopped shared departure fetcher")

        # Stop the API poller tasks for all routes
        for route_state in self.route_states.values():
            await route_state.stop_api_poller()

        if self._server:
            self._server.should_exit = True
