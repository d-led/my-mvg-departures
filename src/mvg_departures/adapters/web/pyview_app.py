"""PyView web adapter for displaying departures."""

import asyncio
import contextlib
import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from pyview import LiveView, LiveViewSocket, is_connected
from pyview.events import InfoEvent

from mvg_departures.adapters.config import AppConfig
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import (
    Departure,
    RouteConfiguration,
    StopConfiguration,
)
from mvg_departures.domain.ports import DisplayAdapter

from .state import DeparturesState, State

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from aiohttp import ClientSession


class DeparturesLiveView(LiveView[DeparturesState]):
    """LiveView for displaying MVG departures."""

    def __init__(
        self,
        state_manager: State,
        grouping_service: DepartureGroupingService,
        stop_configs: list[StopConfiguration],
        config: AppConfig,
    ) -> None:
        """Initialize the LiveView."""
        super().__init__()
        self.state_manager = state_manager
        self.grouping_service = grouping_service
        self.stop_configs = stop_configs
        self.config = config

    async def mount(self, socket: LiveViewSocket[DeparturesState], _session: dict) -> None:
        """Mount the LiveView and register socket for updates."""
        # Initialize context with current shared state
        socket.context = DeparturesState(
            direction_groups=self.state_manager.departures_state.direction_groups,
            last_update=self.state_manager.departures_state.last_update,
            api_status=self.state_manager.departures_state.api_status,
        )

        # Register socket for broadcasts
        self.state_manager.register_socket(socket)

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
        self.state_manager.unregister_socket(socket)

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
            socket.context.direction_groups = self.state_manager.departures_state.direction_groups
            socket.context.last_update = self.state_manager.departures_state.last_update
            socket.context.api_status = self.state_manager.departures_state.api_status
            logger.info(
                f"Updated context from pubsub message at {datetime.now(UTC)}, groups: {len(self.state_manager.departures_state.direction_groups)}"
            )
        else:
            logger.debug(f"Ignoring pubsub message with payload: {payload}")

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

        # Return only the content that goes inside the body
        # PyView's root template will wrap this in the full HTML structure
        html_content = """
    <!-- Viewport meta tag to prevent zooming on iOS devices -->
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />
    <!-- Minimal DaisyUI for theme support only -->
    <link href="https://cdn.jsdelivr.net/npm/daisyui@4.12.10/dist/full.min.css" rel="stylesheet" type="text/css" />
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        // Apply theme based on configuration
        const themeConfig = '{{ theme }}';
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
            font-size: {{ font_size_route_number }};
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
            overflow-x: hidden;
            overflow-y: hidden;
            white-space: nowrap;
            padding: 0 0.75rem;
            min-width: 0;
            font-size: {{ font_size_destination }};
            font-weight: 500;
            text-align: left;
        }
        .destination-text {
            display: inline-block;
            white-space: nowrap;
        }
        /* Auto-scroll animation for clipped destination text */
        /* Only applies when .clipped class is present (added by JS when text overflows) */
        @keyframes scroll-destination {
            0%, 30% {
                transform: translateX(0);
            }
            50%, 70% {
                /* Scroll distance is set dynamically via CSS variable --scroll-distance */
                transform: translateX(var(--scroll-distance, -18%));
            }
            100% {
                transform: translateX(0);
            }
        }
        .destination-text.clipped {
            animation: scroll-destination 20s ease-in-out infinite;
            will-change: transform;
        }
        /* Pause animation on interaction for better UX */
        .destination:hover .destination-text.clipped,
        .destination:active .destination-text.clipped,
        .departure-row:hover .destination-text.clipped {
            animation-play-state: paused;
        }
        [data-theme="light"] .destination {
            color: #374151;
        }
        [data-theme="dark"] .destination {
            color: #e5e7eb;
        }
        .platform {
            flex: 0 0 auto;
            font-size: {{ font_size_platform }};
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
            font-size: {{ font_size_time }};
            padding: 0 0.75rem 0 0.75rem;
            margin-right: 0;
            white-space: nowrap;
            min-width: fit-content;
            overflow: hidden;
            transition: opacity 0.3s ease-in-out;
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
            font-size: {{ font_size_no_departures }};
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
            font-size: {{ font_size_direction_header }};
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
            background-color: {{ banner_color }};
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
            font-size: {{ font_size_pagination_indicator }};
            font-weight: 600;
            z-index: 10;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        .countdown-text {
            font-size: {{ font_size_countdown_text }};
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
            font-size: {{ font_size_stop_header }};
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
            font-size: {{ font_size_delay_amount }};
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
            font-size: {{ font_size_status_header }};
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
        /* GitHub icon link inside status bar */
        .status-floating-box-github {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 1em;
            height: 1em;
            min-width: 1em;
            min-height: 1em;
            flex-shrink: 0;
            text-decoration: none;
            transition: opacity 0.2s;
            margin-left: auto; /* Push to the right */
        }
        .status-floating-box-github:hover {
            opacity: 0.8;
        }
        .status-floating-box-github svg {
            width: 100%;
            height: 100%;
            display: block;
        }
        [data-theme="light"] .status-floating-box-github svg {
            color: #000000;
        }
        [data-theme="dark"] .status-floating-box-github svg {
            color: #ffffff;
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
        /* Mobile responsive font sizes - reduce on phones for better fit */
        @media (max-width: 768px) {
            .route-number {
                font-size: calc({{ font_size_route_number }} * 0.75);
            }
            .destination {
                font-size: calc({{ font_size_destination }} * 0.75);
            }
            .platform {
                font-size: calc({{ font_size_platform }} * 0.75);
            }
            .time {
                font-size: calc({{ font_size_time }} * 0.75);
            }
            .direction-header {
                font-size: calc({{ font_size_direction_header }} * 0.75);
            }
            .stop-header {
                font-size: calc({{ font_size_stop_header }} * 0.75);
            }
            .no-departures {
                font-size: calc({{ font_size_no_departures }} * 0.75);
            }
            .pagination-indicator {
                font-size: calc({{ font_size_pagination_indicator }} * 0.75);
            }
            .countdown-text {
                font-size: calc({{ font_size_countdown_text }} * 0.75);
            }
            .status-header-item {
                font-size: calc({{ font_size_status_header }} * 0.75);
            }
            .delay-amount {
                font-size: calc({{ font_size_delay_amount }} * 0.75);
            }
        }
        /* Extra small phones (iPhone 13 mini, etc.) - more aggressive reduction */
        @media (max-width: 400px) {
            .route-number {
                font-size: calc({{ font_size_route_number }} * 0.55);
            }
            .destination {
                font-size: calc({{ font_size_destination }} * 0.65);
            }
            .platform {
                font-size: calc({{ font_size_platform }} * 0.65);
            }
            .time {
                font-size: calc({{ font_size_time }} * 0.55);
            }
            .direction-header {
                font-size: calc({{ font_size_direction_header }} * 0.65);
            }
            .stop-header {
                font-size: calc({{ font_size_stop_header }} * 0.65);
            }
            .no-departures {
                font-size: calc({{ font_size_no_departures }} * 0.65);
            }
            .pagination-indicator {
                font-size: calc({{ font_size_pagination_indicator }} * 0.65);
            }
            .countdown-text {
                font-size: calc({{ font_size_countdown_text }} * 0.65);
            }
            .status-header-item {
                font-size: calc({{ font_size_status_header }} * 0.65);
            }
            .delay-amount {
                font-size: calc({{ font_size_delay_amount }} * 0.65);
            }
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
                Last updated: {{ update_time }}
            </div>
        </div>

        <div id="departures" role="region" aria-label="Departure information" aria-live="polite" aria-atomic="false">
            {% if not has_departures %}
            <div role="status" aria-live="polite" style="text-align: center; padding: 4rem 2rem; opacity: 0.7; font-size: {{ font_size_no_departures }}; font-weight: 500;">No departures available</div>
            {% else %}
            {% for group in groups_with_departures %}
            <div class="direction-group">
                <h2 class="direction-header" role="heading" aria-level="2">
                    {% if group.is_first_header %}
                    <span class="direction-header-text">{{ group.header }}</span>
                    <div class="direction-header-time status-header-item" id="datetime-display" aria-label="Current date and time"></div>
                    {% else %}
                    {{ group.header }}
                    {% endif %}
                </h2>
                <ul role="list" aria-label="Departures for {{ group.header }}">
                    {% for departure in group.departures %}
                    <li class="departure-row{% if departure.cancelled %} cancelled{% endif %}" role="listitem" aria-label="{{ departure.aria_label }}">
                        <div class="route-number" aria-hidden="true">{{ departure.line }}</div>
                        <div class="destination" aria-hidden="true"><span class="destination-text">{{ departure.destination }}</span></div>
                        <div class="platform" aria-hidden="true">{% if departure.platform %}{{ departure.platform }}{% endif %}</div>
                        <div class="time{% if departure.has_delay %} delay{% endif %}{% if departure.is_realtime %} realtime{% endif %}" aria-hidden="true" data-time-relative="{{ departure.time_str_relative }}" data-time-absolute="{{ departure.time_str_absolute }}">
                            {{ departure.time_str_relative }}{% if departure.delay_display %}{{ departure.delay_display }}{% endif %}
                        </div>
                        <span class="sr-only">{{ departure.aria_label }}</span>
                    </li>
                    {% endfor %}
                </ul>
            </div>
            {% endfor %}
            {% for stop_name in stops_without_departures %}
            <div class="direction-group">
                <h2 class="direction-header" role="heading" aria-level="2">{{ stop_name }}</h2>
                <div class="departure-row" role="status" aria-live="polite">
                    <div class="no-departures">No departures</div>
                </div>
            </div>
            {% endfor %}
            {% endif %}
        </div>

        <!-- Floating status box at bottom center -->
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
            <div class="status-floating-box-item refresh-countdown" role="img" aria-label="Refresh countdown timer" data-last-update='{{ last_update_timestamp }}'>
                <svg viewBox="0 0 12 12" width="100%" height="100%" aria-hidden="true">
                    <circle cx="6" cy="6" r="5" class="background"></circle>
                    <circle cx="6" cy="6" r="5" class="progress" transform="rotate(-90 6 6)"></circle>
                </svg>
                <span class="sr-only" id="refresh-countdown-sr">Refresh countdown</span>
            </div>
            <!-- GitHub icon on the right side of status bar -->
            <a href="https://github.com/d-led/my-mvg-departures" target="_blank" rel="noopener noreferrer" class="status-floating-box-github status-floating-box-item" aria-label="View repository on GitHub">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" fill="currentColor" aria-hidden="true">
                    <path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2 .27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.46-.55.38A7.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/>
                </svg>
                <span class="sr-only">View repository on GitHub</span>
            </a>
        </div>
    </div>

    <script>
        // Prevent zooming on iOS devices, especially when unlocking
        (function() {
            // Reset zoom on visibility change (when device is unlocked)
            document.addEventListener('visibilitychange', function() {
                if (!document.hidden) {
                    // Reset zoom by setting viewport scale
                    const viewport = document.querySelector('meta[name="viewport"]');
                    if (viewport) {
                        viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover');
                    }
                    // Force a reflow to ensure zoom is reset
                    void document.body.offsetHeight;
                }
            });
            
            // Also reset zoom on focus (when app comes to foreground)
            window.addEventListener('focus', function() {
                const viewport = document.querySelector('meta[name="viewport"]');
                if (viewport) {
                    viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover');
                }
                void document.body.offsetHeight;
            });
            
            // Prevent double-tap zoom on iOS
            let lastTouchEnd = 0;
            document.addEventListener('touchend', function(event) {
                const now = Date.now();
                if (now - lastTouchEnd <= 300) {
                    event.preventDefault();
                }
                lastTouchEnd = now;
            }, false);
        })();

        // Pagination configuration
        const PAGINATION_ENABLED = {{ pagination_enabled }};
        const DEPARTURES_PER_PAGE = {{ departures_per_page }};
        const PAGE_ROTATION_SECONDS = {{ page_rotation_seconds }};
        const REFRESH_INTERVAL_SECONDS = {{ refresh_interval_seconds }};
        const INITIAL_API_STATUS = '{{ api_status }}';

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

        // Time format toggle - animate text content change
        let timeFormatToggleInterval = null;
        let currentTimeFormat = 'relative';
        const TIME_FORMAT_TOGGLE_SECONDS = {{ time_format_toggle_seconds }};

        function toggleTimeFormat() {
            if (TIME_FORMAT_TOGGLE_SECONDS <= 0) {
                // If toggle is disabled (0), show only relative format
                document.querySelectorAll('.time').forEach(el => {
                    const relative = el.getAttribute('data-time-relative');
                    if (relative) {
                        // Fade out, change text, fade in
                        el.style.opacity = '0';
                        setTimeout(() => {
                            const delayDisplay = el.querySelector('.delay-amount');
                            const delayHTML = delayDisplay ? delayDisplay.outerHTML : '';
                            el.innerHTML = relative + delayHTML;
                            el.style.opacity = '1';
                        }, 150);
                    }
                });
                return;
            }

            const timeElements = document.querySelectorAll('.time');

            timeElements.forEach(el => {
                const relative = el.getAttribute('data-time-relative');
                const absolute = el.getAttribute('data-time-absolute');
                if (!relative || !absolute) return;

                // Store current width to prevent layout shift when longer text is inserted
                const currentWidth = el.offsetWidth;
                el.style.width = currentWidth + 'px';

                // Fade out smoothly
                el.style.opacity = '0';

                setTimeout(() => {
                    // Preserve delay display if present
                    const delayDisplay = el.querySelector('.delay-amount');
                    const delayHTML = delayDisplay ? delayDisplay.outerHTML : '';

                    // Change text content
                    if (currentTimeFormat === 'relative') {
                        // Switch to absolute
                        el.innerHTML = absolute + delayHTML;
                    } else {
                        // Switch to relative
                        el.innerHTML = relative + delayHTML;
                    }

                    // Remove fixed width to allow new content to size naturally
                    el.style.width = '';

                    // Fade in smoothly
                    el.style.opacity = '1';
                }, 150);
            });

            currentTimeFormat = currentTimeFormat === 'relative' ? 'absolute' : 'relative';

            // Recalculate destination clipping after layout settles (time format change may affect container widths)
            setTimeout(() => {
                initDestinationScrolling();
            }, 200);
        }

        function initTimeFormatToggle() {
            // Clear any existing interval
            if (timeFormatToggleInterval) {
                clearInterval(timeFormatToggleInterval);
                timeFormatToggleInterval = null;
            }

            // Ensure all time elements start with relative format and full opacity
            document.querySelectorAll('.time').forEach(el => {
                const relative = el.getAttribute('data-time-relative');
                if (relative) {
                    // Preserve existing delay display if present
                    const delayDisplay = el.querySelector('.delay-amount');
                    const delayHTML = delayDisplay ? delayDisplay.outerHTML : '';
                    el.innerHTML = relative + delayHTML;
                }
                el.style.opacity = '1';
            });

            if (TIME_FORMAT_TOGGLE_SECONDS > 0) {
                // Start with relative format
                currentTimeFormat = 'relative';

                // Toggle every TIME_FORMAT_TOGGLE_SECONDS
                timeFormatToggleInterval = setInterval(toggleTimeFormat, TIME_FORMAT_TOGGLE_SECONDS * 1000);
            }
        }

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
        let lastServerUpdateTime = null; // Track server's last_update to detect real data updates

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

            // On initial load, start the countdown
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
            console.log('phx:update received', event);
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

            // Re-initialize time format toggle after DOM update
            requestAnimationFrame(() => {
                initTimeFormatToggle();
            });

            // Re-check destination scrolling after DOM update
            requestAnimationFrame(() => {
                initDestinationScrolling();
            });

            // Immediately update datetime display (before delay)
            // This ensures it's visible right away, even if pyview replaced it
            requestAnimationFrame(() => {
                updateDateTime();
            });

            // Check if we got a new data update by comparing server's last_update timestamp
            setTimeout(() => {
                // Re-query the countdown circle in case it was replaced by DOM diff
                const countdownEl = document.querySelector('.refresh-countdown');
                const circle = countdownEl ? countdownEl.querySelector('circle.progress') : null;

                if (!circle || !countdownEl) {
                    console.warn('Countdown circle not found after phx:update, will retry');
                    // Retry initialization
                    initRefreshCountdown();
                    return;
                }

                // Get the server's last_update timestamp from the data attribute
                const serverUpdateTime = countdownEl.getAttribute('data-last-update');
                const newServerUpdateTime = serverUpdateTime ? parseInt(serverUpdateTime, 10) : null;

                // Only restart countdown if the server's last_update timestamp actually changed
                // This ensures we only restart on real data updates, not just DOM refreshes
                if (newServerUpdateTime && newServerUpdateTime !== lastServerUpdateTime) {
                    lastServerUpdateTime = newServerUpdateTime;

                    if (countdownInitialized && startCountdown) {
                        console.log('Restarting countdown - new data update received');
                        startCountdown();
                    } else {
                        // Initialize if not already done
                        initRefreshCountdown();
                    }
                } else if (!countdownInitialized) {
                    // Initialize on first load even if timestamp hasn't changed
                    initRefreshCountdown();
                    if (newServerUpdateTime) {
                        lastServerUpdateTime = newServerUpdateTime;
                    }
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
            if (timeFormatToggleInterval) {
                clearInterval(timeFormatToggleInterval);
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

        // Check and enable scrolling animation for clipped destination text
        function initDestinationScrolling() {
            document.querySelectorAll('.destination-text').forEach(textEl => {
                const container = textEl.closest('.destination');
                if (!container) return;
                // Check if text is clipped (text width > container width)
                const textWidth = textEl.scrollWidth;
                const containerWidth = container.clientWidth;
                const wasClipped = textEl.classList.contains('clipped');
                const isClipped = textWidth > containerWidth;

                if (isClipped) {
                    // Text is clipped - add clipped class and calculate exact scroll distance
                    const scrollDistance = containerWidth - textWidth;
                    const currentScrollDistance = textEl.style.getPropertyValue('--scroll-distance');

                    // Only update if clipping state changed or scroll distance changed significantly
                    // This prevents restarting animation unnecessarily when time format changes
                    if (!wasClipped || Math.abs(parseFloat(currentScrollDistance) - scrollDistance) > 1) {
                        textEl.classList.add('clipped');
                        // Set CSS variable with the exact scroll distance
                        textEl.style.setProperty('--scroll-distance', scrollDistance + 'px');
                    }
                } else {
                    // Text fits - remove clipped class
                    if (wasClipped) {
                        textEl.classList.remove('clipped');
                        textEl.style.removeProperty('--scroll-distance');
                    }
                }
            });
        }

        // Initialize on load
        function initializeAll() {
            if (PAGINATION_ENABLED) {
                initPagination();
            }
            // initRefreshCountdown will start the countdown automatically once initialized
            initRefreshCountdown();
            // Initialize time format toggle
            initTimeFormatToggle();
            // Initialize destination scrolling for clipped text
            initDestinationScrolling();
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
            "update_time": self._format_update_time(last_update),
        }

        # Use pyview's LiveTemplate system properly
        # Create an ibis Template from the HTML string, wrap in LiveTemplate, then return LiveRender
        from pyview.template.live_template import LiveRender, LiveTemplate
        from pyview.vendor.ibis import Template as IbisTemplate

        # Create ibis template from HTML string
        ibis_template = IbisTemplate(html_content, template_id="departures")
        # Wrap in LiveTemplate
        live_template = LiveTemplate(ibis_template)
        # Return LiveRender which provides text() and tree() methods
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
                    time_str = self._format_departure_time(departure)
                    time_str_relative = self._format_departure_time_relative(departure)
                    time_str_absolute = self._format_departure_time_absolute(departure)

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

    def _format_departure_time(self, departure: Departure) -> str:
        """Format departure time according to configuration."""
        # Convert to configured timezone
        server_timezone = ZoneInfo(self.config.timezone)
        now = datetime.now(UTC).astimezone(server_timezone)
        time_until = departure.time.astimezone(server_timezone)

        if self.config.time_format == "minutes":
            delta = time_until - now
            if delta.total_seconds() < 0:
                return "now"
            # Format as compact hours and minutes (e.g., "2h40m")
            return self._format_compact_duration(delta)
        # "at" format
        return time_until.strftime("%H:%M")

    def _format_departure_time_relative(self, departure: Departure) -> str:
        """Format departure time as relative in compact format (e.g., '5m', '2h40m', 'now')."""
        # Convert to configured timezone
        server_timezone = ZoneInfo(self.config.timezone)
        now = datetime.now(UTC).astimezone(server_timezone)
        time_until = departure.time.astimezone(server_timezone)
        delta = time_until - now
        if delta.total_seconds() < 0:
            return "now"
        # Format as compact hours and minutes (e.g., "2h40m")
        return self._format_compact_duration(delta)

    def _format_departure_time_absolute(self, departure: Departure) -> str:
        """Format departure time as absolute (HH:mm format)."""
        # Convert to configured timezone
        server_timezone = ZoneInfo(self.config.timezone)
        time_until = departure.time.astimezone(server_timezone)
        return time_until.strftime("%H:%M")

    def _format_compact_duration(self, delta: timedelta) -> str:
        """Format timedelta as compact hours and minutes (e.g., '2h40m', '5m', 'now')."""
        total_seconds = int(delta.total_seconds())
        if total_seconds < 0:
            return "now"
        if total_seconds < 60:
            return "<1m"

        total_minutes = total_seconds // 60
        if total_minutes < 60:
            return f"{total_minutes}m"

        hours = total_minutes // 60
        minutes = total_minutes % 60
        if minutes == 0:
            return f"{hours}h"
        return f"{hours}h{minutes}m"

    def _format_update_time(self, update_time: datetime | None) -> str:
        """Format last update time."""
        if not update_time:
            return "Never"
        return update_time.strftime("%H:%M:%S")


class PyViewWebAdapter(DisplayAdapter):
    """PyView-based web adapter for displaying departures."""

    def __init__(
        self,
        grouping_service: DepartureGroupingService,
        route_configs: list[RouteConfiguration],
        config: AppConfig,
        session: "ClientSession | None" = None,
    ) -> None:
        """Initialize the web adapter.

        Args:
            grouping_service: Service for grouping departures.
            route_configs: List of route configurations, each with a path and stops.
            config: Application configuration.
            session: Optional aiohttp session.
        """
        self.grouping_service = grouping_service
        self.route_configs = route_configs
        self.config = config
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

        # Create a LiveView for each route
        adapter = self

        def make_live_view_class(
            state: State, stop_configs: list[StopConfiguration]
        ) -> type[DeparturesLiveView]:
            """Create a LiveView class with captured route-specific values."""
            # Capture values in closure to avoid late binding issues
            captured_state = state
            captured_stop_configs = stop_configs

            class ConfiguredDeparturesLiveView(DeparturesLiveView):
                def __init__(self) -> None:
                    super().__init__(
                        captured_state,
                        adapter.grouping_service,
                        captured_stop_configs,
                        adapter.config,
                    )

            return ConfiguredDeparturesLiveView

        for route_config in self.route_configs:
            route_path = route_config.path
            route_state = self.route_states[route_path]
            route_stop_configs = route_config.stop_configs

            logger.info(
                f"Registering route at path '{route_path}' with {len(route_stop_configs)} stops"
            )
            live_view_class = make_live_view_class(route_state, route_stop_configs)
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

        # Get the departure repository from the grouping service
        departure_repo = self.grouping_service._departure_repository

        async def _fetch_all_stations() -> None:
            """Fetch raw departures for all unique stations."""
            fetch_limit = 50  # Same as in DepartureGroupingService
            for station_id in unique_station_ids:
                try:
                    departures = await departure_repo.get_departures(
                        station_id, limit=fetch_limit
                    )
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
