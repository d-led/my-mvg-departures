"""PyView web adapter for displaying departures."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pyview import ConnectedLiveViewSocket, LiveView, LiveViewSocket, is_connected
from pyview.events import InfoEvent

logger = logging.getLogger(__name__)

from mvg_departures.adapters.config import AppConfig
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import Departure, StopConfiguration
from mvg_departures.domain.ports import DisplayAdapter

if TYPE_CHECKING:
    from aiohttp import ClientSession


@dataclass
class DeparturesState:
    """State for the departures LiveView."""

    direction_groups: list[tuple[str, str, list[Departure]]] = field(default_factory=list)
    last_update: datetime | None = None
    api_status: str = "unknown"


# Shared state and connected sockets for broadcasting
_departures_state = DeparturesState()
_connected_sockets: set[LiveViewSocket[DeparturesState]] = set()
_api_poller_task: asyncio.Task | None = None
# Cache for stale departures per stop (station_name -> list of direction groups)
_cached_departures: dict[str, list[tuple[str, list[Departure]]]] = {}


async def _api_poller(
    grouping_service: DepartureGroupingService,
    stop_configs: list[StopConfiguration],
    config: AppConfig,
) -> None:
    """Independent API poller that updates shared state and broadcasts to connected sockets.

    This runs as a separate background task, completely independent of LiveView instances.
    It polls the API periodically and broadcasts updates to all connected sockets.
    """
    from pyview.live_socket import pub_sub_hub
    from pyview.vendor.flet.pubsub import PubSub

    # Create PubSub instance once and reuse it
    pubsub = PubSub(pub_sub_hub, _departures_broadcast_topic)

    logger.info("API poller started (independent of client connections)")

    def extract_error_details(error: Exception) -> tuple[int | None, str]:
        """Extract HTTP status code and error reason from exception."""
        import re

        error_str = str(error)
        # Try to extract HTTP status code from error message
        # Format: "Bad API call: Got response (502) from ..."
        status_match = re.search(r"\((\d+)\)", error_str)
        status_code = int(status_match.group(1)) if status_match else None

        # Determine error reason
        if status_code == 429:
            reason = "Rate limit exceeded"
        elif status_code == 502:
            reason = "Bad gateway (server error)"
        elif status_code == 503:
            reason = "Service unavailable"
        elif status_code == 504:
            reason = "Gateway timeout"
        elif status_code is not None:
            reason = f"HTTP {status_code}"
        else:
            reason = "Unknown error"

        return status_code, reason

    async def _fetch_and_broadcast() -> None:
        """Fetch departures and broadcast update to all connected sockets."""
        # Fetch departures from API - handle errors per stop
        all_groups: list[tuple[str, str, list[Departure]]] = []
        has_errors = False

        for stop_config in stop_configs:
            try:
                groups = await grouping_service.get_grouped_departures(stop_config)
                # Convert to format with station_name
                stop_groups: list[tuple[str, list[Departure]]] = []
                for direction_name, departures in groups:
                    stop_groups.append((direction_name, departures))
                    all_groups.append((stop_config.station_name, direction_name, departures))
                # Cache successful fetch
                _cached_departures[stop_config.station_name] = stop_groups
                logger.debug(f"Successfully fetched departures for {stop_config.station_name}")
            except Exception as e:
                status_code, reason = extract_error_details(e)
                logger.error(
                    f"API poller failed to fetch departures for {stop_config.station_name}: "
                    f"{reason} (status: {status_code}, error: {e})"
                )
                has_errors = True
                if status_code == 429:
                    logger.warning(
                        f"Rate limit (429) detected for {stop_config.station_name} - "
                        "consider adding delays between API calls"
                    )

                # Use cached data if available, mark as stale
                if stop_config.station_name in _cached_departures:
                    cached_groups = _cached_departures[stop_config.station_name]
                    logger.info(
                        f"Using cached departures for {stop_config.station_name} "
                        f"({len(cached_groups)} direction groups) due to {reason}"
                    )
                    # Mark departures as stale (non-realtime)
                    from dataclasses import replace

                    for direction_name, cached_departures in cached_groups:
                        stale_departures = [
                            replace(dep, is_realtime=False) for dep in cached_departures
                        ]
                        all_groups.append(
                            (stop_config.station_name, direction_name, stale_departures)
                        )
                # Continue with other stops even if one fails

        # Update shared state (even if some stops failed, use what we got)
        _departures_state.direction_groups = all_groups
        _departures_state.last_update = datetime.now()
        _departures_state.api_status = "error" if has_errors else "success"

        logger.debug(
            f"API poller updated departures at {datetime.now()}, "
            f"groups: {len(all_groups)}, errors: {has_errors}"
        )

        # Broadcast update via pubsub to all subscribed sockets
        try:
            await pubsub.send_all_on_topic_async(_departures_broadcast_topic, "update")
            logger.info(f"Broadcasted update via pubsub to topic: {_departures_broadcast_topic}")
        except Exception as pubsub_err:
            logger.error(f"Failed to broadcast via pubsub: {pubsub_err}", exc_info=True)

    # Do initial update immediately
    await _fetch_and_broadcast()

    # Then poll periodically
    try:
        while True:
            await asyncio.sleep(config.refresh_interval_seconds)
            await _fetch_and_broadcast()
    except asyncio.CancelledError:
        logger.info("API poller cancelled")
        raise


_departures_broadcast_topic: str = "departures:updates"  # Keep for handle_info compatibility


class DeparturesLiveView(LiveView[DeparturesState]):
    """LiveView for displaying MVG departures."""

    def __init__(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
    ) -> None:
        """Initialize the LiveView."""
        super().__init__()
        self.grouping_service = grouping_service
        self.stop_configs = stop_configs
        self.config = config

    async def mount(self, socket: LiveViewSocket[DeparturesState], _session: dict) -> None:
        """Mount the LiveView and register socket for updates."""
        # Initialize context with current shared state
        socket.context = DeparturesState(
            direction_groups=_departures_state.direction_groups,
            last_update=_departures_state.last_update,
            api_status=_departures_state.api_status,
        )

        # Register socket for broadcasts
        _connected_sockets.add(socket)
        logger.info(f"Registered socket, total connected: {len(_connected_sockets)}")

        # Subscribe to broadcast topic for receiving updates
        if is_connected(socket):
            try:
                await socket.subscribe(_departures_broadcast_topic)
                logger.info(
                    f"Successfully subscribed socket to broadcast topic: {_departures_broadcast_topic}"
                )
            except Exception as e:
                logger.error(
                    f"Failed to subscribe to topic {_departures_broadcast_topic}: {e}",
                    exc_info=True,
                )
        else:
            logger.warning("Socket not connected during mount, will receive updates when connected")

    async def unmount(self, socket: LiveViewSocket[DeparturesState]) -> None:
        """Unmount the LiveView and unregister socket."""
        _connected_sockets.discard(socket)
        logger.info(f"Unregistered socket, total connected: {len(_connected_sockets)}")

    async def handle_info(
        self, event: str | InfoEvent, socket: LiveViewSocket[DeparturesState]
    ) -> None:
        """Handle update messages from pubsub."""

        # Extract payload from event - type-safe extraction
        payload: str
        if isinstance(event, InfoEvent):
            payload = event.payload
            topic = event.name
            logger.debug(f"Received InfoEvent from topic '{topic}' with payload: {payload}")
        elif isinstance(event, str):
            # Direct payload (string)
            payload = event
            logger.debug(f"Received direct payload: {payload}")
        else:
            # Unknown event type - log error and return
            logger.error(
                f"Unexpected event type in handle_info: {type(event)}, "
                f"expected str or InfoEvent, got: {event}"
            )
            return

        # When we receive an update message, read from shared state
        # (We don't serialize Departure objects in pubsub, just read from shared state)
        if payload == "update":
            # Update the existing context object's fields directly
            # Pyview detects field changes and automatically triggers re-render
            socket.context.direction_groups = _departures_state.direction_groups
            socket.context.last_update = _departures_state.last_update
            socket.context.api_status = _departures_state.api_status
            logger.info(
                f"Updated context from pubsub message at {datetime.now()}, groups: {len(_departures_state.direction_groups)}"
            )
        else:
            logger.debug(f"Ignoring pubsub message with payload: {payload}")

    async def render(self, assigns: DeparturesState | dict, meta: Any) -> str:
        """Render the HTML template."""
        logger.debug(f"Render called at {datetime.now()}, assigns type: {type(assigns)}")

        # Get state from assigns (which is socket.context, a DeparturesState object)
        if isinstance(assigns, DeparturesState):
            state = assigns
        elif isinstance(assigns, dict):
            # Fallback: if it's a dict, try to get context or use shared state
            state = assigns.get("context", _departures_state)
            if not isinstance(state, DeparturesState):
                state = _departures_state
        else:
            # Fallback to shared state
            state = _departures_state

        direction_groups = state.direction_groups
        last_update = state.last_update
        api_status = state.api_status

        # Determine theme
        theme = self.config.theme.lower()
        if theme not in ("light", "dark", "auto"):
            theme = "auto"

        # Get banner color from config
        banner_color = self.config.banner_color

        # Return only the content that goes inside the body
        # PyView's root template will wrap this in the full HTML structure
        html_content = (
            """
    <!-- Minimal DaisyUI for theme support only -->
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        // Apply theme based on configuration
        const themeConfig = '"""
            + theme
            + """';
        if (themeConfig === 'light') {
            document.documentElement.setAttribute('data-theme', 'light');
            localStorage.theme = 'light';
        } else if (themeConfig === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
            localStorage.theme = 'dark';
        } else {
            // Auto: follow system preference
            if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
                document.documentElement.setAttribute('data-theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-theme', 'light');
            }
        }
    </script>
    <style>
        * {
            box-sizing: border-box;
        }
        html, body {
            height: 100vh;
            width: 100vw;
            margin: 0;
            padding: 0;
            overflow: hidden;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.2;
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100vw;
            max-width: 100vw;
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        [data-theme="light"] body {
            background-color: #ffffff;
            color: #111827;
        }
        [data-theme="dark"] body {
            background-color: #1d232a;
            color: #f9fafb;
        }
        .departure-row {
            display: flex;
            align-items: center;
            padding: 0.75rem 0 0.75rem 0.75rem;
            border-bottom: 1px solid rgba(0, 0, 0, 0.08);
            min-height: 4.5rem;
            width: 100%;
            box-sizing: border-box;
        }
        .departure-row:nth-child(even) {
            background-color: rgba(0, 0, 0, 0.02);
        }
        [data-theme="light"] .departure-row {
            border-bottom-color: rgba(0, 0, 0, 0.08);
        }
        [data-theme="light"] .departure-row:nth-child(even) {
            background-color: rgba(0, 0, 0, 0.02);
        }
        [data-theme="dark"] .departure-row {
            border-bottom-color: rgba(255, 255, 255, 0.08);
            background-color: #1d232a;
        }
        [data-theme="dark"] .departure-row:nth-child(even) {
            background-color: rgba(255, 255, 255, 0.03);
        }
        .route-number {
            flex: 0 0 5rem;
            font-weight: 700;
            font-size: """
            + self.config.font_size_route_number
            + """;
            text-align: left;
            padding: 0 0.75rem 0 0;
            white-space: nowrap;
        }
        [data-theme="light"] .route-number {
            color: #1f2937;
        }
        [data-theme="dark"] .route-number {
            color: #f3f4f6;
        }
        .destination {
            flex: 1 1 auto;
            overflow-x: auto;
            overflow-y: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            padding: 0 0.75rem;
            min-width: 0;
            font-size: """
            + self.config.font_size_destination
            + """;
            font-weight: 500;
            text-align: left;
            scrollbar-width: none;
        }
        .destination::-webkit-scrollbar {
            display: none;
        }
        [data-theme="light"] .destination {
            color: #374151;
        }
        [data-theme="dark"] .destination {
            color: #e5e7eb;
        }
        .platform {
            flex: 0 0 auto;
            font-size: """
            + self.config.font_size_platform
            + """;
            font-weight: 400;
            text-align: left;
            padding: 0 0.75rem;
            white-space: nowrap;
            min-width: fit-content;
            color: #6b7280;
        }
        [data-theme="light"] .platform {
            color: #6b7280;
        }
        [data-theme="dark"] .platform {
            color: #9ca3af;
        }
        .time {
            flex: 0 0 auto;
            text-align: right;
            font-weight: 600;
            font-size: """
            + self.config.font_size_time
            + """;
            padding: 0 0.75rem 0 0.75rem;
            margin-right: 0;
            white-space: nowrap;
            min-width: fit-content;
        }
        [data-theme="light"] .time {
            color: #111827;
        }
        [data-theme="dark"] .time {
            color: #f9fafb;
        }
        .no-departures {
            width: 100%;
            text-align: center;
            font-size: """
            + self.config.font_size_no_departures
            + """;
            color: #9ca3af;
            padding: 2rem 0;
            font-style: italic;
        }
        [data-theme="light"] .no-departures {
            color: #6b7280;
        }
        [data-theme="dark"] .no-departures {
            color: #6b7280;
        }
        .direction-header {
            font-size: """
            + self.config.font_size_direction_header
            + """;
            font-weight: 700;
            margin: 0.5rem 0 0.25rem 0;
            padding: 0 0.75rem 0.25rem 0.75rem;
            border-bottom: 2px solid rgba(0, 0, 0, 0.2);
            opacity: 0.85;
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 0.5rem;
        }
        h2.direction-header {
            margin: 0.5rem 0 0.25rem 0;
            padding: 0 0.75rem 0.25rem 0.75rem;
        }
        .direction-header-text {
            flex: 1;
            min-width: 0;
        }
        .direction-header-status-group {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            flex-shrink: 0;
            margin-right: 0.25rem;
            font-size: inherit;
        }
        .direction-header-time {
            flex-shrink: 0;
            margin-left: auto; /* Push to right */
            white-space: nowrap;
            display: flex;
            align-items: center; /* Vertical alignment */
            line-height: 1; /* Match header text line height */
        }
        [data-theme="light"] .direction-header {
            background-color: """
            + banner_color
            + """;
            color: #ffffff;
            border-bottom-color: rgba(255, 255, 255, 0.25);
        }
        [data-theme="dark"] .direction-header {
            color: #f3f4f6;
            border-bottom-color: rgba(255, 255, 255, 0.15);
        }
        .route-group-header {
            height: 0.15em;
            line-height: 0.15em;
            margin: 0.15rem 0.5rem;
            border-top: 1px solid rgba(0, 0, 0, 0.08);
            opacity: 0.4;
        }
        [data-theme="light"] .route-group-header {
            border-top-color: rgba(0, 0, 0, 0.1);
        }
        [data-theme="dark"] .route-group-header {
            border-top-color: rgba(255, 255, 255, 0.08);
        }
        .pagination-container {
            position: relative;
            overflow: hidden;
            min-height: 3rem;
        }
        .pagination-page {
            display: none;
            animation: fadeIn 0.5s ease-in;
        }
        .pagination-page.active {
            display: block;
        }
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }
        .pagination-indicator {
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            padding: 0.6rem 0.8rem;
            border-radius: 0.5rem;
            font-size: """
            + self.config.font_size_pagination_indicator
            + """;
            font-weight: 600;
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .countdown-text {
            font-size: """
            + self.config.font_size_countdown_text
            + """;
            font-weight: 500;
            min-width: 2.5rem;
            text-align: center;
        }
        [data-theme="light"] .pagination-indicator {
            background: rgba(0, 0, 0, 0.75);
            color: #ffffff;
        }
        [data-theme="dark"] .pagination-indicator {
            background: rgba(255, 255, 255, 0.2);
            color: #ffffff;
        }
        .countdown-circle {
            width: 1.4rem;
            height: 1.4rem;
            border-radius: 50%;
            border: 2px solid currentColor;
            position: relative;
            display: inline-block;
        }
        .countdown-circle svg {
            width: 100%;
            height: 100%;
            transform: rotate(-90deg);
        }
        .countdown-circle circle {
            fill: none;
            stroke: currentColor;
            stroke-width: 2.5;
            stroke-dasharray: 31.416;
            stroke-dashoffset: 0;
            transition: stroke-dashoffset 0.1s linear;
        }
        .direction-group-container {
            position: relative;
            overflow: visible;
        }
        .stop-header {
            font-size: """
            + self.config.font_size_stop_header
            + """;
            font-weight: 700;
            margin: 0.5rem 0.5rem 0.25rem 0.5rem;
            padding: 0;
            opacity: 0.95;
        }
        [data-theme="light"] .stop-header {
            color: #111827;
        }
        [data-theme="dark"] .stop-header {
            color: #f9fafb;
        }
        .cancelled {
            opacity: 0.5;
            text-decoration: line-through;
        }
        .delay {
            color: #d97706;
        }
        [data-theme="light"] .delay {
            color: #b45309;
        }
        [data-theme="dark"] .delay {
            color: #fbbf24;
        }
        .delay-amount {
            color: #dc2626;
            font-size: """
            + self.config.font_size_delay_amount
            + """;
            font-weight: 500;
            margin-left: 0.5rem;
        }
        [data-theme="light"] .delay-amount {
            color: #dc2626;
        }
        [data-theme="dark"] .delay-amount {
            color: #f87171;
        }
        .realtime {
            color: #059669;
        }
        [data-theme="light"] .realtime {
            color: #047857;
        }
        [data-theme="dark"] .realtime {
            color: #34d399;
        }
        .container {
            width: 100vw !important;
            max-width: 100vw !important;
            height: 100vh;
            margin: 0 !important;
            padding: 0 !important;
            flex: 1 1 100%;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-sizing: border-box;
        }
        [data-theme="light"] .container {
            background-color: #ffffff;
        }
        [data-theme="dark"] .container {
            background-color: #1d232a;
        }
        .header-section {
            display: none; /* Hide header to save space */
        }
        h1 {
            display: none; /* Hide title */
        }
        .last-update {
            display: none; /* Hide last update to save space */
        }
        .stop-section {
            width: 100%;
        }
        .direction-group {
            width: 100%;
        }
        .route-group {
            width: 100%;
        }
        #departures {
            flex: 1 1 100%;
            overflow-y: auto;
            overflow-x: hidden;
            position: relative;
            width: 100%;
            height: 100%;
            box-sizing: border-box;
            padding: 0;
            margin: 0;
        }
        .status-header {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            pointer-events: none;
        }
        .status-header-item {
            display: flex;
            align-items: center;
            gap: 0.25rem;
            font-size: """
            + self.config.font_size_status_header
            + """;
            font-weight: 500;
        }
        #datetime-display {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-variant-numeric: tabular-nums;
            letter-spacing: 0.01em;
            vertical-align: baseline;
        }
        [data-theme="light"] .status-header-item {
            color: #ffffff;
        }
        [data-theme="dark"] .status-header-item {
            color: #f3f4f6;
        }
        .status-icon.connected {
            color: #059669;
        }
        [data-theme="light"] .status-icon.connected {
            color: #047857;
        }
        [data-theme="dark"] .status-icon.connected {
            color: #34d399;
        }
        .status-icon.disconnected {
            color: #dc2626;
        }
        [data-theme="light"] .status-icon.disconnected {
            color: #dc2626;
        }
        [data-theme="dark"] .status-icon.disconnected {
            color: #f87171;
        }
        .status-icon.connecting {
            color: #d97706;
            animation: pulse-connecting 2s ease-in-out infinite;
        }
        [data-theme="light"] .status-icon.connecting {
            color: #b45309;
        }
        [data-theme="dark"] .status-icon.connecting {
            color: #fbbf24;
        }
        @keyframes pulse-connecting {
            0%, 100% {
                opacity: 1;
            }
            50% {
                opacity: 0.5;
            }
        }
        .status-icon.error {
            color: #ffffff;
        }
        [data-theme="light"] .status-icon.error {
            color: #ffffff;
        }
        [data-theme="dark"] .status-icon.error {
            color: #f3f4f6;
        }
        /* Floating status box at center bottom */
        .status-floating-box {
            position: fixed;
            bottom: 1rem;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            align-items: center;
            gap: 0.4rem;
            padding: 0.4rem 0.6rem;
            background-color: rgba(128, 128, 128, 0.3);
            backdrop-filter: blur(4px);
            border-radius: 0.4rem;
            z-index: 1000;
        }
        [data-theme="light"] .status-floating-box {
            background-color: rgba(128, 128, 128, 0.2);
        }
        [data-theme="dark"] .status-floating-box {
            background-color: rgba(128, 128, 128, 0.4);
        }
        .status-floating-box-item {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 1em;
            height: 1em;
            min-width: 1em;
            min-height: 1em;
            flex-shrink: 0;
        }
        /* All status icons same size - 1em */
        .status-icon, .api-status-icon {
            width: 100%;
            height: 100%;
            display: block;
        }
        .refresh-countdown svg {
            width: 100%;
            height: 100%;
            display: block;
        }
        .refresh-countdown circle {
            fill: none;
            stroke-width: 2;
            transition: stroke-dashoffset 0.1s linear;
        }
        [data-theme="light"] .refresh-countdown circle {
            stroke: rgba(0, 0, 0, 0.3);
        }
        [data-theme="light"] .refresh-countdown circle.progress {
            stroke: rgba(0, 0, 0, 0.8);
        }
        [data-theme="dark"] .refresh-countdown circle {
            stroke: rgba(255, 255, 255, 0.3);
        }
        [data-theme="dark"] .refresh-countdown circle.progress {
            stroke: rgba(255, 255, 255, 0.8);
        }
        .api-status-icon.api-success {
            color: #059669;
        }
        [data-theme="light"] .api-status-icon.api-success {
            color: #047857;
        }
        [data-theme="dark"] .api-status-icon.api-success {
            color: #34d399;
        }
        /* Make checkmark more visible */
        #api-success-path {
            stroke-width: 2.5;
        }
        .api-status-icon.api-error {
            color: #dc2626;
        }
        [data-theme="light"] .api-status-icon.api-error {
            color: #dc2626;
        }
        [data-theme="dark"] .api-status-icon.api-error {
            color: #f87171;
        }
        .api-status-icon.api-unknown {
            color: rgba(255, 255, 255, 0.5);
        }
        [data-theme="light"] .api-status-icon.api-unknown {
            color: rgba(0, 0, 0, 0.3);
        }
        [data-theme="dark"] .api-status-icon.api-unknown {
            color: rgba(255, 255, 255, 0.3);
        }
        /* Screen reader only class */
        .sr-only {
            position: absolute;
            width: 1px;
            height: 1px;
            padding: 0;
            margin: -1px;
            overflow: hidden;
            clip: rect(0, 0, 0, 0);
            white-space: nowrap;
            border-width: 0;
        }
        /* Skip link for keyboard navigation */
        .skip-link {
            position: absolute;
            top: -40px;
            left: 0;
            background: #000;
            color: #fff;
            padding: 8px;
            text-decoration: none;
            z-index: 100;
        }
        .skip-link:focus {
            top: 0;
        }
        /* Ensure list items maintain departure-row styling */
        .departure-row {
            list-style: none;
        }
    </style>
</head>
<body class="min-h-screen bg-base-100" style="width: 100vw; max-width: 100vw; margin: 0; padding: 0;">
    <!-- Skip to main content link for keyboard navigation -->
    <a href="#departures" class="skip-link">Skip to main content</a>
    
    <!-- ARIA live region for status announcements -->
    <div id="aria-live-status" aria-live="polite" aria-atomic="true" class="sr-only"></div>
    <!-- ARIA live region for departure updates -->
    <div id="aria-live-departures" aria-live="polite" aria-atomic="false" class="sr-only"></div>
    
    <div class="container" data-phx-main role="main" aria-label="MVG Departures Dashboard">
        <div class="header-section">
            <h1>MVG Departures</h1>
            <div class="last-update" aria-live="polite" aria-atomic="true">
                Last updated: """
            + self._format_update_time(last_update)
            + """
            </div>
        </div>

        <div id="departures" role="region" aria-label="Departure information" aria-live="polite" aria-atomic="false">
            """
            + self._render_departures(direction_groups)
            + """
        </div>
        
        <!-- Floating status box at bottom right -->
        <div class="status-floating-box" role="status" aria-label="Connection and API status">
            <div class="status-floating-box-item" id="connection-status" role="img" aria-label="Connection status: connecting">
                <svg class="status-icon connecting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" id="connection-icon" aria-hidden="true">
                    <!-- Connected: show plug normally -->
                    <g id="connected-plug" style="display: none;">
                        <rect x="8" y="6" width="8" height="10" rx="1"></rect>
                        <line x1="10" y1="16" x2="10" y2="20"></line>
                        <line x1="14" y1="16" x2="14" y2="20"></line>
                    </g>
                    <!-- Disconnected: show plug with diagonal line -->
                    <g id="disconnected-plug" style="display: none;">
                        <rect x="8" y="6" width="8" height="10" rx="1"></rect>
                        <line x1="10" y1="16" x2="10" y2="20"></line>
                        <line x1="14" y1="16" x2="14" y2="20"></line>
                        <line x1="6" y1="4" x2="18" y2="22" stroke-width="2.5"></line>
                    </g>
                    <!-- Connecting: show pulsing plug -->
                    <g id="connecting-plug">
                        <rect x="8" y="6" width="8" height="10" rx="1"></rect>
                        <line x1="10" y1="16" x2="10" y2="20"></line>
                        <line x1="14" y1="16" x2="14" y2="20"></line>
                    </g>
                </svg>
            </div>
            <div class="status-floating-box-item" id="api-status-container" role="img" aria-label="API status: unknown">
                <svg class="api-status-icon api-unknown" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" id="api-status-icon" aria-hidden="true">
                    <circle cx="12" cy="12" r="10" id="api-status-circle"></circle>
                    <path d="M9 12l2 2 4-4" id="api-success-path" style="display: none;"></path>
                    <line x1="9" y1="9" x2="15" y2="15" id="api-error-line1" style="display: none;"></line>
                    <line x1="15" y1="9" x2="9" y2="15" id="api-error-line2" style="display: none;"></line>
                </svg>
            </div>
            <div class="status-floating-box-item refresh-countdown" role="img" aria-label="Refresh countdown timer">
                <svg viewBox="0 0 12 12" width="100%" height="100%" aria-hidden="true">
                    <circle cx="6" cy="6" r="5" class="background"></circle>
                    <circle cx="6" cy="6" r="5" class="progress" transform="rotate(-90 6 6)"></circle>
                </svg>
                <span class="sr-only" id="refresh-countdown-sr">Refresh countdown</span>
            </div>
        </div>
    </div>

    <script>
        // Pagination configuration
        const PAGINATION_ENABLED = """
            + str(self.config.pagination_enabled).lower()
            + """;
        const DEPARTURES_PER_PAGE = """
            + str(self.config.departures_per_page)
            + """;
        const PAGE_ROTATION_SECONDS = """
            + str(self.config.page_rotation_seconds)
            + """;
        const REFRESH_INTERVAL_SECONDS = """
            + str(self.config.refresh_interval_seconds)
            + """;
        const INITIAL_API_STATUS = '"""
            + api_status
            + """';
        
        // Date/time display
        function updateDateTime() {
            const datetimeEl = document.getElementById('datetime-display');
            if (!datetimeEl) return;
            
            const now = new Date();
            const year = now.getFullYear();
            const month = String(now.getMonth() + 1).padStart(2, '0');
            const day = String(now.getDate()).padStart(2, '0');
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            
            const dateStr = year + '-' + month + '-' + day;
            const timeStr = hours + ':' + minutes + ':' + seconds;
            const fullDateTime = dateStr + ' ' + timeStr;
            
            datetimeEl.textContent = fullDateTime;
            datetimeEl.setAttribute('aria-label', 'Current date and time: ' + fullDateTime);
        }
        
        // Update date/time every second
        updateDateTime();
        setInterval(updateDateTime, 1000);
        
        // Connection status monitoring
        // States: connecting (yellow), connected (green), broken (red)
        let connectionState = 'connecting'; // Start as connecting (yellow)
        let countdownInterval = null;
        let countdownElapsed = 0;
        let countdownRunning = false;
        let lastUpdateTime = Date.now();
        let startCountdown = null; // Will be set by initRefreshCountdown
        
        function updateConnectionStatus() {
            const connectionEl = document.getElementById('connection-status');
            if (!connectionEl) {
                console.warn('connection-status element not found');
                return;
            }
            
            const icon = connectionEl.querySelector('.status-icon');
            const connectedPlug = connectionEl.querySelector('#connected-plug');
            const disconnectedPlug = connectionEl.querySelector('#disconnected-plug');
            const connectingPlug = connectionEl.querySelector('#connecting-plug');
            const liveRegion = document.getElementById('aria-live-status');
            
            if (!icon) {
                console.warn('status-icon element not found');
                return;
            }
            
            // Explicitly remove animation to stop any running animations
            icon.style.animation = 'none';
            // Force a reflow to ensure animation is stopped
            void icon.offsetHeight;
            
            // Determine state: connecting (yellow), connected (green), or broken (red)
            if (connectionState === 'connecting') {
                icon.className = 'status-icon connecting';
                connectionEl.setAttribute('aria-label', 'Connection status: connecting');
                // Re-enable animation for connecting state
                icon.style.animation = '';
                if (connectedPlug) connectedPlug.style.display = 'none';
                if (disconnectedPlug) disconnectedPlug.style.display = 'none';
                if (connectingPlug) connectingPlug.style.display = '';
                if (liveRegion) liveRegion.textContent = 'Connection status: connecting';
            } else if (connectionState === 'connected') {
                icon.className = 'status-icon connected';
                connectionEl.setAttribute('aria-label', 'Connection status: connected');
                // Ensure animation is removed for connected state
                icon.style.animation = 'none';
                if (connectedPlug) connectedPlug.style.display = '';
                if (disconnectedPlug) disconnectedPlug.style.display = 'none';
                if (connectingPlug) connectingPlug.style.display = 'none';
                if (liveRegion) liveRegion.textContent = 'Connection status: connected';
            } else { // broken
                icon.className = 'status-icon disconnected';
                connectionEl.setAttribute('aria-label', 'Connection status: disconnected');
                // Ensure animation is removed for broken state
                icon.style.animation = 'none';
                if (connectedPlug) connectedPlug.style.display = 'none';
                if (disconnectedPlug) disconnectedPlug.style.display = '';
                if (connectingPlug) connectingPlug.style.display = 'none';
                if (liveRegion) liveRegion.textContent = 'Connection status: disconnected';
            }
        }
        
        // Refresh countdown circle - synchronized with server updates
        let countdownInitialized = false;
        let reconnectTimeout = null;
        let countdownCircle = null;
        let circumference = 0;
        
        function initRefreshCountdown() {
            const circle = document.querySelector('.refresh-countdown circle.progress');
            if (!circle) {
                console.warn('Countdown circle not found yet, will retry');
                // Retry after a short delay if element not found
                setTimeout(initRefreshCountdown, 100);
                return;
            }
            countdownCircle = circle;
            
            // Only initialize circumference and startCountdown function once
            if (!countdownInitialized) {
                countdownInitialized = true;
                const radius = 5; // Smaller radius to match reduced icon size
                circumference = 2 * Math.PI * radius;
                
                // Define startCountdown and make it accessible globally
                startCountdown = function() {
                    // Re-query the element in case DOM was updated by pyview
                    const circle = document.querySelector('.refresh-countdown circle.progress');
                    if (!circle) {
                        console.warn('Countdown circle not found, cannot start countdown');
                        return;
                    }
                    countdownCircle = circle;
                    
                    // Ensure circumference is set
                    if (circumference === 0) {
                        const radius = 5;
                        circumference = 2 * Math.PI * radius;
                    }
                    circle.setAttribute('stroke-dasharray', circumference);
                    
                    // Clear any existing interval
                    if (countdownInterval) {
                        clearInterval(countdownInterval);
                        countdownInterval = null;
                    }
                    
                    countdownElapsed = 0;
                    countdownRunning = true;
                    // Reset the circle to full (offset = 0 means full circle)
                    circle.setAttribute('stroke-dashoffset', '0');
                    const updateInterval = 100; // Update every 100ms for smooth animation
                    
                    function updateCountdown() {
                        // Re-query element in case it was replaced during countdown
                        const circle = document.querySelector('.refresh-countdown circle.progress');
                        if (!countdownRunning || !circle) return;
                        
                        countdownElapsed += updateInterval;
                        const progress = countdownElapsed / (REFRESH_INTERVAL_SECONDS * 1000);
                        const offset = circumference * (1 - progress);
                        circle.setAttribute('stroke-dashoffset', offset.toString());
                        
                        // Update screen reader text with remaining time
                        const remainingSeconds = Math.ceil((REFRESH_INTERVAL_SECONDS * 1000 - countdownElapsed) / 1000);
                        const srText = document.getElementById('refresh-countdown-sr');
                        if (srText && remainingSeconds > 0) {
                            srText.textContent = `Refresh countdown: ${remainingSeconds} seconds remaining`;
                        }
                        
                        // When countdown reaches the end, stop and wait for next update
                        if (countdownElapsed >= REFRESH_INTERVAL_SECONDS * 1000) {
                            countdownRunning = false;
                            clearInterval(countdownInterval);
                            countdownInterval = null;
                            // Update screen reader text
                            const srTextFinal = document.getElementById('refresh-countdown-sr');
                            if (srTextFinal) {
                                srTextFinal.textContent = 'Refresh countdown: updating';
                            }
                            // Check if we're overdue for an update
                            const timeSinceLastUpdate = Date.now() - lastUpdateTime;
                            if (timeSinceLastUpdate > REFRESH_INTERVAL_SECONDS * 1000 * 1.5) {
                                console.warn('No update received - server may not be sending updates');
                                // Don't mark as error immediately, just log warning
                                // The connection status will show if WebSocket is disconnected
                            }
                        }
                    }
                    
                    countdownInterval = setInterval(updateCountdown, updateInterval);
                    console.log('Countdown started');
                }
            }
            
            // Always restart countdown when called (for phx:update)
            if (startCountdown) {
                startCountdown();
            }
        }
        
        // Set up event listeners once (outside initRefreshCountdown)
        window.addEventListener('phx:error', (event) => {
            console.error('phx:error received:', event);
            connectionState = 'broken';
            // Clear reconnection timeout on error
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = null;
            }
            updateConnectionStatus();
            updateApiStatus('error');
            // Stop countdown on error
            if (countdownInterval) {
                clearInterval(countdownInterval);
                countdownInterval = null;
                countdownRunning = false;
            }
        });
        
        window.addEventListener('phx:update', (event) => {
            console.log('phx:update received - restarting countdown', event);
            // Data was successfully fetched - connection is working
            connectionState = 'connected';
            lastUpdateTime = Date.now();
            // Clear reconnection timeout since we're now connected
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = null;
            }
            
            // Update connection status after DOM update (pyview may have replaced elements)
            // Use requestAnimationFrame to ensure DOM is fully updated
            requestAnimationFrame(() => {
                updateConnectionStatus();
                // Get API status from event detail if available, default to success
                const apiStatus = event.detail?.api_status || 'success';
                updateApiStatus(apiStatus);
            });
            
            // Handle pagination if enabled
            if (PAGINATION_ENABLED) {
                initPagination();
            }
            
            // Immediately update datetime display (before delay)
            // This ensures it's visible right away, even if pyview replaced it
            requestAnimationFrame(() => {
                updateDateTime();
            });
            
            // Restart countdown after DOM update (pyview may have replaced the element)
            // Use a small delay to ensure DOM patch is complete
            setTimeout(() => {
                // Re-query the countdown circle in case it was replaced by DOM diff
                const circle = document.querySelector('.refresh-countdown circle.progress');
                if (!circle) {
                    console.warn('Countdown circle not found after phx:update, will retry');
                    // Retry initialization
                    initRefreshCountdown();
                    return;
                }
                
                // If countdown was already initialized, just restart it
                if (countdownInitialized && startCountdown) {
                    console.log('Restarting countdown after phx:update');
                    startCountdown();
                } else {
                    // Initialize if not already done
                    initRefreshCountdown();
                }
            }, 50); // Small delay to ensure DOM patch is complete
        });
        
        function updateApiStatus(status) {
                const apiStatusIcon = document.getElementById('api-status-icon');
                const apiStatusContainer = document.getElementById('api-status-container');
                if (!apiStatusIcon) {
                    console.warn('api-status-icon not found');
                    return;
                }
                
                const statusCircle = document.getElementById('api-status-circle');
                const successPath = document.getElementById('api-success-path');
                const errorLine1 = document.getElementById('api-error-line1');
                const errorLine2 = document.getElementById('api-error-line2');
                const liveRegion = document.getElementById('aria-live-status');
                
                // Remove existing status classes
                apiStatusIcon.classList.remove('api-success', 'api-error', 'api-unknown');
                
                // Add new status class and show/hide appropriate elements
                if (status === 'success') {
                    apiStatusIcon.classList.add('api-success');
                    if (apiStatusContainer) apiStatusContainer.setAttribute('aria-label', 'API status: success');
                    if (statusCircle) statusCircle.style.display = 'none'; // Hide circle, show checkmark
                    if (successPath) {
                        successPath.style.display = '';
                        successPath.setAttribute('stroke-width', '2.5'); // Make checkmark thicker
                        console.log('Showing checkmark for success');
                    } else {
                        console.warn('api-success-path not found');
                    }
                    if (errorLine1) errorLine1.style.display = 'none';
                    if (errorLine2) errorLine2.style.display = 'none';
                    if (liveRegion) liveRegion.textContent = 'API status: success';
                } else if (status === 'error') {
                    apiStatusIcon.classList.add('api-error');
                    if (apiStatusContainer) apiStatusContainer.setAttribute('aria-label', 'API status: error');
                    if (statusCircle) statusCircle.style.display = 'none'; // Hide circle, show X
                    if (successPath) successPath.style.display = 'none';
                    if (errorLine1) errorLine1.style.display = '';
                    if (errorLine2) errorLine2.style.display = '';
                    if (liveRegion) liveRegion.textContent = 'API status: error';
                } else {
                    apiStatusIcon.classList.add('api-unknown');
                    if (apiStatusContainer) apiStatusContainer.setAttribute('aria-label', 'API status: unknown');
                    if (statusCircle) statusCircle.style.display = ''; // Show circle for unknown
                    if (successPath) successPath.style.display = 'none';
                    if (errorLine1) errorLine1.style.display = 'none';
                    if (errorLine2) errorLine2.style.display = 'none';
                    if (liveRegion) liveRegion.textContent = 'API status: unknown';
                }
            }
            
            // Handle reconnection timeout - if we've been connecting for too long, show broken
            function startReconnectTimeout() {
                // Clear any existing timeout
                if (reconnectTimeout) {
                    clearTimeout(reconnectTimeout);
                }
                // If we're connecting for more than 10 seconds, show as broken
                reconnectTimeout = setTimeout(() => {
                    if (connectionState === 'connecting') {
                        console.warn('Reconnection timeout - showing broken state');
                        connectionState = 'broken';
                        updateConnectionStatus();
                    }
                }, 10000); // 10 second timeout
            }
        
        window.addEventListener('phx:disconnect', () => {
            console.log('phx:disconnect received - connection disconnected');
            // On disconnect, show broken state (red)
            connectionState = 'broken';
            // Use requestAnimationFrame to ensure DOM is ready
            requestAnimationFrame(() => {
                updateConnectionStatus();
                console.log('Connection status updated to broken (red)');
            });
            // Start timeout for reconnection
            startReconnectTimeout();
            // Stop countdown on disconnect - will restart when reconnected
            if (countdownInterval) {
                clearInterval(countdownInterval);
                countdownInterval = null;
                countdownRunning = false;
            }
        });
        
        // Handle permanent connection close
        window.addEventListener('phx:close', () => {
            console.log('phx:close received - connection permanently closed');
            connectionState = 'broken';
            updateConnectionStatus();
            // Stop countdown
            if (countdownInterval) {
                clearInterval(countdownInterval);
                countdownInterval = null;
                countdownRunning = false;
            }
        });
        
        // Detect connecting state (when WebSocket is connecting/reconnecting)
        window.addEventListener('phx:connecting', () => {
            console.log('phx:connecting received - attempting to reconnect');
            connectionState = 'connecting';
            // Use requestAnimationFrame to ensure DOM is ready
            requestAnimationFrame(() => {
                updateConnectionStatus();
                console.log('Connection status updated to connecting (yellow, pulsating)');
            });
            // Start/restart timeout for reconnection
            startReconnectTimeout();
        });
        
        // Detect when WebSocket opens (connected)
        window.addEventListener('phx:open', () => {
            console.log('phx:open received - WebSocket connected');
            connectionState = 'connected';
            // Clear reconnection timeout since we're now connected
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = null;
            }
            // Use requestAnimationFrame to ensure DOM is ready after pyview updates
            requestAnimationFrame(() => {
                updateConnectionStatus();
                console.log('Connection status updated to connected (green)');
            });
        });
        
        // Initial state: connecting (will change to connected on first phx:update or phx:open)
        // Update connection status immediately on page load
        // Use requestAnimationFrame to ensure DOM is ready
        requestAnimationFrame(() => {
            updateConnectionStatus();
            updateApiStatus(INITIAL_API_STATUS); // Use initial API status from server
        });
        
        // Cleanup on unload
        window.addEventListener('beforeunload', () => {
            if (countdownInterval) {
                clearInterval(countdownInterval);
            }
            if (reconnectTimeout) {
                clearTimeout(reconnectTimeout);
            }
        });
        
        // Note: phx:update handling is done in the main phx:update listener above
        
        function createCountdownCircle(radius = 5) {
            const circumference = 2 * Math.PI * radius;
            const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
            svg.setAttribute('viewBox', '0 0 12 12');
            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', '6');
            circle.setAttribute('cy', '6');
            circle.setAttribute('r', radius.toString());
            circle.setAttribute('stroke-dasharray', circumference.toString());
            circle.setAttribute('stroke-dashoffset', '0');
            svg.appendChild(circle);
            return { svg, circle, circumference };
        }
        
        function updateCountdown(circle, circumference, elapsed, total) {
            const progress = elapsed / total;
            const offset = circumference * (1 - progress);
            circle.setAttribute('stroke-dashoffset', offset.toString());
        }
        
        function initPagination() {
            // Paginate departures within route groups
            document.querySelectorAll('.route-group').forEach(group => {
                const departures = group.querySelectorAll('.departure-row');
                if (departures.length <= DEPARTURES_PER_PAGE) return;
                
                let currentPage = 0;
                const totalPages = Math.ceil(departures.length / DEPARTURES_PER_PAGE);
                
                // Create pagination indicator
                const indicator = document.createElement('div');
                indicator.className = 'pagination-indicator';
                indicator.setAttribute('role', 'status');
                indicator.setAttribute('aria-live', 'polite');
                indicator.setAttribute('aria-label', `Pagination: page ${currentPage + 1} of ${totalPages}`);
                const { svg, circle, circumference } = createCountdownCircle(5);
                svg.setAttribute('aria-hidden', 'true');
                indicator.appendChild(svg);
                const pageText = document.createElement('span');
                pageText.textContent = `${currentPage + 1}/${totalPages}`;
                pageText.setAttribute('aria-hidden', 'true');
                indicator.appendChild(pageText);
                const countdownText = document.createElement('span');
                countdownText.className = 'countdown-text';
                countdownText.textContent = `${PAGE_ROTATION_SECONDS}s`;
                countdownText.setAttribute('aria-hidden', 'true');
                indicator.appendChild(countdownText);
                // Add screen reader text
                const srText = document.createElement('span');
                srText.className = 'sr-only';
                srText.id = `pagination-sr-${Date.now()}`;
                srText.textContent = `Page ${currentPage + 1} of ${totalPages}`;
                indicator.appendChild(srText);
                group.appendChild(indicator);
                
                // Create pages
                for (let i = 0; i < totalPages; i++) {
                    const page = document.createElement('div');
                    page.className = 'pagination-page' + (i === 0 ? ' active' : '');
                    const start = i * DEPARTURES_PER_PAGE;
                    const end = start + DEPARTURES_PER_PAGE;
                    for (let j = start; j < end && j < departures.length; j++) {
                        page.appendChild(departures[j].cloneNode(true));
                    }
                    group.appendChild(page);
                }
                
                // Hide original departures
                departures.forEach(d => d.style.display = 'none');
                
                // Countdown timer
                let elapsed = 0;
                const updateInterval = 100; // Update every 100ms for smooth animation
                const countdownInterval = setInterval(() => {
                    elapsed += updateInterval;
                    updateCountdown(circle, circumference, elapsed, PAGE_ROTATION_SECONDS * 1000);
                    const remaining = Math.ceil((PAGE_ROTATION_SECONDS * 1000 - elapsed) / 1000);
                    countdownText.textContent = `${Math.max(0, remaining)}s`;
                    if (elapsed >= PAGE_ROTATION_SECONDS * 1000) {
                        elapsed = 0;
                    }
                }, updateInterval);
                
                // Rotate pages
                const pageInterval = setInterval(() => {
                    const pages = group.querySelectorAll('.pagination-page');
                    if (pages.length === 0) {
                        clearInterval(pageInterval);
                        clearInterval(countdownInterval);
                        return;
                    }
                    pages[currentPage].classList.remove('active');
                    currentPage = (currentPage + 1) % totalPages;
                    pages[currentPage].classList.add('active');
                    pageText.textContent = `${currentPage + 1}/${totalPages}`;
                    countdownText.textContent = `${PAGE_ROTATION_SECONDS}s`;
                    elapsed = 0; // Reset countdown
                    // Update ARIA labels
                    indicator.setAttribute('aria-label', `Pagination: page ${currentPage + 1} of ${totalPages}`);
                    const srText = indicator.querySelector('.sr-only');
                    if (srText) {
                        srText.textContent = `Page ${currentPage + 1} of ${totalPages}`;
                    }
                }, PAGE_ROTATION_SECONDS * 1000);
                
                // Store intervals for cleanup
                if (!window._paginationIntervals) {
                    window._paginationIntervals = [];
                }
                window._paginationIntervals.push(pageInterval, countdownInterval);
            });
            
            // Direction groups: no pagination, just scroll
            // Users can scroll vertically to see all direction groups
        }
        
        // Initialize on load
        function initializeAll() {
            if (PAGINATION_ENABLED) {
                initPagination();
            }
            // initRefreshCountdown will start the countdown automatically once initialized
            initRefreshCountdown();
        }
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeAll);
        } else {
            initializeAll();
        }
        
        // Cleanup intervals on page unload/disconnect
        window.addEventListener('beforeunload', () => {
            if (window._paginationIntervals) {
                window._paginationIntervals.forEach(interval => clearInterval(interval));
                window._paginationIntervals = [];
            }
        });
        
        // Also cleanup on LiveView disconnect
        window.addEventListener('phx:disconnect', () => {
            if (window._paginationIntervals) {
                window._paginationIntervals.forEach(interval => clearInterval(interval));
                window._paginationIntervals = [];
            }
        });
    </script>
    <!-- PyView client JavaScript - required for WebSocket connections -->
    <!-- Verify CSRF token is available before loading client JS -->
    <script>
        // Verify CSRF token exists
        const csrfMeta = document.querySelector("meta[name='csrf-token']");
        if (!csrfMeta) {
            console.error('CSRF token meta tag not found!');
        } else {
            console.log('CSRF token found:', csrfMeta.getAttribute('content'));
        }
        
        // Verify data-phx-main exists
        const phxMain = document.querySelector('[data-phx-main]');
        if (!phxMain) {
            console.error('data-phx-main element not found!');
        } else {
            console.log('data-phx-main element found');
        }
        
        // Load pyview client JS
        const script = document.createElement('script');
        script.src = '/static/assets/app.js';
        script.onerror = function() {
            console.error('Failed to load /static/assets/app.js');
        };
        script.onload = function() {
            console.log('app.js loaded successfully');
            // Connection status will be updated via phx:open/phx:close events
            // No need to check directly - observe events instead
        };
        document.body.appendChild(script);
    </script>
</body>
</html>
        """
        )

        # Use pyview's LiveTemplate system properly
        # Create an ibis Template from the HTML string, wrap in LiveTemplate, then return LiveRender
        from pyview.template.live_template import LiveTemplate, LiveRender
        from pyview.vendor.ibis import Template as IbisTemplate
        from pyview.meta import PyViewMeta

        # Create ibis template from HTML string
        ibis_template = IbisTemplate(html_content, template_id="departures")
        # Wrap in LiveTemplate
        live_template = LiveTemplate(ibis_template)
        # Return LiveRender which provides text() and tree() methods
        return LiveRender(live_template, assigns, meta)  # type: ignore[no-any-return]

    def _render_departures(self, direction_groups: list[tuple[str, str, list[Departure]]]) -> str:
        """Render departures grouped by direction, sorted chronologically within each group.
        Stops without departures are shown at the bottom."""
        config = self.config
        stop_configs = self.stop_configs

        if not direction_groups:
            return f'<div role="status" aria-live="polite" style="text-align: center; padding: 4rem 2rem; opacity: 0.7; font-size: {config.font_size_no_departures_available}; font-weight: 500;">No departures available</div>'

        # Separate groups with departures from stops that have no departures at all
        groups_with_departures: list[tuple[str, str, list[Departure]]] = []
        stops_with_departures: set[str] = set()

        for stop_name, direction_name, departures in direction_groups:
            if departures:
                groups_with_departures.append((stop_name, direction_name, departures))
                stops_with_departures.add(stop_name)

        # Find stops that are configured but have no departures at all
        configured_stops = {stop_config.station_name for stop_config in stop_configs}
        stops_without_departures = configured_stops - stops_with_departures

        html_parts: list[str] = []
        current_stop = None
        is_first_header = True

        # First, render all groups with departures
        for stop_name, direction_name, departures in groups_with_departures:
            # Remove "->" prefix from direction name if present
            direction_clean = direction_name.lstrip("->")

            # Combine stop name and direction into one header
            combined_header = f"{stop_name} → {direction_clean}"

            if stop_name != current_stop:
                if current_stop is not None:
                    html_parts.append("</ul></div>")  # Close list and stop-section
                html_parts.append(
                    f'<div class="stop-section" role="region" aria-label="Departures from {self._escape_html(stop_name)}">'
                )
                current_stop = stop_name

            # Status icons are now in floating box, only show time in header
            if is_first_header:
                status_html = """
                <div class="direction-header-time status-header-item" id="datetime-display" aria-label="Current date and time"></div>
                """
                html_parts.append(
                    f'<div class="direction-group"><h2 class="direction-header" role="heading" aria-level="2"><span class="direction-header-text">{self._escape_html(combined_header)}</span>{status_html}</h2><ul role="list" aria-label="Departures for {self._escape_html(combined_header)}">'
                )
                is_first_header = False
            else:
                html_parts.append(
                    f'<div class="direction-group"><h2 class="direction-header" role="heading" aria-level="2">{self._escape_html(combined_header)}</h2><ul role="list" aria-label="Departures for {self._escape_html(combined_header)}">'
                )

            # Sort by arrival time (chronological order within this direction group)
            sorted_departures = sorted(departures, key=lambda d: d.time)
            for departure in sorted_departures:
                html_parts.append(self._render_departure(departure))

            html_parts.append("</ul></div>")  # Close list and direction-group

        if current_stop is not None:
            html_parts.append("</div>")  # Close stop-section

        # At the bottom, show stops without departures - each with its own banner
        for stop_name in sorted(stops_without_departures):
            html_parts.append(
                f'<div class="stop-section" role="region" aria-label="Departures from {self._escape_html(stop_name)}">'
            )
            html_parts.append(
                f'<div class="direction-group"><h2 class="direction-header" role="heading" aria-level="2">{self._escape_html(stop_name)}</h2>'
            )
            html_parts.append(
                '<div class="departure-row" role="status" aria-live="polite"><div class="no-departures">No departures</div></div>'
            )
            html_parts.append("</div>")  # Close direction-group
            html_parts.append("</div>")  # Close stop-section

        return "".join(html_parts)

    def _render_departure(self, departure: Departure) -> str:
        """Render a single departure as HTML."""
        time_str: str = self._format_departure_time(departure)
        cancelled_class = " cancelled" if departure.is_cancelled else ""
        delay_class = " delay" if departure.delay_seconds and departure.delay_seconds > 60 else ""
        realtime_class = " realtime" if departure.is_realtime else ""

        # Format route display: just show line number (no transport type)
        route_display = departure.line

        # Format platform display
        platform_display = ""
        platform_aria = ""
        if departure.platform is not None:
            platform_display = str(departure.platform)
            platform_aria = f", Platform {platform_display}"

        # Format delay display and ARIA text
        delay_display = ""
        delay_aria = ""
        if departure.delay_seconds and departure.delay_seconds > 60:
            delay_minutes = departure.delay_seconds // 60
            delay_display = (
                f'<span class="delay-amount" aria-hidden="true">{delay_minutes}m 😞</span>'
            )
            delay_aria = f", delayed by {delay_minutes} minutes"

        # Build ARIA label with all departure information
        status_parts = []
        if departure.is_cancelled:
            status_parts.append("cancelled")
        if departure.is_realtime:
            status_parts.append("real-time")
        status_text = ", ".join(status_parts) if status_parts else "scheduled"

        aria_label = (
            f"Line {route_display} to {departure.destination}"
            f"{platform_aria}"
            f", departing in {time_str}"
            f"{delay_aria}"
            f", {status_text}"
        )

        return f"""
        <li class="departure-row{cancelled_class}" role="listitem" aria-label="{self._escape_html(aria_label)}">
            <div class="route-number" aria-hidden="true">{self._escape_html(route_display)}</div>
            <div class="destination" aria-hidden="true">{self._escape_html(departure.destination)}</div>
            <div class="platform" aria-hidden="true">{self._escape_html(platform_display)}</div>
            <div class="time{delay_class}{realtime_class}" aria-hidden="true">{time_str}{delay_display}</div>
            <span class="sr-only">{self._escape_html(aria_label)}</span>
        </li>
        """

    def _format_departure_time(self, departure: Departure) -> str:
        """Format departure time according to configuration."""
        now = datetime.now()
        time_until = departure.time

        if self.config.time_format == "minutes":
            delta = time_until - now
            minutes = int(delta.total_seconds() / 60)
            if minutes < 0:
                return "now"
            if minutes == 0:
                return "<1m"
            return f"{minutes}m"
        else:  # "at" format
            return time_until.strftime("%H:%M")

    def _format_update_time(self, update_time: datetime | None) -> str:
        """Format last update time."""
        if not update_time:
            return "Never"
        return update_time.strftime("%H:%M:%S")

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )


class PyViewWebAdapter(DisplayAdapter):
    """PyView-based web adapter for displaying departures."""

    def __init__(
        self,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
        session: "ClientSession | None" = None,
    ) -> None:
        """Initialize the web adapter."""
        self.grouping_service = grouping_service
        self.stop_configs = stop_configs
        self.config = config
        self.session = session
        self._update_task: asyncio.Task | None = None
        self._server: Any | None = None

    async def display_departures(self, direction_groups: list[tuple[str, list[Departure]]]) -> None:
        """Display grouped departures (not used directly, handled by LiveView)."""
        # This is handled by the LiveView's periodic updates
        pass

    async def start(self) -> None:
        """Start the web server."""
        import uvicorn
        from pyview import PyView

        # Store dependencies in adapter for the LiveView class to access
        # Create a LiveView class that accesses these dependencies
        adapter = self

        class ConfiguredDeparturesLiveView(DeparturesLiveView):
            def __init__(self) -> None:
                super().__init__(
                    adapter.grouping_service,
                    adapter.stop_configs,
                    adapter.config,
                )

        app = PyView()
        app.add_live_view("/", ConfiguredDeparturesLiveView)

        # Store app instance for broadcasting updates
        DeparturesLiveView._app_instance = app

        # Start the API poller immediately when server starts
        # This runs independently of client connections - API calls happen regardless
        # Do initial API call immediately before starting the server
        async def start_api_poller() -> None:
            global _api_poller_task
            if _api_poller_task is None or _api_poller_task.done():
                # Do initial fetch immediately (before starting periodic polling)
                logger.info("Making initial API call on server startup...")
                try:
                    # Fetch departures from API immediately
                    all_groups: list[tuple[str, str, list[Departure]]] = []

                    for stop_config in self.stop_configs:
                        groups = await self.grouping_service.get_grouped_departures(stop_config)
                        for direction_name, departures in groups:
                            all_groups.append(
                                (stop_config.station_name, direction_name, departures)
                            )

                    # Update shared state immediately
                    _departures_state.direction_groups = all_groups
                    _departures_state.last_update = datetime.now()
                    _departures_state.api_status = "success"
                    logger.info(
                        f"Initial API call completed at {datetime.now()}, found {len(all_groups)} direction groups"
                    )
                except Exception as e:
                    logger.error(f"Initial API call failed: {e}", exc_info=True)
                    _departures_state.api_status = "error"

                # Now start the periodic polling task
                _api_poller_task = asyncio.create_task(
                    _api_poller(
                        self.grouping_service,
                        self.stop_configs,
                        self.config,
                    )
                )
                logger.info("Started API poller (independent of client connections)")

        # Start the API poller - runs regardless of client connections
        # Create the task but don't await it - let it run in background
        asyncio.create_task(start_api_poller())

        # Serve pyview's client JavaScript and static assets
        from starlette.responses import Response, FileResponse
        from starlette.routing import Route
        from pathlib import Path
        import importlib.resources

        async def static_app_js(request: Any) -> Any:
            """Serve pyview's client JavaScript."""
            try:
                # Get pyview package path
                import pyview

                pyview_path = Path(pyview.__file__).parent
                client_js_path = pyview_path / "static" / "assets" / "app.js"

                if client_js_path.exists():
                    return FileResponse(str(client_js_path), media_type="application/javascript")
                else:
                    # Fallback: try alternative path
                    alt_path = pyview_path / "assets" / "js" / "app.js"
                    if alt_path.exists():
                        return FileResponse(str(alt_path), media_type="application/javascript")
                    else:
                        logger.error(
                            f"Could not find pyview client JS at {client_js_path} or {alt_path}"
                        )
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

        # Add route to serve pyview's client JavaScript
        app.routes.append(Route("/static/assets/app.js", static_app_js))

        config = uvicorn.Config(
            app,
            host=self.config.host,
            port=self.config.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)

        await self._server.serve()

    async def stop(self) -> None:
        """Stop the web server."""
        # Cancel the API poller task
        global _api_poller_task
        if _api_poller_task and not _api_poller_task.done():
            _api_poller_task.cancel()
            try:
                await _api_poller_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped API poller")

        if self._server:
            self._server.should_exit = True
