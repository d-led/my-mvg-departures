// Verify CSRF token exists
const csrfMeta = document.querySelector("meta[name='csrf-token']");
if (!csrfMeta) {
  // console.error('CSRF token meta tag not found!');
} else {
  // console.log('CSRF token found:', csrfMeta.getAttribute('content'));
}

// Verify data-phx-main exists
const phxMain = document.querySelector("[data-phx-main]");
if (!phxMain) {
  // console.error('data-phx-main element not found!');
} else {
  // console.log('data-phx-main element found');
}

// Intercept WebSocket connections to fix undefined referer
// PyView's app.js sets _live_referer from document.referrer, which can be undefined
// We need to ensure it's always a valid value
const originalWebSocket = window.WebSocket;
window.WebSocket = function (url, protocols) {
  // Fix undefined referer in WebSocket URL
  if (typeof url === "string" && url.includes("_live_referer=undefined")) {
    // Replace undefined referer with current page URL
    const currentUrl = window.location.href;
    url = url.replace("_live_referer=undefined", "_live_referer=" + encodeURIComponent(currentUrl));
  }
  return new originalWebSocket(url, protocols);
};
// Copy static properties
Object.setPrototypeOf(window.WebSocket, originalWebSocket);
Object.setPrototypeOf(window.WebSocket.prototype, originalWebSocket.prototype);

// Load pyview client JS
const script = document.createElement("script");
script.src = "/static/assets/app.js";
script.onerror = function () {
  // console.error('Failed to load /static/assets/app.js');
};
script.onload = function () {
  // console.log('app.js loaded successfully');
  // Configure LiveSocket timeout settings and hooks after it's loaded
  // PyView creates LiveSocket automatically, so we configure it after creation
  function configureLiveSocket() {
    if (window.liveSocket) {
      // Get the underlying Phoenix Socket
      const socket = window.liveSocket.getSocket ? window.liveSocket.getSocket() : null;

      if (socket) {
        // Hook into WebSocket close event for immediate feedback
        // This fires when the WebSocket actually closes (server stops, network issue, etc.)
        // We set connection to 'unstable' (orange) on close, then 'broken' (red) on phx:disconnect
        socket.onClose((event) => {
          // WebSocket closed - set to unstable (orange) immediately
          // phx:disconnect should fire next and set it to broken (red)
          if (connectionState !== "broken") {
            connectionState = "unstable";
            updateConnectionStatus();

            // Fallback: if phx:disconnect doesn't fire within 3 seconds, set to broken
            // This handles cases where PyView doesn't fire phx:disconnect immediately
            const closeTimeout = setTimeout(() => {
              // Check if WebSocket is still closed and we're still unstable
              if (connectionState === "unstable") {
                // Verify WebSocket is actually closed (not OPEN = 1)
                const wsState = socket.conn ? socket.conn.readyState : null;
                if (wsState !== null && wsState !== 1) {
                  // Not OPEN
                  connectionState = "broken";
                  updateConnectionStatus();
                } else if (wsState === null) {
                  // No connection object - definitely broken
                  connectionState = "broken";
                  updateConnectionStatus();
                }
              }
            }, 3000); // Wait 3 seconds for phx:disconnect, then force broken

            // Store timeout ID so phx:disconnect can clear it if it fires
            window._closeTimeout = closeTimeout;
          }
        });
      }
    }
  }

  // Try to configure immediately
  configureLiveSocket();

  // Also try after a short delay in case LiveSocket isn't ready yet
  setTimeout(configureLiveSocket, 100);

  // Connection status will be updated via phx:open/phx:disconnect/phx:close events
  // Don't interfere with PyView's connection management
};
document.body.appendChild(script);
