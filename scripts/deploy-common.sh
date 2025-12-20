#!/bin/bash
# Common functions for deployment scripts
# This file is sourced by other deployment scripts

# Find the project root directory (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Application configuration
APP_NAME="mvg-departures"
APP_DIR="/opt/${APP_NAME}"
VENV_DIR="${APP_DIR}/.venv"
PIDFILE="/var/run/${APP_NAME}.pid"
LOGFILE="/var/log/${APP_NAME}.log"
APP_USER="${APP_NAME}"

# Detect if running as installed service or development mode
detect_mode() {
    if [ -d "$APP_DIR" ] && [ -f "${VENV_DIR}/bin/mvg-departures" ]; then
        echo "service"
    else
        echo "dev"
    fi
}

# Get the Python executable and app script
get_app_paths() {
    local mode=$(detect_mode)
    
    if [ "$mode" = "service" ]; then
        PYTHON="${VENV_DIR}/bin/python"
        APP_SCRIPT="${VENV_DIR}/bin/mvg-departures"
        WORK_DIR="$APP_DIR"
    else
        # Development mode - use project's venv or system python
        if [ -d "${PROJECT_ROOT}/.venv" ]; then
            PYTHON="${PROJECT_ROOT}/.venv/bin/python"
        elif [ -d "${PROJECT_ROOT}/venv" ]; then
            PYTHON="${PROJECT_ROOT}/venv/bin/python"
        else
            PYTHON="python3"
        fi
        APP_SCRIPT="${PYTHON} -m mvg_departures.main"
        WORK_DIR="$PROJECT_ROOT"
    fi
    
    export PYTHON APP_SCRIPT WORK_DIR
}

# Check if application is running
is_running() {
    if [ -f "$PIDFILE" ]; then
        local pid=$(cat "$PIDFILE" 2>/dev/null)
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            return 0
        else
            # Stale PID file
            rm -f "$PIDFILE"
        fi
    fi
    return 1
}

# Get process PID (from PID file or by name)
get_pid() {
    if [ -f "$PIDFILE" ]; then
        cat "$PIDFILE"
    else
        pgrep -f "mvg_departures.main" | head -1
    fi
}


