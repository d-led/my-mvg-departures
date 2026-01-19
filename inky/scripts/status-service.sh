#!/bin/bash
# Check status of MVG Departures Inky Display service
# Works from any directory

set -e

SERVICE_NAME="mvg-departures-inky"

# Check if running as root (required for systemctl status)
if [ "$EUID" -ne 0 ]; then
    echo "This script requires root privileges. Use: sudo $0"
    exit 1
fi

systemctl status "${SERVICE_NAME}"
