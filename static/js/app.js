// Suppress pyview debug logging (mount/update events from app.js)
    // This must run before app.js loads to intercept its console.log calls

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
    const PAGINATION_ENABLED = window.DEPARTURES_CONFIG.paginationEnabled === true;
    const DEPARTURES_PER_PAGE = window.DEPARTURES_CONFIG.departuresPerPage || 5;
    const PAGE_ROTATION_SECONDS = window.DEPARTURES_CONFIG.pageRotationSeconds || 10;
    const REFRESH_INTERVAL_SECONDS = window.DEPARTURES_CONFIG.refreshIntervalSeconds || 20;
    const TIME_FORMAT_TOGGLE_SECONDS = window.DEPARTURES_CONFIG.timeFormatToggleSeconds || 0;
    const INITIAL_API_STATUS = (window.DEPARTURES_CONFIG.apiStatus && window.DEPARTURES_CONFIG.apiStatus !== 'undefined' && window.DEPARTURES_CONFIG.apiStatus !== '') ? window.DEPARTURES_CONFIG.apiStatus : 'unknown';

    // OPTIONAL: Time on the topmost visible header on scroll
    // Set to true to enable this feature
    const DATETIME_ON_VISIBLE_HEADER = true;

    // Find the topmost visible direction header (if it's not the first one)
    function findTopmostVisibleHeader() {
        const departuresEl = document.getElementById('departures');
        if (!departuresEl) return null;

        const scrollTop = departuresEl.scrollTop;
        const viewportBottom = scrollTop + departuresEl.clientHeight;
        const headers = departuresEl.querySelectorAll('.direction-header');
        
        if (headers.length === 0) return null;

        const firstHeader = headers[0];
        let topmostVisibleHeader = null;
        let topmostTop = Infinity;

        // Find the topmost visible header
        for (let i = 0; i < headers.length; i++) {
            const header = headers[i];
            const rect = header.getBoundingClientRect();
            const containerRect = departuresEl.getBoundingClientRect();
            
            // Check if header is visible in viewport
            const headerTop = rect.top - containerRect.top + scrollTop;
            const headerBottom = headerTop + rect.height;
            
            if (headerTop <= viewportBottom && headerBottom >= scrollTop) {
                // This header is visible, check if it's the topmost so far
                if (headerTop < topmostTop) {
                    topmostTop = headerTop;
                    topmostVisibleHeader = header;
                }
            }
        }

        // Only return if the topmost visible header is not the first one
        if (topmostVisibleHeader && topmostVisibleHeader !== firstHeader) {
            return topmostVisibleHeader;
        }
        
        return null;
    }

    // Update clock in a header element
    function updateHeaderClock(headerEl, dateTimeStr) {
        if (!headerEl) return;
        
        // Find or create the clock element in this header
        let clockEl = headerEl.querySelector('.direction-header-time');
        
        if (!clockEl) {
            // Create clock element if it doesn't exist
            clockEl = document.createElement('div');
            clockEl.className = 'direction-header-time status-header-item';
            clockEl.setAttribute('aria-label', 'Current date and time: ' + dateTimeStr);
            headerEl.appendChild(clockEl);
        }
        
        // Update only the text content (quick update)
        clockEl.textContent = dateTimeStr.split(' ')[1]; // Only time part (HH:MM:SS)
        clockEl.setAttribute('aria-label', 'Current date and time: ' + dateTimeStr);
    }

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

        // Update main header clock
        datetimeEl.textContent = fullDateTime;
        datetimeEl.setAttribute('aria-label', 'Current date and time: ' + fullDateTime);

        // If feature is enabled, also update topmost visible header
        if (DATETIME_ON_VISIBLE_HEADER) {
            const topmostHeader = findTopmostVisibleHeader();
            if (topmostHeader) {
                updateHeaderClock(topmostHeader, fullDateTime);
            }
        }
    }

    // Update date/time every second
    updateDateTime();
    setInterval(updateDateTime, 1000);

    // Time format toggle - animate text content change
    let timeFormatToggleInterval = null;
    let currentTimeFormat = 'relative';
    // TIME_FORMAT_TOGGLE_SECONDS is defined above with safe defaults

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
    // States: connecting (yellow), connected (green), unstable (orange/question-mark-circle), broken (red)
    // Start as 'connecting' - will change to 'connected' on phx:open, or 'broken' on phx:disconnect/phx:close
    let connectionState = 'connecting';
    let countdownInterval = null;
    let countdownElapsed = 0;
    let countdownRunning = false;
    let lastUpdateTime = Date.now();
    let startCountdown = null; // Will be set by initRefreshCountdown
    let updateTimeout = null; // Timeout to detect when updates stop arriving
    let failedUpdateCount = 0; // Track consecutive failed updates
    let lastSuccessfulUpdate = Date.now(); // Track last successful update
    // No reconnectTimeout - PyView handles reconnection, we just listen to events


    function updateConnectionStatus() {
        const connectionEl = document.getElementById('connection-status');
        if (!connectionEl) {
            // console.warn('connection-status element not found');
            return;
        }

        const connectedIcon = connectionEl.querySelector('#connected-icon');
        const disconnectedIcon = connectionEl.querySelector('#disconnected-icon');
        const connectingIcon = connectionEl.querySelector('#connecting-icon');
        const unstableIcon = connectionEl.querySelector('#unstable-icon');
        const liveRegion = document.getElementById('aria-live-status');

        if (!connectedIcon || !disconnectedIcon || !connectingIcon || !unstableIcon) {
            // console.warn('Connection status icons not found');
            return;
        }

        // Update data attribute to preserve state across DOM updates
        connectionEl.setAttribute('data-connection-state', connectionState);

        // Hide all icons first
        connectedIcon.style.display = 'none';
        disconnectedIcon.style.display = 'none';
        connectingIcon.style.display = 'none';
        unstableIcon.style.display = 'none';

        // Determine state: connecting (yellow), connected (green), unstable (orange/question-mark-circle), or broken (red)
        // CSS handles animations via classes - no need to manage inline styles
        if (connectionState === 'connecting') {
            connectionEl.setAttribute('aria-label', 'Connection status: connecting');
            connectionEl.setAttribute('title', 'WebSocket connection: connecting');
            connectingIcon.style.display = '';
            if (liveRegion) liveRegion.textContent = 'Connection status: connecting';
        } else if (connectionState === 'connected') {
            connectionEl.setAttribute('aria-label', 'Connection status: connected');
            connectionEl.setAttribute('title', 'WebSocket connection: connected');
            connectedIcon.style.display = '';
            if (liveRegion) liveRegion.textContent = 'Connection status: connected';
        } else if (connectionState === 'unstable') {
            connectionEl.setAttribute('aria-label', 'Connection status: unstable');
            connectionEl.setAttribute('title', 'WebSocket connection: unstable - updates may be delayed or incomplete');
            unstableIcon.style.display = '';
            if (liveRegion) liveRegion.textContent = 'Connection status: unstable';
        } else { // broken
            connectionEl.setAttribute('aria-label', 'Connection status: disconnected');
            connectionEl.setAttribute('title', 'WebSocket connection: disconnected');
            disconnectedIcon.style.display = '';
            if (liveRegion) liveRegion.textContent = 'Connection status: disconnected';
        }
    }

    // Restore connection state from data attribute after DOM updates
    function restoreConnectionState() {
        const connectionEl = document.getElementById('connection-status');
        if (connectionEl) {
            const savedState = connectionEl.getAttribute('data-connection-state');
            if (savedState && (savedState === 'connecting' || savedState === 'connected' || savedState === 'unstable' || savedState === 'broken')) {
                // Only restore if we don't have a more recent state
                // This prevents overwriting a newer state with an older one
                if (connectionState === 'connecting' && savedState !== 'connecting') {
                    connectionState = savedState;
                } else if (connectionState !== savedState && savedState !== 'connecting') {
                    // If saved state is more definitive (connected/unstable/broken), use it
                    connectionState = savedState;
                }
            }
        }
    }

    // Refresh countdown circle - synchronized with server updates
    let countdownInitialized = false;
    let countdownCircle = null;
    let circumference = 0;
    let lastServerUpdateTime = null; // Track server's last_update to detect real data updates

    function initRefreshCountdown() {
        const circle = document.querySelector('.refresh-countdown circle.progress');
        if (!circle) {
            // console.warn('Countdown circle not found yet, will retry');
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
                    // console.warn('Countdown circle not found, cannot start countdown');
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
                            // console.warn('No update received - server may not be sending updates');
                            // Don't mark as error immediately, just log warning
                            // The connection status will show if WebSocket is disconnected
                        }
                    }
                }

                countdownInterval = setInterval(updateCountdown, updateInterval);
                // console.log('Countdown started');
            }
        }

        // On initial load, start the countdown
        if (startCountdown) {
            startCountdown();
        }
    }

    // Set up event listeners once (outside initRefreshCountdown)
    window.addEventListener('phx:error', (event) => {
        try {
            console.error('phx:error received:', event);
            // Error occurred - but don't change connection state
            // Only phx:disconnect/phx:close indicate real disconnections
            // phx:error might be a data error, not a connection error
            // Use requestAnimationFrame to ensure DOM is ready
            requestAnimationFrame(() => {
                updateApiStatus('error');
            });
        // Stop countdown on error
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
            countdownRunning = false;
        }
        } catch (e) {
            console.error('Error in phx:error handler:', e);
            throw e; // Re-throw to maintain observability
        }
    });

    window.addEventListener('phx:update', (event) => {
        try {
            // console.log('phx:update received', event);
            // Data was successfully fetched - connection is working
            const now = Date.now();
        const timeSinceLastUpdate = now - lastUpdateTime;
        
        // phx:update means we're connected and receiving data
        // Always set to connected when we receive updates - this overrides any false positive from fallback checks
        // This is the PRIMARY way to know we're connected - updates mean the connection is working
        connectionState = 'connected';
        failedUpdateCount = 0;
        
        lastUpdateTime = now;
        lastSuccessfulUpdate = now;
        
        // Update connection status immediately to ensure UI reflects connected state
        updateConnectionStatus();

        // PyView handles reconnection - no custom timeout to clear

        // Clear update timeout - we don't use it to detect disconnections
        // Only phx:disconnect/phx:close events indicate real disconnections
        if (updateTimeout) {
            clearTimeout(updateTimeout);
            updateTimeout = null;
        }

        // Determine API status: prioritize server's API status, then check update health
        let apiStatus = 'unknown';
        const departuresEl = document.getElementById('departures');
        const apiStatusEl = document.getElementById('api-status-value');
        
        // First, check server's API status (indicates if MVG API call succeeded/failed)
        let serverApiStatus = null;
        if (apiStatusEl) {
            const statusText = (apiStatusEl.textContent || '').trim().toLowerCase();
            if (statusText === 'success' || statusText === 'error' || statusText === 'unknown') {
                serverApiStatus = statusText;
            }
        }
        
        // If server reports API error, show error regardless of update health
        if (serverApiStatus === 'error') {
            apiStatus = 'error';
        } else {
            // Check if update contains undefined values (unhealthy update from server)
            let updateIsHealthy = true;
            if (departuresEl) {
                const content = departuresEl.textContent || '';
                if (content.includes('undefined') || content.trim() === 'undefined') {
                    updateIsHealthy = false;
                }
            }
            
            if (!updateIsHealthy) {
                // Unhealthy update - show error
                apiStatus = 'error';
            } else if (serverApiStatus === 'success') {
                // Healthy update and server reports success
                apiStatus = 'success';
            } else if (serverApiStatus === 'unknown') {
                // Server status unknown, but update looks healthy
                apiStatus = 'unknown';
            } else {
                // No server status, but update looks healthy - assume success
                apiStatus = 'success';
            }
        }
        
        updateApiStatus(apiStatus);

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

        // Recalculate font sizes if fill_vertical_space is enabled
        if (window.DEPARTURES_CONFIG && window.DEPARTURES_CONFIG.fillVerticalSpace) {
            requestAnimationFrame(() => {
                calculateFillVerticalSpace();
            });
        }

        // Check if we got a new data update by comparing server's last_update timestamp
        setTimeout(() => {
            // Re-query the countdown circle in case it was replaced by DOM diff
            const countdownEl = document.querySelector('.refresh-countdown');
            const circle = countdownEl ? countdownEl.querySelector('circle.progress') : null;

            if (!circle || !countdownEl) {
                // console.warn('Countdown circle not found after phx:update, will retry');
                // Retry initialization
                initRefreshCountdown();
                return;
            }

            // Get the server's last_update timestamp from the data attribute
            const serverUpdateTime = countdownEl.getAttribute('data-last-update');
            const newServerUpdateTime = serverUpdateTime ? parseInt(serverUpdateTime, 10) : null;

            // Always restart countdown on phx:update to keep it in sync
            if (countdownInitialized && startCountdown) {
                startCountdown();
            } else {
                // Initialize if not already done
                initRefreshCountdown();
            }
            
            // Update the tracked timestamp
            if (newServerUpdateTime) {
                lastServerUpdateTime = newServerUpdateTime;
            }
        }, 50); // Small delay to ensure DOM patch is complete
        } catch (e) {
            console.error('Error in phx:update handler:', e, event);
            throw e; // Re-throw to maintain observability
        }
    });

    // Presence count is managed entirely by PyView - do not modify DOM

    function updateApiStatus(status) {
        const apiSuccessIcon = document.getElementById('api-success-icon');
        const apiErrorIcon = document.getElementById('api-error-icon');
        const apiUnknownIcon = document.getElementById('api-unknown-icon');
        const apiStatusContainer = document.getElementById('api-status-container');
        const liveRegion = document.getElementById('aria-live-status');

        if (!apiSuccessIcon || !apiErrorIcon || !apiUnknownIcon) {
            // console.warn('API status icons not found');
            return;
        }

        // Hide all icons first
        apiSuccessIcon.style.display = 'none';
        apiErrorIcon.style.display = 'none';
        apiUnknownIcon.style.display = 'none';

        // Show appropriate icon based on status
        if (status === 'success') {
            if (apiStatusContainer) {
                apiStatusContainer.setAttribute('aria-label', 'API status: success');
                apiStatusContainer.setAttribute('title', 'MVG API connection: success');
            }
            apiSuccessIcon.style.display = '';
            if (liveRegion) liveRegion.textContent = 'API status: success';
        } else if (status === 'error') {
            if (apiStatusContainer) {
                apiStatusContainer.setAttribute('aria-label', 'API status: error');
                apiStatusContainer.setAttribute('title', 'MVG API connection: error');
            }
            apiErrorIcon.style.display = '';
            if (liveRegion) liveRegion.textContent = 'API status: error';
        } else {
            if (apiStatusContainer) {
                apiStatusContainer.setAttribute('aria-label', 'API status: unknown');
                apiStatusContainer.setAttribute('title', 'MVG API connection: status unknown');
            }
            apiUnknownIcon.style.display = '';
            if (liveRegion) liveRegion.textContent = 'API status: unknown';
        }
    }

        // No custom reconnection logic - PyView handles reconnection automatically
        // We just listen to the events: phx:disconnect -> phx:connecting -> phx:open

    window.addEventListener('phx:disconnect', () => {
        try {
            // On disconnect, show broken state (red) - PyView will attempt to reconnect
            // Note: onClose hook already set it to 'unstable' (orange), now we confirm it's broken (red)
            connectionState = 'broken';
            // Update UI immediately - don't wait for requestAnimationFrame
            updateConnectionStatus();
            
        // Clear update timeout since we're disconnected
        if (updateTimeout) {
            clearTimeout(updateTimeout);
            updateTimeout = null;
        }
        
        // Clear the close timeout from onClose hook since phx:disconnect fired
        if (window._closeTimeout) {
            clearTimeout(window._closeTimeout);
            window._closeTimeout = null;
        }
        
        // Also update in next frame to ensure it sticks
        requestAnimationFrame(() => {
            updateConnectionStatus();
        });
        // Stop countdown on disconnect - will restart when reconnected via phx:open
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
            countdownRunning = false;
        }
        } catch (e) {
            console.error('Error in phx:disconnect handler:', e);
            throw e;
        }
    });

    // Handle permanent connection close (no reconnection will be attempted)
    window.addEventListener('phx:close', () => {
        try {
            // console.log('phx:close received - connection permanently closed, no reconnection');
            // This is a permanent close - PyView will NOT attempt to reconnect
            connectionState = 'broken';
        // Clear update timeout since connection is closed
        if (updateTimeout) {
            clearTimeout(updateTimeout);
            updateTimeout = null;
        }
        // Use requestAnimationFrame to ensure DOM is ready
        requestAnimationFrame(() => {
            updateConnectionStatus();
            // console.log('Connection status updated to broken (red)');
        });
        // Stop countdown
        if (countdownInterval) {
            clearInterval(countdownInterval);
            countdownInterval = null;
            countdownRunning = false;
        }
        } catch (e) {
            console.error('Error in phx:close handler:', e);
            throw e;
        }
    });

    // Detect connecting state (when WebSocket is connecting/reconnecting)
    window.addEventListener('phx:connecting', () => {
        try {
            // console.log('phx:connecting received - attempting to reconnect');
            connectionState = 'connecting';
        // Use requestAnimationFrame to ensure DOM is ready
        requestAnimationFrame(() => {
            updateConnectionStatus();
            // console.log('Connection status updated to connecting (yellow, pulsating)');
        });
        // PyView handles reconnection automatically - just update UI to show connecting state
        } catch (e) {
            console.error('Error in phx:connecting handler:', e);
            throw e;
        }
    });

    // Disable debug logging once - assume liveSocket is available in callbacks
    let debugDisabled = false;
    function disableDebugOnce() {
        if (debugDisabled || !window.liveSocket) return;
        try {
            window.liveSocket.disableDebug();
            debugDisabled = true;
        } catch (e) {
            // Silently fail - not critical
        }
    }

    // Detect when WebSocket opens (connected or reconnected)
    window.addEventListener('phx:open', () => {
        try {
            // console.log('phx:open received - WebSocket connected/reconnected');
            connectionState = 'connected';
            // Reset failed update count on successful connection
            failedUpdateCount = 0;
            // Update lastUpdateTime to prevent false disconnection detection
            lastUpdateTime = Date.now();
            
            // Disable debug logging once after connection
            disableDebugOnce();
            
        // PyView handles reconnection - no custom timeout to clear
        // Use requestAnimationFrame to ensure DOM is ready after pyview updates
        requestAnimationFrame(() => {
            updateConnectionStatus();
            // console.log('Connection status updated to connected (green)');
        });
        // Restart countdown when connection opens/reopens
        if (countdownInitialized && startCountdown) {
            startCountdown();
        }
        } catch (e) {
            console.error('Error in phx:open handler:', e);
            throw e;
        }
    });

    // Initial state: connecting (will change to connected on first phx:update or phx:open)
    // Update connection status immediately on page load
    // Use requestAnimationFrame to ensure DOM is ready
    requestAnimationFrame(() => {
        updateConnectionStatus();
        updateApiStatus(INITIAL_API_STATUS); // Use initial API status from server
    });

    // No fallback connection check - we rely ONLY on PyView events
    // The user requirement: "the only thing that should cause a disconnection animation 
    // or a disconnected icon is a REAL DISCONNECTION of liveSocket!"
    // PyView's phx:disconnect and phx:close events are the source of truth

    // Cleanup on unload
    window.addEventListener('beforeunload', () => {
        if (countdownInterval) {
            clearInterval(countdownInterval);
        }
        // No reconnectTimeout - PyView handles reconnection
        if (updateTimeout) {
            clearTimeout(updateTimeout);
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

    // Calculate dynamic font sizes to fill vertical space
    function calculateFillVerticalSpace() {
        if (!window.DEPARTURES_CONFIG || !window.DEPARTURES_CONFIG.fillVerticalSpace) {
            return;
        }

        const departuresEl = document.getElementById('departures');
        if (!departuresEl) return;

        // Get all direction groups
        const directionGroups = departuresEl.querySelectorAll('.direction-group');
        if (directionGroups.length === 0) return;

        // Count total rows: each direction group has 1 header + its departure rows
        let totalRows = 0;
        directionGroups.forEach(group => {
            const header = group.querySelector('.direction-header');
            const departureRows = group.querySelectorAll('.departure-row');
            if (header) totalRows += 1; // Header counts as 1 row
            totalRows += departureRows.length;
        });

        if (totalRows === 0) return;

        // Calculate available viewport height
        // Account for status bar at bottom (approximately 60px including padding)
        const statusBarHeight = 60;
        const viewportHeight = window.innerHeight;
        const availableHeight = viewportHeight - statusBarHeight;

        // Calculate height per row (distribute evenly)
        const heightPerRow = availableHeight / totalRows;

        // Calculate base font size from height per row
        // Use almost all available height, reserving only minimal padding
        // We'll use a slightly higher line-height to better fill the vertical space
        const reservedPadding = 4; // Minimal padding per row in pixels (reduced to eliminate bottom whitespace)
        const usableHeight = heightPerRow - reservedPadding;
        // Use a slightly higher line height (1.25 instead of 1.2) to better distribute vertical space
        const lineHeight = 1.25;
        const baseFontSize = usableHeight / lineHeight;

        // Calculate proportional font sizes for different elements
        // These ratios are based on the default font sizes in the config:
        // route_number: 4rem, destination: 3.5rem, time: 4rem, platform: 2.5rem
        // direction_header: same as destination (3.5rem), stop_header: 3rem
        // So relative to a base of ~3.5rem (destination):
        const fontSizes = {
            routeNumber: baseFontSize * (4.0 / 3.5),      // 4rem relative to 3.5rem base
            destination: baseFontSize,                       // 3.5rem is our base
            time: baseFontSize * (4.0 / 3.5),              // 4rem relative to 3.5rem base
            platform: baseFontSize * (2.5 / 3.5),         // 2.5rem relative to 3.5rem base
            directionHeader: baseFontSize,                  // Same size as destination
            stopHeader: baseFontSize * (3.0 / 3.5),       // 3rem relative to 3.5rem base
            noDepartures: baseFontSize * (2.5 / 3.5),     // 2.5rem relative to 3.5rem base
            paginationIndicator: baseFontSize * (2.0 / 3.5),
            countdownText: baseFontSize * (1.8 / 3.5),
            delayAmount: baseFontSize * (2.0 / 3.5),
            statusHeader: baseFontSize * (1.875 / 3.5),
        };

        // Apply minimum font size to ensure legibility (at least 12px)
        const minFontSize = 12;
        Object.keys(fontSizes).forEach(key => {
            if (fontSizes[key] < minFontSize) {
                fontSizes[key] = minFontSize;
            }
        });

        // Update CSS custom properties (use px units for precise control)
        const root = document.documentElement;
        root.style.setProperty('--font-size-route-number', fontSizes.routeNumber + 'px');
        root.style.setProperty('--font-size-destination', fontSizes.destination + 'px');
        root.style.setProperty('--font-size-platform', fontSizes.platform + 'px');
        root.style.setProperty('--font-size-time', fontSizes.time + 'px');
        root.style.setProperty('--font-size-direction-header', fontSizes.directionHeader + 'px');
        root.style.setProperty('--font-size-stop-header', fontSizes.stopHeader + 'px');
        root.style.setProperty('--font-size-no-departures', fontSizes.noDepartures + 'px');
        root.style.setProperty('--font-size-pagination-indicator', fontSizes.paginationIndicator + 'px');
        root.style.setProperty('--font-size-countdown-text', fontSizes.countdownText + 'px');
        root.style.setProperty('--font-size-delay-amount', fontSizes.delayAmount + 'px');
        root.style.setProperty('--font-size-status-header', fontSizes.statusHeader + 'px');
        
        // Set line-height to match our calculation for better vertical space distribution
        root.style.setProperty('--line-height', lineHeight.toString());

        // Remove spurious margins from direction headers and set exact heights
        directionGroups.forEach(group => {
            const header = group.querySelector('.direction-header');
            if (header) {
                // Remove top margin (0.5rem) that creates spurious space before headers
                header.style.marginTop = '0';
                header.style.marginBottom = '0';
                // Keep minimal padding for readability
                header.style.padding = '0 0.75rem 0.25rem 0.75rem';
                // Set exact height to match calculated row height
                header.style.height = heightPerRow + 'px';
                header.style.minHeight = heightPerRow + 'px';
                header.style.maxHeight = heightPerRow + 'px';
                // Ensure flex alignment centers content vertically
                header.style.display = 'flex';
                header.style.alignItems = 'center';
                // Apply line-height to match our calculation
                header.style.lineHeight = lineHeight.toString();
            }
        });

        // Set exact heights on departure rows to eliminate extra spacing
        const departureRows = departuresEl.querySelectorAll('.departure-row');
        departureRows.forEach(row => {
            // Set exact height (not just min-height) to ensure tight fit
            row.style.height = heightPerRow + 'px';
            row.style.minHeight = heightPerRow + 'px';
            row.style.maxHeight = heightPerRow + 'px';
            // Keep minimal padding for readability (reduced from default)
            row.style.padding = '0.25rem 0 0.25rem 0.75rem';
            // Apply line-height to match our calculation for better vertical distribution
            row.style.lineHeight = lineHeight.toString();
        });

        // Remove any top margins from direction groups to eliminate spurious space
        directionGroups.forEach(group => {
            group.style.marginTop = '0';
            group.style.marginBottom = '0';
        });
    }

    // Initialize on load
    function initializeAll() {
        // Update datetime immediately when DOM is ready
        updateDateTime();
        
        if (PAGINATION_ENABLED) {
            initPagination();
        }
        // initRefreshCountdown will start the countdown automatically once initialized
        initRefreshCountdown();
        // Initialize time format toggle
        initTimeFormatToggle();
        // Initialize destination scrolling for clipped text
        initDestinationScrolling();
        // Calculate dynamic font sizes if fill_vertical_space is enabled
        if (window.DEPARTURES_CONFIG && window.DEPARTURES_CONFIG.fillVerticalSpace) {
            // Use requestAnimationFrame to ensure DOM is fully rendered
            requestAnimationFrame(() => {
                calculateFillVerticalSpace();
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeAll);
    } else {
        initializeAll();
    }

    // Handle window resize for fill_vertical_space
    let resizeTimeout;
    window.addEventListener('resize', () => {
        if (window.DEPARTURES_CONFIG && window.DEPARTURES_CONFIG.fillVerticalSpace) {
            // Debounce resize events
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => {
                calculateFillVerticalSpace();
            }, 150);
        }
    });

    // Cleanup intervals on page unload/disconnect
    window.addEventListener('beforeunload', () => {
        if (window._paginationIntervals) {
            window._paginationIntervals.forEach(interval => clearInterval(interval));
            window._paginationIntervals = [];
        }
    });

    // Also cleanup on LiveView disconnect
    // Second phx:disconnect handler for pagination cleanup
    // Note: The main phx:disconnect handler at line 1436 already sets connectionState = 'broken'
    // This handler only handles pagination-specific cleanup
    window.addEventListener('phx:disconnect', () => {
        // Clear pagination intervals
        if (window._paginationIntervals) {
            window._paginationIntervals.forEach(interval => clearInterval(interval));
            window._paginationIntervals = [];
        }
    });