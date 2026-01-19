#!/bin/bash
# Restart MVG Departures Inky Display service
# Works from any directory

set -e

SERVICE_NAME="mvg-departures-inky"

# Check if running as root (required for systemctl)
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges. Use: sudo $0"
    exit 1
fi

echo "Restarting ${SERVICE_NAME}..."
systemctl restart "${SERVICE_NAME}"

# Show status
echo ""
echo "Service status:"
systemctl status "${SERVICE_NAME}" --no-pager -l || true
