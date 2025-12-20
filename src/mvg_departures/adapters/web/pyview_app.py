"""PyView web adapter for displaying departures."""

import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from pyview import LiveView

from mvg_departures.adapters.config import AppConfig
from mvg_departures.application.services import DepartureGroupingService
from mvg_departures.domain.models import Departure, StopConfiguration
from mvg_departures.domain.ports import DisplayAdapter

if TYPE_CHECKING:
    from aiohttp import ClientSession


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
        self.direction_groups: list[tuple[str, str, list[Departure]]] = []  # (stop_name, direction, departures)
        self.last_update: datetime | None = None
        self._update_task: asyncio.Task | None = None

    async def mount(self, socket: object, _session: dict) -> None:
        """Mount the LiveView and start periodic updates."""
        await self._update_departures()
        # Schedule periodic updates
        self._update_task = asyncio.create_task(self._periodic_updates())
        # Set context on socket (required by pyview)
        socket.context = {
            "direction_groups": self.direction_groups,
            "last_update": self.last_update,
        }

    async def handle_info(self, message: dict, socket: object) -> None:
        """Handle periodic update messages."""
        if message.get("type") == "update":
            await self._update_departures()
            # Trigger re-render by updating socket state
            await self.push_event(socket, "update", {})

    async def _periodic_updates(self) -> None:
        """Send periodic update messages to all connected sockets."""
        try:
            while True:
                await asyncio.sleep(self.config.refresh_interval_seconds)
                # Update departures and notify all sockets
                await self._update_departures()
                # Broadcast update to all connected sockets
                if hasattr(self, "broadcast"):
                    await self.broadcast({"type": "update"})
                else:
                    # Fallback: update will happen on next socket interaction
                    pass
        except asyncio.CancelledError:
            pass

    async def _update_departures(self) -> None:
        """Update departure data from all configured stops."""
        all_groups: list[tuple[str, str, list[Departure]]] = []

        for stop_config in self.stop_configs:
            groups = await self.grouping_service.get_grouped_departures(
                stop_config
            )
            for direction_name, departures in groups:
                all_groups.append(
                    (stop_config.station_name, direction_name, departures)
                )

        self.direction_groups = all_groups
        self.last_update = datetime.now()

    async def render(self, assigns: dict, meta):
        """Render the HTML template."""
        from pyview.template.live_template import LiveRender, LiveTemplate
        
        direction_groups = assigns.get("direction_groups", [])
        last_update = assigns.get("last_update")

        # Determine theme
        theme = self.config.theme.lower()
        if theme not in ('light', 'dark', 'auto'):
            theme = 'auto'
        
        # Get banner color from config
        banner_color = self.config.banner_color
        
        html_content = """
<!DOCTYPE html>
<html lang="en" data-theme=""" + ('"' + theme + '"' if theme != 'auto' else '"auto"') + """>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MVG Departures</title>
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
        }
        .direction-header-text {
            flex: 1;
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
            gap: 1rem;
            pointer-events: none;
        }
        .status-header-item {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: """ + self.config.font_size_status_header + """;
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
        .status-icon {
            width: """ + self.config.font_size_status_header + """;
            height: """ + self.config.font_size_status_header + """;
            display: inline-block;
            flex-shrink: 0;
            vertical-align: middle;
        }
        .status-icon svg {
            width: 100%;
            height: 100%;
            display: block;
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
            color: #ffffff;
        }
        [data-theme="light"] .status-icon.disconnected {
            color: #ffffff;
        }
        [data-theme="dark"] .status-icon.disconnected {
            color: #f3f4f6;
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
        .refresh-countdown {
            width: 2.5rem;
            height: 2.5rem;
        }
        .refresh-countdown circle {
            fill: none;
            stroke-width: 3;
            transition: stroke-dashoffset 0.1s linear;
        }
        [data-theme="light"] .refresh-countdown circle {
            stroke: rgba(255, 255, 255, 0.3);
        }
        [data-theme="light"] .refresh-countdown circle.progress {
            stroke: rgba(255, 255, 255, 0.8);
        }
        [data-theme="dark"] .refresh-countdown circle {
            stroke: rgba(255, 255, 255, 0.3);
        }
        [data-theme="dark"] .refresh-countdown circle.progress {
            stroke: rgba(255, 255, 255, 0.8);
        }
    </style>
</head>
<body class="min-h-screen bg-base-100" style="width: 100vw; max-width: 100vw; margin: 0; padding: 0;">
    <div class="container">
        <div class="header-section">
            <h1>MVG Departures</h1>
            <div class="last-update">
                Last updated: """ + self._format_update_time(last_update) + """
            </div>
        </div>

        <div id="departures">
            """ + self._render_departures(direction_groups) + """
        </div>
    </div>

    <script>
        // Pagination configuration
        const PAGINATION_ENABLED = """ + str(self.config.pagination_enabled).lower() + """;
        const DEPARTURES_PER_PAGE = """ + str(self.config.departures_per_page) + """;
        const PAGE_ROTATION_SECONDS = """ + str(self.config.page_rotation_seconds) + """;
        const REFRESH_INTERVAL_SECONDS = """ + str(self.config.refresh_interval_seconds) + """;
        
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
        let lastUpdateTime = Date.now();
        let isConnected = true;
        let hasError = false;
        
        function updateConnectionStatus() {
            const connectionEl = document.getElementById('connection-status');
            const errorEl = document.getElementById('error-status');
            if (!connectionEl || !errorEl) return;
            
            const timeSinceUpdate = Date.now() - lastUpdateTime;
            // Check if we're still connected (within 2x refresh interval)
            const stillConnected = timeSinceUpdate < (REFRESH_INTERVAL_SECONDS * 1000 * 2);
            
            // Update connection status based on last fetch result
            connectionEl.style.display = 'flex';
            const icon = connectionEl.querySelector('.status-icon');
            const connectedPath = connectionEl.querySelector('#connected-path');
            const disconnectedLine1 = connectionEl.querySelector('#disconnected-line1');
            const disconnectedLine2 = connectionEl.querySelector('#disconnected-line2');
            
            if (icon) {
                // Green checkmark = successfully fetched data, Red X = failed/disconnected
                icon.className = 'status-icon ' + (isConnected && !hasError ? 'connected' : 'disconnected');
            }
            
            if (isConnected && !hasError) {
                // Show green checkmark
                if (connectedPath) connectedPath.style.display = '';
                if (disconnectedLine1) disconnectedLine1.style.display = 'none';
                if (disconnectedLine2) disconnectedLine2.style.display = 'none';
            } else {
                // Show red X
                if (connectedPath) connectedPath.style.display = 'none';
                if (disconnectedLine1) disconnectedLine1.style.display = '';
                if (disconnectedLine2) disconnectedLine2.style.display = '';
            }
            
            // If we haven't received updates for too long, mark as disconnected
            if (!stillConnected && isConnected) {
                isConnected = false;
            }
            
            // Show/hide error status
            if (hasError) {
                errorEl.style.display = 'flex';
            } else {
                errorEl.style.display = 'none';
            }
        }
        
        // Monitor for errors and connection issues
        window.addEventListener('phx:error', (event) => {
            hasError = true;
            isConnected = false;
            updateConnectionStatus();
        });
        
        window.addEventListener('phx:update', () => {
            // Data was successfully fetched
            lastUpdateTime = Date.now();
            hasError = false;
            isConnected = true;
            updateConnectionStatus();
        });
        
        window.addEventListener('phx:disconnect', () => {
            hasError = true;
            isConnected = false;
            updateConnectionStatus();
        });
        
        // Check connection status periodically
        setInterval(updateConnectionStatus, 1000);
        updateConnectionStatus();
        
        // Refresh countdown circle
        function initRefreshCountdown() {
            const countdownCircle = document.querySelector('.refresh-countdown circle.progress');
            if (!countdownCircle) return;
            
            const radius = 15;
            const circumference = 2 * Math.PI * radius;
            countdownCircle.setAttribute('stroke-dasharray', circumference);
            countdownCircle.setAttribute('stroke-dashoffset', '0');
            
            let elapsed = 0;
            const updateInterval = 100; // Update every 100ms for smooth animation
            
            function updateCountdown() {
                elapsed += updateInterval;
                const progress = elapsed / (REFRESH_INTERVAL_SECONDS * 1000);
                const offset = circumference * (1 - progress);
                countdownCircle.setAttribute('stroke-dashoffset', offset.toString());
                
                if (elapsed >= REFRESH_INTERVAL_SECONDS * 1000) {
                    elapsed = 0;
                }
            }
            
            const countdownInterval = setInterval(updateCountdown, updateInterval);
            
            // Reset on LiveView update
            window.addEventListener('phx:update', () => {
                elapsed = 0;
                countdownCircle.setAttribute('stroke-dashoffset', '0');
            });
            
            // Cleanup on unload
            window.addEventListener('beforeunload', () => {
                clearInterval(countdownInterval);
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
        if not direction_groups:
            return f'<div style="text-align: center; padding: 4rem 2rem; opacity: 0.7; font-size: {self.config.font_size_no_departures_available}; font-weight: 500;">No departures available</div>'

        # Separate groups with departures from stops that have no departures at all
        groups_with_departures: list[tuple[str, str, list[Departure]]] = []
        stops_with_departures: set[str] = set()
        
        for stop_name, direction_name, departures in direction_groups:
            if departures:
                groups_with_departures.append((stop_name, direction_name, departures))
                stops_with_departures.add(stop_name)
        
        # Find stops that are configured but have no departures at all
        configured_stops = {stop_config.station_name for stop_config in self.stop_configs}
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

            # Add status header to first direction header only
            if is_first_header:
                status_html = """
                <div class="status-header">
                    <div class="status-header-item" id="datetime-display"></div>
                    <div class="status-header-item" id="connection-status" style="display: none;">
                        <svg class="status-icon connected" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" id="connection-icon">
                            <circle cx="12" cy="12" r="10"></circle>
                            <path d="M9 12l2 2 4-4" id="connected-path"></path>
                            <line x1="9" y1="9" x2="15" y2="15" id="disconnected-line1" style="display: none;"></line>
                            <line x1="15" y1="9" x2="9" y2="15" id="disconnected-line2" style="display: none;"></line>
                        </svg>
                    </div>
                    <div class="status-header-item" id="error-status" style="display: none;">
                        <svg class="status-icon error" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="12" cy="12" r="10"></circle>
                            <line x1="12" y1="8" x2="12" y2="12"></line>
                            <line x1="12" y1="16" x2="12.01" y2="16"></line>
                        </svg>
                    </div>
                    <div class="refresh-countdown">
                        <svg viewBox="0 0 36 36" width="100%" height="100%">
                            <circle cx="18" cy="18" r="15" class="background"></circle>
                            <circle cx="18" cy="18" r="15" class="progress" transform="rotate(-90 18 18)"></circle>
                        </svg>
                    </div>
                </div>
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
        if self._server:
            self._server.should_exit = True

