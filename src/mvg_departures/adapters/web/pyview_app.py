"""PyView web adapter for displaying departures."""

import asyncio
import logging
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from pyview import LiveView

logger = logging.getLogger(__name__)

from mvg_departures.adapters.config import AppConfig
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import Departure, StopConfiguration
from mvg_departures.domain.ports import DisplayAdapter

if TYPE_CHECKING:
    from aiohttp import ClientSession


# Shared state and topic for departures (separate from LiveView)
_departures_state: dict = {
    "direction_groups": [],
    "last_update": None,
    "api_status": "unknown",
}
_departures_broadcast_topic: str = "departures:updates"
_api_poller_task: asyncio.Task | None = None


async def _api_poller(
    grouping_service: DepartureGroupingService,
    stop_configs: list[StopConfiguration],
    config: AppConfig,
) -> None:
    """Independent API poller that updates shared state and publishes via pubsub.
    
    This runs as a separate background task, completely independent of LiveView instances.
    It polls the API periodically and publishes updates to all subscribers via pubsub.
    """
    from pyview.live_socket import pub_sub_hub
    from pyview.vendor.flet.pubsub import PubSub
    
    logger.info("API poller started (independent of client connections)")
    
    async def _fetch_and_publish() -> None:
        """Fetch departures and publish update via pubsub."""
        try:
            # Fetch departures from API
            all_groups: list[tuple[str, str, list[Departure]]] = []
            
            for stop_config in stop_configs:
                groups = await grouping_service.get_grouped_departures(stop_config)
                for direction_name, departures in groups:
                    all_groups.append(
                        (stop_config.station_name, direction_name, departures)
                    )
            
            # Update shared state
            _departures_state["direction_groups"] = all_groups
            _departures_state["last_update"] = datetime.now()
            _departures_state["api_status"] = "success"
            
            logger.debug(f"API poller updated departures at {datetime.now()}")
            
            # Publish update via pubsub to all subscribers
            pubsub = PubSub(pub_sub_hub, _departures_broadcast_topic)
            update_message = {
                "type": "update",
                "timestamp": datetime.now().isoformat(),
                "api_status": "success",
            }
            await pubsub.send_all_on_topic_async(_departures_broadcast_topic, update_message)
            logger.info(f"Published update via pubsub to topic: {_departures_broadcast_topic}")
            
        except Exception as e:
            logger.error(f"API poller failed to update departures: {e}", exc_info=True)
            _departures_state["api_status"] = "error"
            
            # Still publish the error status
            try:
                pubsub = PubSub(pub_sub_hub, _departures_broadcast_topic)
                update_message = {
                    "type": "update",
                    "timestamp": datetime.now().isoformat(),
                    "api_status": "error",
                }
                await pubsub.send_all_on_topic_async(_departures_broadcast_topic, update_message)
            except Exception as pubsub_error:
                logger.error(f"Failed to publish error status via pubsub: {pubsub_error}")
    
    # Do initial update immediately
    await _fetch_and_publish()
    
    # Then poll periodically
    try:
        while True:
            await asyncio.sleep(config.refresh_interval_seconds)
            await _fetch_and_publish()
    except asyncio.CancelledError:
        logger.info("API poller cancelled")
        raise


class DeparturesLiveView(LiveView):
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

    async def mount(self, socket: object, _session: dict) -> None:
        """Mount the LiveView and subscribe to updates."""
        # Subscribe to broadcast topic for receiving updates
        # The socket's subscribe method uses _topic_callback_internal which calls send_info
        if hasattr(socket, 'connected') and socket.connected and hasattr(socket, 'subscribe'):
            try:
                # Use socket's subscribe method which sets up the callback properly
                await socket.subscribe(_departures_broadcast_topic)
                logger.debug(f"Subscribed socket to broadcast topic: {_departures_broadcast_topic}")
            except Exception as e:
                logger.warning(f"Failed to subscribe socket to broadcast topic: {e}")
        
        # Set context on socket (required by pyview)
        # Use shared state - the API poller keeps it updated independently
        socket.context = {
            "direction_groups": _departures_state["direction_groups"],
            "last_update": _departures_state["last_update"],
            "api_status": _departures_state["api_status"],
        }

    async def unmount(self, socket: object) -> None:
        """Handle socket disconnection."""
        # Unsubscribe from broadcast topic
        if hasattr(socket, 'pub_sub'):
            try:
                await socket.pub_sub.unsubscribe_topic_async(_departures_broadcast_topic)
                logger.debug(f"Unsubscribed socket from broadcast topic: {_departures_broadcast_topic}")
            except Exception as e:
                logger.warning(f"Failed to unsubscribe socket from broadcast topic: {e}")

    async def handle_info(self, event, socket: object) -> None:
        """Handle update messages from pubsub."""
        from pyview.events import InfoEvent
        
        # Extract message from InfoEvent (from pubsub) or use event directly if it's already a dict
        if isinstance(event, InfoEvent):
            # InfoEvent has name (topic) and payload (message)
            message = event.payload
            topic = event.name
            # Only process if it's from our broadcast topic
            if topic != _departures_broadcast_topic:
                return
        elif isinstance(event, dict):
            message = event
        else:
            # Unknown format, try to use as-is
            message = event
        
        # Check if this is an update message
        if isinstance(message, dict) and message.get("type") == "update":
            try:
                # Update socket context with latest data from shared state
                # (We don't serialize Departure objects in pubsub, just read from shared state)
                logger.debug("Handled update message from pubsub, updating context from shared state")
                
                # Read from shared state (more efficient than serializing in pubsub message)
                socket.context = {
                    "direction_groups": _departures_state["direction_groups"],
                    "last_update": _departures_state["last_update"],
                    "api_status": _departures_state["api_status"],
                }
                # Note: The actual diff and send is handled by socket.send_info() which calls
                # this method, then renders, calculates diff, and sends to client
            except Exception as e:
                logger.error(f"Failed to handle update message: {e}", exc_info=True)


    async def render(self, assigns: dict, meta):
        """Render the HTML template."""
        from pyview.template.live_template import LiveRender, LiveTemplate
        
        # Use shared state if assigns don't have it (fallback)
        direction_groups = assigns.get("direction_groups", _departures_state["direction_groups"])
        last_update = assigns.get("last_update", _departures_state["last_update"])
        api_status = assigns.get("api_status", _departures_state["api_status"])

        # Determine theme
        theme = self.config.theme.lower()
        if theme not in ('light', 'dark', 'auto'):
            theme = 'auto'
        
        # Get banner color from config
        banner_color = self.config.banner_color
        
        # Return only the content that goes inside the body
        # PyView's root template will wrap this in the full HTML structure
        html_content = """
    <!-- Minimal DaisyUI for theme support only -->
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        // Apply theme based on configuration
        const themeConfig = '""" + theme + """';
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
            font-size: """ + self.config.font_size_route_number + """;
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
            font-size: """ + self.config.font_size_destination + """;
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
            font-size: """ + self.config.font_size_platform + """;
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
            font-size: """ + self.config.font_size_time + """;
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
            font-size: """ + self.config.font_size_no_departures + """;
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
            font-size: """ + self.config.font_size_direction_header + """;
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
            margin-left: 0;
            white-space: nowrap;
        }
        [data-theme="light"] .direction-header {
            background-color: """ + banner_color + """;
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
            font-size: """ + self.config.font_size_pagination_indicator + """;
            font-weight: 600;
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .countdown-text {
            font-size: """ + self.config.font_size_countdown_text + """;
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
            font-size: """ + self.config.font_size_stop_header + """;
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
            font-size: """ + self.config.font_size_delay_amount + """;
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
            font-size: """ + self.config.font_size_status_header + """;
            font-weight: 500;
        }
        #datetime-display {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            font-variant-numeric: tabular-nums;
            letter-spacing: 0.01em;
            vertical-align: baseline;
        }
        .direction-header-time {
            margin-left: 0.5rem;
            white-space: nowrap;
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
        /* Floating status box at bottom right */
        .status-floating-box {
            position: fixed;
            bottom: 1rem;
            right: 1rem;
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
        }
        /* All status icons same size - 0.7em for better visibility */
        .status-icon, .api-status-icon, .refresh-countdown {
            width: 0.7em;
            height: 0.7em;
            display: inline-block;
            flex-shrink: 0;
        }
        .status-icon svg, .api-status-icon svg {
            width: 100%;
            height: 100%;
            display: block;
        }
        .refresh-countdown {
            width: 0.7em;
            height: 0.7em;
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
    </style>
</head>
<body class="min-h-screen bg-base-100" style="width: 100vw; max-width: 100vw; margin: 0; padding: 0;">
    <div class="container" data-phx-main>
        <div class="header-section">
            <h1>MVG Departures</h1>
            <div class="last-update">
                Last updated: """ + self._format_update_time(last_update) + """
            </div>
        </div>

        <div id="departures">
            """ + self._render_departures(direction_groups) + """
        </div>
        
        <!-- Floating status box at bottom right -->
        <div class="status-floating-box">
            <div class="status-floating-box-item" id="connection-status">
                <svg class="status-icon connecting" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" id="connection-icon">
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
            <div class="status-floating-box-item" id="api-status-container">
                <svg class="api-status-icon api-unknown" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" id="api-status-icon">
                    <circle cx="12" cy="12" r="10" id="api-status-circle"></circle>
                    <path d="M9 12l2 2 4-4" id="api-success-path" style="display: none;"></path>
                    <line x1="9" y1="9" x2="15" y2="15" id="api-error-line1" style="display: none;"></line>
                    <line x1="15" y1="9" x2="9" y2="15" id="api-error-line2" style="display: none;"></line>
                </svg>
            </div>
            <div class="status-floating-box-item refresh-countdown">
                <svg viewBox="0 0 12 12" width="100%" height="100%">
                    <circle cx="6" cy="6" r="5" class="background"></circle>
                    <circle cx="6" cy="6" r="5" class="progress" transform="rotate(-90 6 6)"></circle>
                </svg>
            </div>
        </div>
    </div>

    <script>
        // Pagination configuration
        const PAGINATION_ENABLED = """ + str(self.config.pagination_enabled).lower() + """;
        const DEPARTURES_PER_PAGE = """ + str(self.config.departures_per_page) + """;
        const PAGE_ROTATION_SECONDS = """ + str(self.config.page_rotation_seconds) + """;
        const REFRESH_INTERVAL_SECONDS = """ + str(self.config.refresh_interval_seconds) + """;
        const INITIAL_API_STATUS = '""" + api_status + """';
        
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
            
            datetimeEl.textContent = dateStr + ' ' + timeStr;
        }
        
        // Update date/time every second
        updateDateTime();
        setInterval(updateDateTime, 1000);
        
        // Connection status monitoring
        let isConnected = false; // Start as false (connecting)
        let isConnecting = true; // Start as connecting
        let hasError = false;
        let countdownInterval = null;
        let countdownElapsed = 0;
        let countdownRunning = false;
        let lastUpdateTime = Date.now();
        
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
            
            if (icon) {
                // Determine state: connecting (yellow), connected (green), or disconnected (red)
                if (isConnecting) {
                    icon.className = 'status-icon connecting';
                    if (connectedPlug) connectedPlug.style.display = 'none';
                    if (disconnectedPlug) disconnectedPlug.style.display = 'none';
                    if (connectingPlug) connectingPlug.style.display = '';
                } else if (isConnected && !hasError) {
                    icon.className = 'status-icon connected';
                    if (connectedPlug) connectedPlug.style.display = '';
                    if (disconnectedPlug) disconnectedPlug.style.display = 'none';
                    if (connectingPlug) connectingPlug.style.display = 'none';
                } else {
                    icon.className = 'status-icon disconnected';
                    if (connectedPlug) connectedPlug.style.display = 'none';
                    if (disconnectedPlug) disconnectedPlug.style.display = '';
                    if (connectingPlug) connectingPlug.style.display = 'none';
                }
            }
        }
        
        // Refresh countdown circle - synchronized with server updates
        function initRefreshCountdown() {
            const countdownCircle = document.querySelector('.refresh-countdown circle.progress');
            if (!countdownCircle) return;
            
            // Reconnection timeout tracking
            let reconnectTimeout = null;
            
            const radius = 5; // Smaller radius to match reduced icon size
            const circumference = 2 * Math.PI * radius;
            countdownCircle.setAttribute('stroke-dasharray', circumference);
            countdownCircle.setAttribute('stroke-dashoffset', '0');
            
            function startCountdown() {
                // Clear any existing interval
                if (countdownInterval) {
                    clearInterval(countdownInterval);
                }
                
                countdownElapsed = 0;
                countdownRunning = true;
                const updateInterval = 100; // Update every 100ms for smooth animation
                
                function updateCountdown() {
                    if (!countdownRunning) return;
                    
                    countdownElapsed += updateInterval;
                    const progress = countdownElapsed / (REFRESH_INTERVAL_SECONDS * 1000);
                    const offset = circumference * (1 - progress);
                    countdownCircle.setAttribute('stroke-dashoffset', offset.toString());
                    
                    // When countdown reaches the end, stop and wait for next update
                    if (countdownElapsed >= REFRESH_INTERVAL_SECONDS * 1000) {
                        countdownRunning = false;
                        clearInterval(countdownInterval);
                        countdownInterval = null;
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
            }
            
            // Monitor for errors and connection issues
            window.addEventListener('phx:error', (event) => {
                console.error('phx:error received:', event);
                hasError = true;
                isConnected = false;
                isConnecting = false;
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
                // Data was successfully fetched - reset everything
                hasError = false;
                isConnected = true;
                isConnecting = false;
                lastUpdateTime = Date.now();
                // Clear reconnection timeout since we're now connected
                if (reconnectTimeout) {
                    clearTimeout(reconnectTimeout);
                    reconnectTimeout = null;
                }
                updateConnectionStatus();
                // Get API status from event detail if available, default to success
                const apiStatus = event.detail?.api_status || 'success';
                updateApiStatus(apiStatus);
                startCountdown(); // Reset and start countdown from beginning
            });
            
            function updateApiStatus(status) {
                const apiStatusIcon = document.getElementById('api-status-icon');
                if (!apiStatusIcon) {
                    console.warn('api-status-icon not found');
                    return;
                }
                
                const statusCircle = document.getElementById('api-status-circle');
                const successPath = document.getElementById('api-success-path');
                const errorLine1 = document.getElementById('api-error-line1');
                const errorLine2 = document.getElementById('api-error-line2');
                
                // Remove existing status classes
                apiStatusIcon.classList.remove('api-success', 'api-error', 'api-unknown');
                
                // Add new status class and show/hide appropriate elements
                if (status === 'success') {
                    apiStatusIcon.classList.add('api-success');
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
                } else if (status === 'error') {
                    apiStatusIcon.classList.add('api-error');
                    if (statusCircle) statusCircle.style.display = 'none'; // Hide circle, show X
                    if (successPath) successPath.style.display = 'none';
                    if (errorLine1) errorLine1.style.display = '';
                    if (errorLine2) errorLine2.style.display = '';
                } else {
                    apiStatusIcon.classList.add('api-unknown');
                    if (statusCircle) statusCircle.style.display = ''; // Show circle for unknown
                    if (successPath) successPath.style.display = 'none';
                    if (errorLine1) errorLine1.style.display = 'none';
                    if (errorLine2) errorLine2.style.display = 'none';
                }
            }
            
            // Handle reconnection timeout - if we've been connecting for too long, show error
            function startReconnectTimeout() {
                // Clear any existing timeout
                if (reconnectTimeout) {
                    clearTimeout(reconnectTimeout);
                }
                // If we're connecting for more than 10 seconds, show as error
                reconnectTimeout = setTimeout(() => {
                    if (isConnecting && !isConnected) {
                        console.warn('Reconnection timeout - showing error state');
                        hasError = true;
                        isConnecting = false;
                        updateConnectionStatus();
                    }
                }, 10000); // 10 second timeout
            }
            
            window.addEventListener('phx:disconnect', () => {
                console.log('phx:disconnect received - will attempt to reconnect');
                // On disconnect, pyview will automatically try to reconnect
                // So we set connecting state (not error state)
                hasError = false;
                isConnected = false;
                isConnecting = true; // Will reconnect automatically
                updateConnectionStatus();
                // Start timeout for reconnection
                startReconnectTimeout();
                // Stop countdown on disconnect - will restart when reconnected
                if (countdownInterval) {
                    clearInterval(countdownInterval);
                    countdownInterval = null;
                    countdownRunning = false;
                }
            });
            
            // Detect connecting state (when WebSocket is connecting/reconnecting)
            window.addEventListener('phx:connecting', () => {
                console.log('phx:connecting received - attempting to reconnect');
                isConnecting = true;
                isConnected = false;
                hasError = false;
                updateConnectionStatus();
                // Start/restart timeout for reconnection
                startReconnectTimeout();
            });
            
        // Initial state: connecting (will change to connected on first phx:update)
        updateConnectionStatus();
        updateApiStatus(INITIAL_API_STATUS); // Use initial API status from server
        // Don't start countdown until first successful update
            
            // Cleanup on unload
            window.addEventListener('beforeunload', () => {
                if (countdownInterval) {
                    clearInterval(countdownInterval);
                }
                if (reconnectTimeout) {
                    clearTimeout(reconnectTimeout);
                }
            });
        }
        
        // Auto-refresh handling via LiveView
        window.addEventListener('phx:update', () => {
            if (PAGINATION_ENABLED) {
                initPagination();
            }
            initRefreshCountdown();
        });
        
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
                const { svg, circle, circumference } = createCountdownCircle(5);
                indicator.appendChild(svg);
                const pageText = document.createElement('span');
                pageText.textContent = `${currentPage + 1}/${totalPages}`;
                indicator.appendChild(pageText);
                const countdownText = document.createElement('span');
                countdownText.className = 'countdown-text';
                countdownText.textContent = `${PAGE_ROTATION_SECONDS}s`;
                indicator.appendChild(countdownText);
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
        if (PAGINATION_ENABLED && document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                initPagination();
                initRefreshCountdown();
            });
        } else if (PAGINATION_ENABLED) {
            initPagination();
            initRefreshCountdown();
        } else {
            initRefreshCountdown();
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
            // Check LiveSocket after a short delay
            setTimeout(function() {
                if (window.liveSocket) {
                    console.log('LiveSocket initialized, socket:', window.liveSocket.socket);
                    const isConnected = window.liveSocket.socket?.isConnected();
                    console.log('WebSocket connected:', isConnected);
                    if (!isConnected) {
                        console.warn('WebSocket not connected - checking connection state...');
                        // Try to manually connect if not connected
                        if (window.liveSocket.socket && !isConnected) {
                            console.log('Attempting to connect WebSocket...');
                            window.liveSocket.socket.connect();
                        }
                    }
                } else {
                    console.error('LiveSocket not found - client JS may have failed to initialize');
                }
            }, 200);
        };
        document.body.appendChild(script);
    </script>
</body>
</html>
        """
        
        # Wrap the HTML string in a LiveRender object that pyview expects
        from pyview.template.live_template import LiveRender
        
        # Create a simple object with text() and tree() methods that LiveRender expects
        class SimpleTemplate:
            def text(self, assigns, meta):
                return html_content
            
            def tree(self, assigns, meta):
                # Return a simple tree structure for pyview
                return {"html": html_content}
        
        return LiveRender(SimpleTemplate(), assigns, meta)

    def _render_departures(
        self, direction_groups: list[tuple[str, str, list[Departure]]]
    ) -> str:
        """Render departures grouped by direction, sorted chronologically within each group.
        Stops without departures are shown at the bottom."""
        config = self.config
        stop_configs = self.stop_configs
        
        if not direction_groups:
            return f'<div style="text-align: center; padding: 4rem 2rem; opacity: 0.7; font-size: {config.font_size_no_departures_available}; font-weight: 500;">No departures available</div>'

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
                    html_parts.append("</div>")
                html_parts.append(f'<div class="stop-section">')
                current_stop = stop_name

            # Status icons are now in floating box, only show time in header
            if is_first_header:
                status_html = """
                <div class="direction-header-time status-header-item" id="datetime-display"></div>
                """
                html_parts.append(
                    f'<div class="direction-group"><div class="direction-header"><span class="direction-header-text">{self._escape_html(combined_header)}</span>{status_html}</div>'
                )
                is_first_header = False
            else:
                html_parts.append(
                    f'<div class="direction-group"><div class="direction-header">{self._escape_html(combined_header)}</div>'
                )

            # Sort by arrival time (chronological order within this direction group)
            sorted_departures = sorted(departures, key=lambda d: d.time)
            for departure in sorted_departures:
                html_parts.append(self._render_departure(departure))
            
            html_parts.append('</div>')  # Close direction-group

        if current_stop is not None:
            html_parts.append("</div>")

        # At the bottom, show stops without departures - each with its own banner
        for stop_name in sorted(stops_without_departures):
            html_parts.append('<div class="stop-section">')
            html_parts.append(
                f'<div class="direction-group"><div class="direction-header">{self._escape_html(stop_name)}</div>'
            )
            html_parts.append('<div class="departure-row"><div class="no-departures">No departures</div></div>')
            html_parts.append('</div>')  # Close direction-group
            html_parts.append("</div>")  # Close stop-section

        return "".join(html_parts)


    def _render_departure(self, departure: Departure) -> str:
        """Render a single departure as HTML."""
        time_str = self._format_departure_time(departure)
        cancelled_class = " cancelled" if departure.is_cancelled else ""
        delay_class = " delay" if departure.delay_seconds and departure.delay_seconds > 60 else ""
        realtime_class = " realtime" if departure.is_realtime else ""
        
        # Format route display: just show line number (no transport type)
        route_display = departure.line
        
        # Format platform display
        platform_display = ""
        if departure.platform is not None:
            platform_display = str(departure.platform)
        
        # Format delay display
        delay_display = ""
        if departure.delay_seconds and departure.delay_seconds > 60:
            delay_minutes = departure.delay_seconds // 60
            delay_display = f'<span class="delay-amount">{delay_minutes}m 😞</span>'

        return f"""
        <div class="departure-row{cancelled_class}">
            <div class="route-number">{self._escape_html(route_display)}</div>
            <div class="destination">{self._escape_html(departure.destination)}</div>
            <div class="platform">{self._escape_html(platform_display)}</div>
            <div class="time{delay_class}{realtime_class}">{time_str}{delay_display}</div>
        </div>
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
        self._server = None

    async def display_departures(
        self, direction_groups: list[tuple[str, list[Departure]]]
    ) -> None:
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
            def __init__(self):
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
        async def start_api_poller():
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
                    _departures_state["direction_groups"] = all_groups
                    _departures_state["last_update"] = datetime.now()
                    _departures_state["api_status"] = "success"
                    logger.info(f"Initial API call completed at {datetime.now()}, found {len(all_groups)} direction groups")
                except Exception as e:
                    logger.error(f"Initial API call failed: {e}", exc_info=True)
                    _departures_state["api_status"] = "error"
                
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
        
        async def static_app_js(request):
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
                        logger.error(f"Could not find pyview client JS at {client_js_path} or {alt_path}")
                        return Response(content="// PyView client not found", media_type="application/javascript", status_code=404)
            except Exception as e:
                logger.error(f"Error serving pyview client JS: {e}", exc_info=True)
                return Response(content="// Error loading client", media_type="application/javascript", status_code=500)
        
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

