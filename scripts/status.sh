#!/bin/bash
# Check status of MVG Departures application
# Works from any directory

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/deploy-common.sh"

get_app_paths

mode=$(detect_mode)

echo "Mode: $mode"
echo ""

if is_running; then
    pid=$(get_pid)
    echo "Status: RUNNING"
    echo "PID: $pid"
    
    # Show process info
    if command -v ps &> /dev/null; then
        echo ""
        echo "Process info:"
        ps -p "$pid" -o pid,ppid,user,%cpu,%mem,etime,cmd 2>/dev/null || true
    fi
    
    # Show log tail if available
    if [ -f "$LOGFILE" ]; then
        echo ""
        echo "Recent log entries:"
        tail -5 "$LOGFILE" 2>/dev/null || true
    fi
    
    exit 0
else
    echo "Status: STOPPED"
    
    # Check for stale PID file
    if [ -f "$PIDFILE" ]; then
        echo "Warning: Stale PID file found at $PIDFILE"
    fi
    
    exit 1
fi

