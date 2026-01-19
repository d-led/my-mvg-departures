#!/bin/bash
# Deployment script for MVG Departures Inky Display on Raspberry Pi
# This script sets up everything needed to run the inky display on a Raspberry Pi
#
# Usage:
#   1. Transfer the project to your Raspberry Pi
#   2. Run: cd /path/to/project/inky && sudo ./scripts/deploy-rpi.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INKY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARENT_ROOT="$(cd "${INKY_ROOT}/.." && pwd)"

echo "=========================================="
echo "MVG Departures Inky Display - RPi Deployment"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# Get the actual user (who ran sudo)
ACTUAL_USER="${SUDO_USER:-${USER}}"
ACTUAL_HOME=$(eval echo ~"$ACTUAL_USER")

echo "Deploying for user: ${ACTUAL_USER}"
echo "Project root: ${PARENT_ROOT}"
echo ""

# Step 1: Setup (as the actual user, not root)
echo "Step 1: Setting up project dependencies..."
echo "  (This will run as user ${ACTUAL_USER})"
echo ""

# Switch to the actual user to run setup
sudo -u "$ACTUAL_USER" bash <<EOF
cd "$PARENT_ROOT"
if [ -d "inky" ] && [ -f "inky/pyproject.toml" ]; then
    cd inky
    echo "Running inky setup script..."
    ./scripts/setup.sh
else
    echo "Error: Could not find inky project directory"
    exit 1
fi
EOF

if [ $? -ne 0 ]; then
    echo "Error: Setup failed. Please check the output above."
    exit 1
fi

echo ""
echo "✓ Setup complete!"
echo ""

# Step 2: Install systemd service
echo "Step 2: Installing systemd service..."
"${SCRIPT_DIR}/install-service.sh"

echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "The service has been installed and should be running."
echo ""
echo "Useful commands:"
echo "  View logs:        sudo journalctl -u mvg-departures-inky -f"
echo "  Check status:     sudo systemctl status mvg-departures-inky"
echo "  Stop service:    sudo systemctl stop mvg-departures-inky"
echo "  Start service:   sudo systemctl start mvg-departures-inky"
echo "  Restart service: sudo systemctl restart mvg-departures-inky"
echo ""
