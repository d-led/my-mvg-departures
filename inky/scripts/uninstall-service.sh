#!/bin/bash
# Uninstallation script for systemd service (MVG Departures Inky Display)

set -euo pipefail

SERVICE_NAME="mvg-departures-inky"
SYSTEMD_DIR="/etc/systemd/system"
SERVICE_FILE="${SYSTEMD_DIR}/${SERVICE_NAME}.service"

echo "Uninstalling ${SERVICE_NAME} systemd service..."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)" >&2
    exit 1
fi

# Check if service exists
if [ ! -f "$SERVICE_FILE" ]; then
    echo "Service file not found: ${SERVICE_FILE}"
    echo "Service may already be uninstalled."
    exit 0
fi

# Stop service if running
if systemctl is-active --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
    echo "Stopping service..."
    systemctl stop "${SERVICE_NAME}.service"
fi

# Disable service
if systemctl is-enabled --quiet "${SERVICE_NAME}.service" 2>/dev/null; then
    echo "Disabling service..."
    systemctl disable "${SERVICE_NAME}.service"
fi

# Remove service file
echo "Removing service file..."
rm -f "$SERVICE_FILE"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload
systemctl reset-failed

echo ""
echo "✓ Service uninstalled successfully!"
echo ""
echo "Note: The application files and virtual environment were not removed."
echo "To remove them, delete the project directory manually."
