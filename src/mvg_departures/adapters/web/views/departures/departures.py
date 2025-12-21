"""Departures LiveView for displaying MVG departures."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any

from pyview import LiveView, LiveViewSocket, is_connected
from pyview.events import InfoEvent
from pyview.template.live_template import LiveRender, LiveTemplate
from pyview.vendor import ibis
from pyview.vendor.ibis.loaders import FileReloader

from mvg_departures.adapters.config import AppConfig
from mvg_departures.adapters.web.broadcasters import PresenceBroadcaster
from mvg_departures.adapters.web.formatters import DepartureFormatter
from mvg_departures.adapters.web.state import DeparturesState, State
from mvg_departures.domain.contracts import (
    PresenceTrackerProtocol,  # noqa: TC001 - Runtime dependency: methods called at runtime
)
from mvg_departures.domain.models import Departure, StopConfiguration
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

    async def mount(self, socket: LiveViewSocket[DeparturesState], _session: dict) -> None:
        """Mount the LiveView and register socket for updates."""
        # Initialize context with current shared state
        route_path = self.state_manager.route_path

        # Create or get stable session ID for this connection
        # This persists across reconnections, unlike socket object ID
        import uuid

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
            presence_local=self.state_manager.departures_state.presence_local,
            presence_total=self.state_manager.departures_state.presence_total,
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
                # Parse payload - might be dict or JSON string
                presence_data: dict[str, Any] | None = None
                if isinstance(payload, dict):
                    presence_data = payload
                elif isinstance(payload, str):
                    # Try to parse as JSON
                    try:
                        presence_data = json.loads(payload)
                    except (json.JSONDecodeError, TypeError):
                        logger.debug(f"Could not parse presence payload as JSON: {payload}")
                        return

                if presence_data:
                    # Update presence counts from payload
                    # For dashboard topic, update both local and total
                    if topic != "presence:global" and "local_count" in presence_data:
                        socket.context.presence_local = presence_data["local_count"]
                    # For both dashboard and global topics, update total
                    if "total_count" in presence_data:
                        socket.context.presence_total = presence_data["total_count"]
                    logger.debug(
                        f"Updated presence counts: local={socket.context.presence_local}, "
                        f"total={socket.context.presence_total}"
                    )
                return

            # Handle regular update messages
            if payload == "update":
                # Update the existing context object's fields directly
                # Pyview detects field changes and automatically triggers re-render
                socket.context.direction_groups = (
                    self.state_manager.departures_state.direction_groups
                )
                socket.context.last_update = self.state_manager.departures_state.last_update
                socket.context.api_status = self.state_manager.departures_state.api_status
                # Also update presence counts from state
                socket.context.presence_local = self.state_manager.departures_state.presence_local
                socket.context.presence_total = self.state_manager.departures_state.presence_total
                logger.info(
                    f"Updated context from pubsub message at {datetime.now(UTC)}, groups: {len(self.state_manager.departures_state.direction_groups)}"
                )
                return

            logger.debug(f"Received InfoEvent from topic '{topic}' with payload: {payload}")
            return

        # Handle direct string payload (legacy format)
        if isinstance(event, str):
            payload = event
            if payload == "update":
                # Update the existing context object's fields directly
                socket.context.direction_groups = (
                    self.state_manager.departures_state.direction_groups
                )
                socket.context.last_update = self.state_manager.departures_state.last_update
                socket.context.api_status = self.state_manager.departures_state.api_status
                # Also update presence counts from state
                socket.context.presence_local = self.state_manager.departures_state.presence_local
                socket.context.presence_total = self.state_manager.departures_state.presence_total
                logger.info(
                    f"Updated context from pubsub message at {datetime.now(UTC)}, groups: {len(self.state_manager.departures_state.direction_groups)}"
                )
                return

            logger.debug(f"Received direct payload: {payload}")
            return

        # Unknown event type - log error and return
        logger.error(
            f"Unexpected event type in handle_info: {type(event)}, "
            f"expected str or InfoEvent, got: {event}"
        )

    async def render(self, assigns: DeparturesState | dict, meta: Any) -> str:
        """Render the HTML template."""
        logger.debug(f"Render called at {datetime.now(UTC)}, assigns type: {type(assigns)}")

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

        direction_groups = state.direction_groups
        last_update = state.last_update
        api_status = state.api_status

        # Determine theme
        theme = self.config.theme.lower()
        if theme not in ("light", "dark", "auto"):
            theme = "auto"

        # Get banner color from config
        banner_color = self.config.banner_color

        # Prepare template data
        template_data = self._prepare_template_data(direction_groups)

        # Merge template data with config values for template
        template_assigns = {
            **template_data,
            "theme": theme,
            "banner_color": banner_color,
            "font_size_route_number": self.config.font_size_route_number,
            "font_size_destination": self.config.font_size_destination,
            "font_size_platform": self.config.font_size_platform,
            "font_size_time": self.config.font_size_time,
            "font_size_no_departures": self.config.font_size_no_departures,
            "font_size_direction_header": self.config.font_size_direction_header,
            "font_size_pagination_indicator": self.config.font_size_pagination_indicator,
            "font_size_countdown_text": self.config.font_size_countdown_text,
            "font_size_status_header": self.config.font_size_status_header,
            "font_size_delay_amount": self.config.font_size_delay_amount,
            "font_size_stop_header": self.config.font_size_stop_header,
            "pagination_enabled": str(self.config.pagination_enabled).lower(),
            "departures_per_page": str(self.config.departures_per_page),
            "page_rotation_seconds": str(self.config.page_rotation_seconds),
            "refresh_interval_seconds": str(self.config.refresh_interval_seconds),
            "time_format_toggle_seconds": str(self.config.time_format_toggle_seconds),
            "api_status": api_status,
            "last_update_timestamp": (
                str(int(last_update.timestamp() * 1000)) if last_update is not None else "0"
            ),
            "update_time": self.formatter.format_update_time(last_update),
            "presence_local": state.presence_local,
            "presence_total": state.presence_total,
        }

        # Use pyview's LiveTemplate system with FileReloader
        # Set up template loader if not already configured
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        views_dir = os.path.dirname(current_file_dir)  # Go up one level from departures/ to views/
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
        return LiveRender(live_template, template_assigns, meta)  # type: ignore[no-any-return]

    def _prepare_template_data(
        self, direction_groups: list[tuple[str, str, list[Departure]]]
    ) -> dict[str, Any]:
        """Prepare data structure for template rendering."""
        stop_configs = self.stop_configs

        # Separate groups with departures from stops that have no departures
        groups_with_departures: list[dict[str, Any]] = []
        stops_with_departures: set[str] = set()
        current_stop: str | None = None

        for stop_name, direction_name, departures in direction_groups:
            if departures:
                direction_clean = direction_name.lstrip("->")
                combined_header = f"{stop_name} → {direction_clean}"

                # Check if this is a new stop
                is_new_stop = stop_name != current_stop
                if is_new_stop:
                    current_stop = stop_name

                # Prepare departures for this group
                sorted_departures = sorted(departures, key=lambda d: d.time)
                departure_data = []
                for departure in sorted_departures:
                    time_str = self.formatter.format_departure_time(departure)
                    time_str_relative = self.formatter.format_departure_time_relative(departure)
                    time_str_absolute = self.formatter.format_departure_time_absolute(departure)

                    # Format platform
                    platform_display = (
                        str(departure.platform) if departure.platform is not None else None
                    )
                    platform_aria = f", Platform {platform_display}" if platform_display else ""

                    # Format delay
                    delay_display = None
                    delay_aria = ""
                    has_delay = departure.delay_seconds is not None and departure.delay_seconds > 60
                    if has_delay and departure.delay_seconds is not None:
                        delay_minutes = departure.delay_seconds // 60
                        delay_display = f'<span class="delay-amount" aria-hidden="true">{delay_minutes}m 😞</span>'
                        delay_aria = f", delayed by {delay_minutes} minutes"

                    # Build ARIA label
                    status_parts = []
                    if departure.is_cancelled:
                        status_parts.append("cancelled")
                    if departure.is_realtime:
                        status_parts.append("real-time")
                    status_text = ", ".join(status_parts) if status_parts else "scheduled"

                    aria_label = (
                        f"Line {departure.line} to {departure.destination}"
                        f"{platform_aria}"
                        f", departing in {time_str}"
                        f"{delay_aria}"
                        f", {status_text}"
                    )

                    departure_data.append(
                        {
                            "line": departure.line,
                            "destination": departure.destination,
                            "platform": platform_display,
                            "time_str": time_str,
                            "time_str_relative": time_str_relative,
                            "time_str_absolute": time_str_absolute,
                            "cancelled": departure.is_cancelled,
                            "has_delay": has_delay,
                            "delay_display": delay_display,
                            "is_realtime": departure.is_realtime,
                            "aria_label": aria_label,
                        }
                    )

                groups_with_departures.append(
                    {
                        "stop_name": stop_name,
                        "header": combined_header,
                        "departures": departure_data,
                        "is_new_stop": is_new_stop,
                    }
                )
                stops_with_departures.add(stop_name)

        # Mark first header and last group
        if groups_with_departures:
            groups_with_departures[0]["is_first_header"] = True
            groups_with_departures[0]["is_first_group"] = True
            groups_with_departures[-1]["is_last_group"] = True
            for i in range(1, len(groups_with_departures) - 1):
                groups_with_departures[i]["is_first_header"] = False
                groups_with_departures[i]["is_first_group"] = False
                groups_with_departures[i]["is_last_group"] = False
            if len(groups_with_departures) > 1:
                groups_with_departures[-1]["is_first_header"] = False
                groups_with_departures[-1]["is_first_group"] = False

        # Find stops without departures
        configured_stops = {stop_config.station_name for stop_config in stop_configs}
        stops_without_departures = sorted(configured_stops - stops_with_departures)

        return {
            "groups_with_departures": groups_with_departures,
            "stops_without_departures": stops_without_departures,
            "has_departures": len(groups_with_departures) > 0,
            "font_size_no_departures": self.config.font_size_no_departures_available,
        }


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
