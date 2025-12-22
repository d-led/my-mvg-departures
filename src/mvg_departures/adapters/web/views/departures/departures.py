"""Departures LiveView for displaying MVG departures."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from pyview import LiveView, LiveViewSocket, is_connected
from pyview.events import InfoEvent
from pyview.template.live_template import LiveRender, LiveTemplate
from pyview.vendor import ibis
from pyview.vendor.ibis.loaders import FileReloader

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.broadcasters import PresenceBroadcaster
from mvg_departures.adapters.web.builders import DepartureGroupingCalculator
from mvg_departures.adapters.web.formatters import DepartureFormatter
from mvg_departures.adapters.web.state import DeparturesState, State
from mvg_departures.domain.contracts import (
    PresenceTrackerProtocol,  # noqa: TC001 - Runtime dependency: methods called at runtime
)
from mvg_departures.domain.models import StopConfiguration
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
    ) -> None:
        """Initialize the LiveView.

        Args:
            state_manager: State manager for this route.
            grouping_service: Service for grouping departures.
            stop_configs: List of stop configurations for this route.
            config: Application configuration.
            presence_tracker: Presence tracker for tracking user connections.
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
        self.formatter = DepartureFormatter(config)
        self.presence_broadcaster = PresenceBroadcaster()
        self.departure_grouping_calculator = DepartureGroupingCalculator(
            stop_configs, config, self.formatter
        )

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
        # Determine theme
        theme = self.config.theme.lower()
        if theme not in ("light", "dark", "auto"):
            theme = "auto"

        last_update = state.last_update

        # Build assigns - keep it simple like the original
        # Only ensure essential safety checks
        if not isinstance(template_data, dict):
            logger.warning(
                f"template_data is not a dict in _build_template_assigns, got {type(template_data)}"
            )
            template_data = {}

        # Ensure groups_with_departures and stops_without_departures exist
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

        last_update = state.last_update
        # Ensure all template variables are strings or numbers, never None
        # This prevents "undefined" or "None" from appearing in the rendered HTML
        return {
            **template_data,
            "theme": str(theme),
            "banner_color": str(self.config.banner_color or "#000000"),
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

    async def mount(self, socket: LiveViewSocket[DeparturesState], _session: dict) -> None:
        """Mount the LiveView and register socket for updates."""
        # Initialize context with current shared state
        route_path = self.state_manager.route_path

        # Create or get stable session ID for this connection
        # This persists across reconnections, unlike socket object ID
        if "_presence_session_id" not in _session:
            _session["_presence_session_id"] = str(uuid.uuid4())
            logger.debug(f"Created new presence session ID: {_session['_presence_session_id']}")

        # Register socket first so we can use it for cleanup
        self.state_manager.register_socket(socket)

        # Join presence tracking - always track, even if not connected yet
        # (socket will connect later and we'll update counts then)
        # Use get_or_create pattern: if already in presence, don't duplicate
        # Use session dict to get stable user ID (persists across reconnections)
        if not self.presence_tracker.is_user_tracked(socket, _session):
            user_id, local_count, total_count = self.presence_tracker.join_dashboard(
                route_path, socket, _session
            )
        else:
            # Already in presence, just ensure it's in the right dashboard
            local_count, total_count = self.presence_tracker.ensure_dashboard_membership(
                route_path, socket, _session
            )
            user_id = self.presence_tracker.get_user_id(socket, _session)
            logger.debug(f"User {user_id} already in presence, ensured dashboard membership")

        logger.info(
            f"Presence: user {user_id} joined dashboard {route_path}. "
            f"Local: {local_count}, Total: {total_count}"
        )

        # Update state with initial presence counts
        self.state_manager.departures_state.presence_local = local_count
        self.state_manager.departures_state.presence_total = total_count

        # Broadcast presence update using PresenceBroadcaster
        await self.presence_broadcaster.broadcast_join(
            route_path, user_id, local_count, total_count, socket
        )

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

        # Store session ID in socket for later use in unmount/disconnect
        # This allows us to use the same stable ID even if session dict is not available
        if not hasattr(socket, "_presence_session_id"):
            socket._presence_session_id = _session.get("_presence_session_id")

        # Socket already registered above for cleanup purposes

        # Subscribe to broadcast topic for receiving updates
        if is_connected(socket):
            try:
                await socket.subscribe(self.state_manager.broadcast_topic)
                logger.info(
                    f"Successfully subscribed socket to broadcast topic: {self.state_manager.broadcast_topic}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to subscribe to topic {self.state_manager.broadcast_topic}: {e}",
                    exc_info=True,
                )
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
        user_id, local_count, total_count = self.presence_tracker.leave_dashboard(
            route_path, socket, session
        )

        logger.info(
            f"Presence: user {user_id} left dashboard {route_path}. "
            f"Local: {local_count}, Total: {total_count}"
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
        user_id, local_count, total_count = self.presence_tracker.leave_dashboard(
            route_path, socket, session
        )

        logger.info(
            f"Presence disconnect: user {user_id} disconnected from dashboard {route_path}. "
            f"Local: {local_count}, Total: {total_count}"
        )

        # Update state with new presence counts
        self.state_manager.departures_state.presence_local = local_count
        self.state_manager.departures_state.presence_total = total_count

        # Broadcast presence update using PresenceBroadcaster
        await self.presence_broadcaster.broadcast_leave(
            route_path, user_id, local_count, total_count, socket
        )

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

    async def render(self, assigns: DeparturesState | dict, meta: Any) -> str:
        """Render the HTML template."""
        logger.debug(f"Render called at {datetime.now(UTC)}, assigns type: {type(assigns)}")

        try:
            # Get state from assigns (which is socket.context, a DeparturesState object)
            if isinstance(assigns, DeparturesState):
                state = assigns
            elif isinstance(assigns, dict):
                # Fallback: if it's a dict, try to get context or use shared state
                state = assigns.get("context", self.state_manager.departures_state)
                if not isinstance(state, DeparturesState):
                    state = self.state_manager.departures_state
            else:
                # Fallback to shared state
                state = self.state_manager.departures_state

            # Ensure direction_groups is never None - default to empty list
            # This prevents "Cannot read properties of undefined" errors
            direction_groups = state.direction_groups if state.direction_groups is not None else []

            # Ensure presence values are never None - default to 0
            # This prevents "undefined" from appearing in the template
            # CRITICAL: Do this BEFORE building template assigns to ensure template engine never sees None
            if not hasattr(state, "presence_local") or state.presence_local is None:
                state.presence_local = 0
            if not hasattr(state, "presence_total") or state.presence_total is None:
                state.presence_total = 0
            # Also ensure they're integers, not floats or strings
            state.presence_local = (
                int(state.presence_local) if isinstance(state.presence_local, (int, float)) else 0
            )
            state.presence_total = (
                int(state.presence_total) if isinstance(state.presence_total, (int, float)) else 0
            )

            # Prepare template data and build assigns
            # Ensure template_data is always a dict with safe defaults
            try:
                template_data = self.departure_grouping_calculator.calculate_display_data(
                    direction_groups
                )
                # Ensure template_data is a dict and has required keys
                if not isinstance(template_data, dict):
                    logger.warning(
                        f"template_data is not a dict, got {type(template_data)}, using empty dict"
                    )
                    template_data = {}
                # Ensure required keys exist with safe defaults
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
            except Exception as e:
                logger.error(f"Error calculating template data: {e}", exc_info=True)
                # Fallback to safe defaults
                template_data = {
                    "groups_with_departures": [],
                    "stops_without_departures": [],
                    "has_departures": False,
                }

            template_assigns = self._build_template_assigns(state, template_data)

            # Use pyview's LiveTemplate system with FileReloader
            # Set up template loader if not already configured
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            views_dir = os.path.dirname(
                current_file_dir
            )  # Go up one level from departures/ to views/
            if not hasattr(ibis, "loader") or not isinstance(ibis.loader, FileReloader):
                ibis.loader = FileReloader(views_dir)

            # Load template from file (relative to views directory)
            # FileReloader uses the template name as a key, and we access it via ibis.loader
            template_path = "departures/departures.html"
            # Read the template file content
            template_file = os.path.join(views_dir, template_path)
            with open(template_file, encoding="utf-8") as f:
                template_content = f.read()

            # Create ibis Template from content
            template = ibis.Template(template_content)
            live_template = LiveTemplate(template)
            # LiveRender returns an object with .text() method, not a string
            # Return it directly - pyview will call .text() on it
            return LiveRender(live_template, template_assigns, meta)  # type: ignore[no-any-return]
        except Exception as e:
            logger.error(f"Error rendering template: {e}", exc_info=True)
            # On error, we still need to return a LiveRender object, not a string
            # Create a minimal error template
            try:
                error_template = ibis.Template("<div>Error rendering template: {{ error }}</div>")
                error_live_template = LiveTemplate(error_template)
                error_assigns = {"error": str(e)}
                return LiveRender(error_live_template, error_assigns, meta)  # type: ignore[no-any-return]
            except Exception:
                # Last resort: return a simple LiveRender with minimal content
                minimal_template = ibis.Template("<div>Error: Failed to render</div>")
                minimal_live_template = LiveTemplate(minimal_template)
                return LiveRender(minimal_live_template, {}, meta)  # type: ignore[no-any-return]


def create_departures_live_view(
    state_manager: State,
    grouping_service: DepartureGroupingService,
    stop_configs: list[StopConfiguration],
    config: AppConfig,
    presence_tracker: PresenceTrackerProtocol,
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

    Returns:
        A configured DeparturesLiveView class that can be registered with PyView.
    """
    # Capture values in closure to avoid late binding issues
    captured_state = state_manager
    captured_stop_configs = stop_configs
    captured_grouping_service = grouping_service
    captured_config = config
    captured_presence_tracker = presence_tracker

    class ConfiguredDeparturesLiveView(DeparturesLiveView):
        """Configured LiveView for a specific route."""

        def __init__(self) -> None:
            super().__init__(
                captured_state,
                captured_grouping_service,
                captured_stop_configs,
                captured_config,
                captured_presence_tracker,
            )

    return ConfiguredDeparturesLiveView
