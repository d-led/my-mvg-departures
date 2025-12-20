#!/bin/bash
# Restart MVG Departures application
# Works from any directory

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/deploy-common.sh"

echo "Restarting ${APP_NAME}..."

# Stop if running
if is_running; then
    "${SCRIPT_DIR}/stop.sh"
    sleep 2
fi

# Start
"${SCRIPT_DIR}/start.sh"


