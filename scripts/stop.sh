#!/bin/bash
# Stop MVG Departures application
# Works from any directory

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/deploy-common.sh"

# Check if running
if ! is_running; then
    echo "${APP_NAME} is not running"
    exit 0
fi

pid=$(get_pid)
mode=$(detect_mode)

if [ "$mode" = "service" ] && [ "$EUID" -ne 0 ]; then
    echo "Service mode requires root privileges. Use: sudo $0"
    exit 1
fi

echo "Stopping ${APP_NAME} (PID: $pid)..."

# Try graceful shutdown first
kill "$pid" 2>/dev/null || true

# Wait for process to stop
count=0
while [ $count -lt 10 ]; do
    if ! kill -0 "$pid" 2>/dev/null; then
        break
    fi
    sleep 1
    count=$((count + 1))
done

# Force kill if still running
if kill -0 "$pid" 2>/dev/null; then
    echo "Force killing ${APP_NAME}..."
    kill -9 "$pid" 2>/dev/null || true
    sleep 1
fi

# Clean up PID file
rm -f "$PIDFILE"

# Verify stopped
if kill -0 "$pid" 2>/dev/null; then
    echo "Warning: Process may still be running"
    exit 1
else
    echo "${APP_NAME} stopped"
    exit 0
fi

