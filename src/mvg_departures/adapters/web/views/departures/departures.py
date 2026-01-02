"""Departures LiveView for displaying MVG departures."""

from __future__ import annotations

import hashlib
import logging
import os
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pyview import LiveView, LiveViewSocket, is_connected
from pyview.events import InfoEvent
from pyview.template.live_template import LiveRender, LiveTemplate
from pyview.vendor import ibis
from pyview.vendor.ibis.loaders import FileReloader

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.broadcasters import PresenceBroadcaster
from mvg_departures.adapters.web.builders import DepartureGroupingCalculator
from mvg_departures.adapters.web.client_info import get_client_info_from_socket
from mvg_departures.adapters.web.formatters import DepartureFormatter
from mvg_departures.adapters.web.state import DeparturesState, State
from mvg_departures.domain.contracts import (
    PresenceTrackerProtocol,  # noqa: TC001 - Runtime dependency: methods called at runtime
)
from mvg_departures.domain.models import (
    DirectionGroupWithMetadata,
    StopConfiguration,
)
from mvg_departures.domain.ports import (
    DepartureGroupingService,  # noqa: TC001 - Runtime dependency: methods called at runtime
)

logger = logging.getLogger(__name__)


class DeparturesLiveView(LiveView[DeparturesState]):
    """LiveView for displaying MVG departures."""

    def __init__(
        self,
        state_manager: State,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        presence_tracker: PresenceTrackerProtocol,
        route_title: str | None = None,
        route_theme: str | None = None,
        fill_vertical_space: bool = False,
        font_scaling_factor_when_filling: float = 1.0,
        random_header_colors: bool = False,
        header_background_brightness: float = 0.7,
        random_color_salt: int = 0,
    ) -> None:
        """Initialize the LiveView.

        Args:
            state_manager: State manager for this route.
            grouping_service: Service for grouping departures.
            stop_configs: List of stop configurations for this route.
            config: Application configuration.
            presence_tracker: Presence tracker for tracking user connections.
            route_title: Optional route-specific title (overrides config title).
            route_theme: Optional route-specific theme (overrides config theme).
            fill_vertical_space: Enable dynamic font sizing to fill viewport.
            font_scaling_factor_when_filling: Scale factor for all fonts when fill_vertical_space is enabled.
            random_header_colors: Enable hash-based pastel colors for headers.
            header_background_brightness: Brightness adjustment for random header colors (0.0-1.0).
            random_color_salt: Salt value for hash-based color generation (default 0).
        """
        super().__init__()
        # Runtime usage - these assignments ensure Ruff detects runtime dependency
        if not isinstance(config, AppConfig):
            raise TypeError("config must be an AppConfig instance")
        if not isinstance(stop_configs, list) or not all(
            isinstance(sc, StopConfiguration) for sc in stop_configs
        ):
            raise TypeError("stop_configs must be a list of StopConfiguration instances")
        # Protocols can't be checked with isinstance, but we verify required methods exist
        # Access methods directly to make runtime dependency explicit for Ruff
        _ = presence_tracker.join_dashboard  # Runtime usage - ensures Ruff detects dependency
        _ = grouping_service.group_departures  # Runtime usage - ensures Ruff detects dependency
        if not callable(presence_tracker.join_dashboard):
            raise TypeError("presence_tracker must implement PresenceTrackerProtocol")
        if not callable(grouping_service.group_departures):
            raise TypeError("grouping_service must implement DepartureGroupingService protocol")

        self.state_manager = state_manager
        self.grouping_service = grouping_service
        self.stop_configs = stop_configs
        self.config = config
        self.presence_tracker = presence_tracker
        self.route_title = route_title
        self.route_theme = route_theme
        self.fill_vertical_space = fill_vertical_space
        self.font_scaling_factor_when_filling = font_scaling_factor_when_filling
        self.random_header_colors = random_header_colors
        self.header_background_brightness = header_background_brightness
        self.random_color_salt = random_color_salt
        self.formatter = DepartureFormatter(config)
        self.presence_broadcaster = PresenceBroadcaster()
        self.departure_grouping_calculator = DepartureGroupingCalculator(
            stop_configs,
            config,
            self.formatter,
            random_header_colors,
            header_background_brightness,
            random_color_salt,
        )
        # Generate static version for cache busting
        self._static_version = self._get_static_version()

    def _update_presence_from_event(
        self, topic: str, payload: dict[str, Any], socket: LiveViewSocket[DeparturesState]
    ) -> None:
        """Update socket context with presence counts from event.

        Args:
            topic: The pub/sub topic name.
            payload: The event payload dictionary (pyview passes dicts directly).
            socket: The socket connection.
        """
        # For dashboard topic, update both local and total
        if topic != "presence:global" and "local_count" in payload:
            socket.context.presence_local = payload["local_count"]
        # For both dashboard and global topics, update total
        if "total_count" in payload:
            socket.context.presence_total = payload["total_count"]
        logger.debug(
            f"Updated presence counts: local={socket.context.presence_local}, "
            f"total={socket.context.presence_total}"
        )

    def _update_context_from_state(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Update socket context from shared state manager.

        Args:
            socket: The socket connection.
        """
        socket.context.direction_groups = self.state_manager.departures_state.direction_groups
        socket.context.last_update = self.state_manager.departures_state.last_update
        socket.context.api_status = self.state_manager.departures_state.api_status
        socket.context.presence_local = (
            self.state_manager.departures_state.presence_local
            if self.state_manager.departures_state.presence_local is not None
            else 0
        )
        socket.context.presence_total = (
            self.state_manager.departures_state.presence_total
            if self.state_manager.departures_state.presence_total is not None
            else 0
        )
        logger.info(
            f"Updated context from pubsub message at {datetime.now(UTC)}, "
            f"groups: {len(self.state_manager.departures_state.direction_groups)}"
        )

    def _normalize_theme(self) -> str:
        """Normalize theme value.

        Returns:
            Normalized theme string (light, dark, or auto).
        """
        theme = self.route_theme if self.route_theme else self.config.theme
        theme = theme.lower()
        if theme not in ("light", "dark", "auto"):
            theme = "auto"
        return theme

    def _validate_template_data(self, template_data: dict[str, Any]) -> dict[str, Any]:
        """Validate and ensure template data has required keys.

        Args:
            template_data: Template data dictionary.

        Returns:
            Validated template data dictionary.
        """
        if not isinstance(template_data, dict):
            logger.warning(
                f"template_data is not a dict in _build_template_assigns, got {type(template_data)}"
            )
            template_data = {}

        if (
            "groups_with_departures" not in template_data
            or template_data["groups_with_departures"] is None
        ):
            template_data["groups_with_departures"] = []
        if (
            "stops_without_departures" not in template_data
            or template_data["stops_without_departures"] is None
        ):
            template_data["stops_without_departures"] = []
        if "has_departures" not in template_data:
            template_data["has_departures"] = False

        return template_data

    def _build_font_size_assigns(self) -> dict[str, str]:
        """Build font size assigns from config.

        Returns:
            Dictionary with font size template variables.
        """
        return {
            "font_size_route_number": str(self.config.font_size_route_number or "1.5rem"),
            "font_size_destination": str(self.config.font_size_destination or "1.2rem"),
            "font_size_platform": str(self.config.font_size_platform or "1rem"),
            "font_size_time": str(self.config.font_size_time or "1.5rem"),
            "font_size_no_departures": str(
                self.config.font_size_no_departures_available or "1.2rem"
            ),
            "font_size_direction_header": str(self.config.font_size_direction_header or "1.3rem"),
            "font_size_pagination_indicator": str(
                self.config.font_size_pagination_indicator or "0.9rem"
            ),
            "font_size_countdown_text": str(self.config.font_size_countdown_text or "0.9rem"),
            "font_size_status_header": str(self.config.font_size_status_header or "1rem"),
            "font_size_delay_amount": str(self.config.font_size_delay_amount or "0.9rem"),
            "font_size_stop_header": str(self.config.font_size_stop_header or "1.1rem"),
        }

    def _build_config_assigns(self) -> dict[str, str]:
        """Build configuration assigns from config.

        Returns:
            Dictionary with configuration template variables.
        """
        return {
            "pagination_enabled": (
                str(self.config.pagination_enabled).lower()
                if self.config.pagination_enabled is not None
                else "false"
            ),
            "departures_per_page": (
                str(self.config.departures_per_page)
                if self.config.departures_per_page is not None
                else "5"
            ),
            "page_rotation_seconds": (
                str(self.config.page_rotation_seconds)
                if self.config.page_rotation_seconds is not None
                else "10"
            ),
            "refresh_interval_seconds": (
                str(self.config.refresh_interval_seconds)
                if self.config.refresh_interval_seconds is not None
                else "20"
            ),
            "time_format_toggle_seconds": (
                str(self.config.time_format_toggle_seconds)
                if self.config.time_format_toggle_seconds is not None
                else "0"
            ),
        }

    def _build_state_assigns(self, state: DeparturesState) -> dict[str, str]:
        """Build state-related assigns from state.

        Args:
            state: Current departures state.

        Returns:
            Dictionary with state template variables.
        """
        last_update = state.last_update
        return {
            "reload_request_id": str(getattr(state, "reload_request_id", 0) or 0),
            "api_status": str(state.api_status or "unknown"),
            "last_update_timestamp": (
                str(int(last_update.timestamp() * 1000)) if last_update is not None else "0"
            ),
            "update_time": str(self.formatter.format_update_time(last_update) or "Never"),
            "presence_local": str(
                int(state.presence_local)
                if state.presence_local is not None
                and isinstance(state.presence_local, (int, float))
                else 0
            ),
            "presence_total": str(
                int(state.presence_total)
                if state.presence_total is not None
                and isinstance(state.presence_total, (int, float))
                else 0
            ),
        }

    def _build_route_assigns(self) -> dict[str, str]:
        """Build route-specific assigns.

        Returns:
            Dictionary with route template variables.
        """
        page_title = self.route_title or self.config.title or "My MVG Departures"
        favicon_path = "/favicon.svg"
        if self.route_title:
            route_path = self.state_manager.route_path.rstrip("/")
            favicon_path = f"{route_path}/favicon.svg"

        return {
            "title": str(page_title),
            "favicon_path": str(favicon_path),
            "fill_vertical_space": (
                str(self.fill_vertical_space).lower()
                if self.fill_vertical_space is not None
                else "false"
            ),
            "font_scaling_factor_when_filling": str(self.font_scaling_factor_when_filling),
        }

    def _build_template_assigns(
        self, state: DeparturesState, template_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Build template assigns dictionary from state and template data.

        Args:
            state: The current departures state.
            template_data: Pre-calculated template data from DepartureGroupingCalculator.

        Returns:
            Dictionary of template variables for rendering.
        """
        theme = self._normalize_theme()
        template_data = self._validate_template_data(template_data)

        return {
            **template_data,
            "theme": str(theme),
            "banner_color": str(self.config.banner_color or "#000000"),
            **self._build_font_size_assigns(),
            **self._build_config_assigns(),
            **self._build_state_assigns(state),
            **self._build_route_assigns(),
            "static_version": self._static_version,
        }

    def _ensure_presence_session_id(self, _session: dict) -> str:
        """Create or get stable session ID for this connection.

        Args:
            _session: Session dictionary.

        Returns:
            Presence session ID.
        """
        if "_presence_session_id" not in _session:
            _session["_presence_session_id"] = str(uuid.uuid4())
            logger.debug(f"Created new presence session ID: {_session['_presence_session_id']}")
        session_id = _session["_presence_session_id"]
        return str(session_id) if isinstance(session_id, str) else str(uuid.uuid4())

    async def _handle_presence_tracking(
        self, route_path: str, socket: LiveViewSocket[DeparturesState], _session: dict
    ) -> None:
        """Handle presence tracking for connected socket.

        Args:
            route_path: Route path.
            socket: LiveView socket.
            _session: Session dictionary.
        """
        if not self.presence_tracker.is_user_tracked(socket, _session):
            presence_result = self.presence_tracker.join_dashboard(route_path, socket, _session)
            user_id = presence_result.user_id
            local_count = presence_result.local_count
            total_count = presence_result.total_count
        else:
            presence_counts = self.presence_tracker.ensure_dashboard_membership(
                route_path, socket, _session
            )
            user_id = self.presence_tracker.get_user_id(socket, _session)
            local_count = presence_counts.local_count
            total_count = presence_counts.total_count
            logger.debug(f"User {user_id} already in presence, ensured dashboard membership")

        client_info = get_client_info_from_socket(socket)
        logger.info(
            (
                "Presence: user %s joined dashboard %s from ip=%s, agent=%s, "
                "browser_id=%s. Local: %s, Total: %s"
            ),
            user_id,
            route_path,
            client_info.ip,
            client_info.user_agent,
            client_info.browser_id,
            local_count,
            total_count,
        )

        self.state_manager.departures_state.presence_local = local_count
        self.state_manager.departures_state.presence_total = total_count

        await self.presence_broadcaster.broadcast_join(
            route_path, user_id, local_count, total_count, socket
        )

    def _set_socket_context(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Set socket context with current state.

        Args:
            socket: LiveView socket.
        """
        socket.context = DeparturesState(
            direction_groups=self.state_manager.departures_state.direction_groups,
            last_update=self.state_manager.departures_state.last_update,
            api_status=self.state_manager.departures_state.api_status,
            presence_local=(
                self.state_manager.departures_state.presence_local
                if self.state_manager.departures_state.presence_local is not None
                else 0
            ),
            presence_total=(
                self.state_manager.departures_state.presence_total
                if self.state_manager.departures_state.presence_total is not None
                else 0
            ),
        )

    async def _subscribe_and_track_presence(
        self, route_path: str, socket: LiveViewSocket[DeparturesState], _session: dict
    ) -> None:
        """Subscribe to broadcast topic and track presence if needed.

        Args:
            route_path: Route path.
            socket: LiveView socket.
            _session: Session dictionary.
        """
        try:
            await socket.subscribe(self.state_manager.broadcast_topic)
            logger.info(
                f"Successfully subscribed socket to broadcast topic: {self.state_manager.broadcast_topic}"
            )

            if not self.presence_tracker.is_user_tracked(socket, _session):
                presence_result = self.presence_tracker.join_dashboard(route_path, socket, _session)
                user_id = presence_result.user_id
                local_count = presence_result.local_count
                total_count = presence_result.total_count
                client_info = get_client_info_from_socket(socket)
                logger.info(
                    (
                        "Presence: user %s joined dashboard %s (connected after mount) "
                        "from ip=%s, agent=%s, browser_id=%s. Local: %s, Total: %s"
                    ),
                    user_id,
                    route_path,
                    client_info.ip,
                    client_info.user_agent,
                    client_info.browser_id,
                    local_count,
                    total_count,
                )
                self.state_manager.departures_state.presence_local = local_count
                self.state_manager.departures_state.presence_total = total_count
                await self.presence_broadcaster.broadcast_join(
                    route_path, user_id, local_count, total_count, socket
                )
        except Exception as e:
            logger.error(
                f"Failed to subscribe to topic {self.state_manager.broadcast_topic}: {e}",
                exc_info=True,
            )

    async def mount(self, socket: LiveViewSocket[DeparturesState], _session: dict) -> None:
        """Mount the LiveView and register socket for updates."""
        route_path = self.state_manager.route_path

        presence_session_id = self._ensure_presence_session_id(_session)
        if not self.state_manager.register_socket(socket, presence_session_id):
            return

        if is_connected(socket):
            await self._handle_presence_tracking(route_path, socket, _session)
        else:
            logger.debug(
                "Socket not connected during mount - skipping presence tracking. "
                "User will be tracked when socket connects."
            )

        self._set_socket_context(socket)

        if not hasattr(socket, "_presence_session_id"):
            socket._presence_session_id = _session.get("_presence_session_id")

        if is_connected(socket):
            await self._subscribe_and_track_presence(route_path, socket, _session)
        else:
            logger.warning("Socket not connected during mount, will receive updates when connected")

    async def unmount(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Unmount the LiveView and unregister socket."""
        route_path = self.state_manager.route_path

        # Get session ID from socket if stored during mount
        # Create a minimal session dict with the stored ID
        session = None
        if hasattr(socket, "_presence_session_id") and socket._presence_session_id:
            session = {"_presence_session_id": socket._presence_session_id}

        # Leave presence tracking - always remove, even if not connected
        presence_result = self.presence_tracker.leave_dashboard(route_path, socket, session)
        user_id = presence_result.user_id
        local_count = presence_result.local_count
        total_count = presence_result.total_count

        client_info = get_client_info_from_socket(socket)
        logger.info(
            (
                "Presence: user %s left dashboard %s from ip=%s, agent=%s, "
                "browser_id=%s. Local: %s, Total: %s"
            ),
            user_id,
            route_path,
            client_info.ip,
            client_info.user_agent,
            client_info.browser_id,
            local_count,
            total_count,
        )

        # Update state with new presence counts
        self.state_manager.departures_state.presence_local = local_count
        self.state_manager.departures_state.presence_total = total_count

        # Broadcast presence update using PresenceBroadcaster
        await self.presence_broadcaster.broadcast_leave(
            route_path, user_id, local_count, total_count, socket
        )

        self.state_manager.unregister_socket(socket)

    async def disconnect(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Handle socket disconnection - ensure presence is cleaned up."""
        route_path = self.state_manager.route_path

        # Get session ID from socket if stored during mount
        # Create a minimal session dict with the stored ID
        session = None
        if hasattr(socket, "_presence_session_id") and socket._presence_session_id:
            session = {"_presence_session_id": socket._presence_session_id}

        # Always remove from presence tracking on disconnect
        presence_result = self.presence_tracker.leave_dashboard(route_path, socket, session)
        user_id = presence_result.user_id
        local_count = presence_result.local_count
        total_count = presence_result.total_count

        client_info = get_client_info_from_socket(socket)
        logger.info(
            (
                "Presence disconnect: user %s disconnected from dashboard %s from ip=%s, "
                "agent=%s, browser_id=%s. Local: %s, Total: %s"
            ),
            user_id,
            route_path,
            client_info.ip,
            client_info.user_agent,
            client_info.browser_id,
            local_count,
            total_count,
        )

        # Update state with new presence counts
        self.state_manager.departures_state.presence_local = local_count
        self.state_manager.departures_state.presence_total = total_count

        # Broadcast presence update using PresenceBroadcaster
        await self.presence_broadcaster.broadcast_leave(
            route_path, user_id, local_count, total_count, socket
        )

        # Mirror unmount behaviour: ensure socket is always unregistered on disconnect.
        # Discarding from the set keeps this idempotent if unmount already ran.
        self.state_manager.unregister_socket(socket)

    async def handle_info(
        self, event: str | InfoEvent, socket: LiveViewSocket[DeparturesState]
    ) -> None:
        """Handle update messages from pubsub."""

        # Handle InfoEvent for presence updates
        if isinstance(event, InfoEvent):
            topic = event.name
            payload = event.payload

            # Handle presence events
            if topic.startswith("presence:"):
                if isinstance(payload, dict):
                    self._update_presence_from_event(topic, payload, socket)
                else:
                    logger.warning(f"Unexpected presence payload type: {type(payload)}")
                return

            # Handle regular update messages
            if payload == "update":
                self._update_context_from_state(socket)
                return

            logger.debug(f"Received InfoEvent from topic '{topic}' with payload: {payload}")
            return

        # Handle direct string payload (legacy format)
        if isinstance(event, str):
            if event == "update":
                self._update_context_from_state(socket)
                return

            logger.debug(f"Received direct payload: {event}")
            return

        # Unknown event type - log error and return
        logger.error(
            f"Unexpected event type in handle_info: {type(event)}, "
            f"expected str or InfoEvent, got: {event}"
        )

    def _get_static_version(self) -> str:
        """Generate or retrieve static asset version for cache busting.

        Returns:
            Version string to append to static asset URLs.
        """
        # First, check if explicitly set via environment variable
        if self.config.static_version:
            return self.config.static_version

        # Try to generate from file modification times (for development)
        # This ensures changes are picked up during development
        try:
            static_js_path = Path.cwd() / "static" / "js" / "app.js"
            if not static_js_path.exists():
                # Try alternative path
                static_js_path = (
                    Path(__file__).parent.parent.parent.parent.parent / "static" / "js" / "app.js"
                )

            if static_js_path.exists():
                # Use file modification time as version
                mtime = static_js_path.stat().st_mtime
                return str(int(mtime))
        except Exception:
            pass

        # Fallback: use a hash of the current time (changes on each server restart)
        # This ensures cache is busted on redeployment
        return hashlib.md5(str(datetime.now(UTC).timestamp()).encode()).hexdigest()[:8]

    def _extract_state_from_assigns(self, assigns: DeparturesState | dict) -> DeparturesState:
        """Extract DeparturesState from assigns.

        Args:
            assigns: Assigns object (DeparturesState or dict).

        Returns:
            DeparturesState object.
        """
        if isinstance(assigns, DeparturesState):
            return assigns

        if isinstance(assigns, dict):
            state = assigns.get("context", self.state_manager.departures_state)
            if isinstance(state, DeparturesState):
                return state

        return self.state_manager.departures_state

    def _normalize_presence_values(self, state: DeparturesState) -> None:
        """Normalize presence values to ensure they're integers.

        Args:
            state: DeparturesState to normalize.
        """
        if not hasattr(state, "presence_local") or state.presence_local is None:
            state.presence_local = 0
        if not hasattr(state, "presence_total") or state.presence_total is None:
            state.presence_total = 0

        state.presence_local = (
            int(state.presence_local) if isinstance(state.presence_local, (int, float)) else 0
        )
        state.presence_total = (
            int(state.presence_total) if isinstance(state.presence_total, (int, float)) else 0
        )

    def _calculate_template_data(
        self, direction_groups: list[DirectionGroupWithMetadata]
    ) -> dict[str, Any]:
        """Calculate and validate template data.

        Args:
            direction_groups: List of direction groups.

        Returns:
            Dictionary with template data.
        """
        try:
            template_data = self.departure_grouping_calculator.calculate_display_data(
                direction_groups
            )
            if not isinstance(template_data, dict):
                logger.warning(
                    f"template_data is not a dict, got {type(template_data)}, using empty dict"
                )
                template_data = {}

            if (
                "groups_with_departures" not in template_data
                or template_data["groups_with_departures"] is None
            ):
                template_data["groups_with_departures"] = []
            if (
                "stops_without_departures" not in template_data
                or template_data["stops_without_departures"] is None
            ):
                template_data["stops_without_departures"] = []
            if "has_departures" not in template_data:
                template_data["has_departures"] = False

            return template_data
        except Exception as e:
            logger.error(f"Error calculating template data: {e}", exc_info=True)
            return {
                "groups_with_departures": [],
                "stops_without_departures": [],
                "has_departures": False,
            }

    def _load_template(self) -> LiveTemplate:
        """Load and prepare template for rendering.

        Returns:
            LiveTemplate object.
        """
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        views_dir = os.path.dirname(current_file_dir)

        if not hasattr(ibis, "loader") or not isinstance(ibis.loader, FileReloader):
            ibis.loader = FileReloader(views_dir)

        template_path = "departures/departures.html"
        template_file = os.path.join(views_dir, template_path)
        with open(template_file, encoding="utf-8") as f:
            template_content = f.read()

        template = ibis.Template(template_content)
        return LiveTemplate(template)

    def _create_error_template(self, error: Exception, meta: Any) -> LiveRender:
        """Create error template for rendering failures.

        Args:
            error: Exception that occurred.
            meta: Template metadata.

        Returns:
            LiveRender object with error template.
        """
        try:
            error_template = ibis.Template("<div>Error rendering template: {{ error }}</div>")
            error_live_template = LiveTemplate(error_template)
            error_assigns = {"error": str(error)}
            return LiveRender(error_live_template, error_assigns, meta)
        except Exception:
            minimal_template = ibis.Template("<div>Error: Failed to render</div>")
            minimal_live_template = LiveTemplate(minimal_template)
            return LiveRender(minimal_live_template, {}, meta)

    async def render(self, assigns: DeparturesState | dict, meta: Any) -> str:
        """Render the HTML template."""
        logger.debug(f"Render called at {datetime.now(UTC)}, assigns type: {type(assigns)}")

        try:
            state = self._extract_state_from_assigns(assigns)
            direction_groups = state.direction_groups if state.direction_groups is not None else []

            self._normalize_presence_values(state)
            template_data = self._calculate_template_data(direction_groups)
            template_assigns = self._build_template_assigns(state, template_data)

            live_template = self._load_template()
            return LiveRender(live_template, template_assigns, meta)  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Error rendering template: {e}", exc_info=True)
            return self._create_error_template(e, meta)  # type: ignore[no-any-return]


def create_departures_live_view(
    state_manager: State,
    grouping_service: DepartureGroupingService,
    stop_configs: list[StopConfiguration],
    config: AppConfig,
    presence_tracker: PresenceTrackerProtocol,
    route_title: str | None = None,
    route_theme: str | None = None,
    fill_vertical_space: bool = False,
    font_scaling_factor_when_filling: float = 1.0,
    random_header_colors: bool = False,
    header_background_brightness: float = 0.7,
    random_color_salt: int = 0,
) -> type[DeparturesLiveView]:
    """Create a configured DeparturesLiveView class for a specific route.

    This factory function creates a LiveView class that is configured with
    route-specific parameters. PyView's add_live_view expects a class, not
    an instance, so we return a configured class.

    Args:
        state_manager: State manager for this route.
        grouping_service: Service for grouping departures.
        stop_configs: List of stop configurations for this route.
        config: Application configuration.
        presence_tracker: Presence tracker for tracking user connections.
        route_title: Optional route-specific title (overrides config title).
        route_theme: Optional route-specific theme (overrides config theme).
        fill_vertical_space: Enable dynamic font sizing to fill viewport.
        font_scaling_factor_when_filling: Scale factor for all fonts when fill_vertical_space is enabled.
        random_header_colors: Enable hash-based pastel colors for headers.
        header_background_brightness: Brightness adjustment for random header colors (0.0-1.0).
        random_color_salt: Salt value for hash-based color generation (default 0).

    Returns:
        A configured DeparturesLiveView class that can be registered with PyView.
    """
    # Capture values in closure to avoid late binding issues
    captured_state = state_manager
    captured_stop_configs = stop_configs
    captured_grouping_service = grouping_service
    captured_config = config
    captured_presence_tracker = presence_tracker
    captured_route_title = route_title
    captured_route_theme = route_theme
    captured_fill_vertical_space = fill_vertical_space
    captured_font_scaling_factor_when_filling = font_scaling_factor_when_filling
    captured_random_header_colors = random_header_colors
    captured_header_background_brightness = header_background_brightness
    captured_random_color_salt = random_color_salt

    class ConfiguredDeparturesLiveView(DeparturesLiveView):
        """Configured LiveView for a specific route."""

        def __init__(self) -> None:
            super().__init__(
                captured_state,
                captured_grouping_service,
                captured_stop_configs,
                captured_config,
                captured_presence_tracker,
                captured_route_title,
                captured_route_theme,
                captured_fill_vertical_space,
                captured_font_scaling_factor_when_filling,
                captured_random_header_colors,
                captured_header_background_brightness,
                captured_random_color_salt,
            )

    return ConfiguredDeparturesLiveView
