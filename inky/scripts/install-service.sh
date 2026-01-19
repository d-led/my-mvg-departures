#!/bin/bash
# Installation script for systemd service (MVG Departures Inky Display)
# For Raspbian/Debian systems using systemd

set -euo pipefail

SERVICE_NAME="mvg-departures-inky"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INKY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARENT_ROOT="$(cd "${INKY_ROOT}/.." && pwd)"
SERVICE_FILE="${SCRIPT_DIR}/${SERVICE_NAME}.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "Installing ${SERVICE_NAME} as systemd service..."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script must be run as root (use sudo)" >&2
    exit 1
fi

# Get the current user (the one who ran sudo)
ACTUAL_USER="${SUDO_USER:-${USER}}"
ACTUAL_HOME=$(eval echo ~"$ACTUAL_USER")

echo "Service will run as user: ${ACTUAL_USER}"
echo "Home directory: ${ACTUAL_HOME}"
echo "Project root: ${PARENT_ROOT}"
echo ""

# Verify project structure
if [ ! -d "${PARENT_ROOT}/inky" ]; then
    echo "Error: Inky project directory not found at ${PARENT_ROOT}/inky" >&2
    exit 1
fi

if [ ! -d "${PARENT_ROOT}/.venv" ]; then
    echo "Error: Virtual environment not found at ${PARENT_ROOT}/.venv" >&2
    echo "Please run ./scripts/setup.sh first" >&2
    exit 1
fi

# Check if Python module is installed
if ! "${PARENT_ROOT}/.venv/bin/python" -c "import mvg_departures_inky" 2>/dev/null; then
    echo "Error: mvg_departures_inky module not found in virtual environment" >&2
    echo "Please run ./scripts/setup.sh first" >&2
    exit 1
fi

# Verify config file exists (my.config.toml or config.example.toml)
CONFIG_FILE="${PARENT_ROOT}/my.config.toml"
FALLBACK_CONFIG="${PARENT_ROOT}/config.example.toml"

if [ ! -f "$CONFIG_FILE" ] && [ ! -f "$FALLBACK_CONFIG" ]; then
    echo "Warning: Neither my.config.toml nor config.example.toml found" >&2
    echo "The service will fail to start without a config file" >&2
    echo "You can create my.config.toml or copy config.example.toml" >&2
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create service file with user-specific paths
echo "Creating systemd service file..."
cat > "${SYSTEMD_DIR}/${SERVICE_NAME}.service" << EOF
[Unit]
Description=MVG Departures Inky Display Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${ACTUAL_USER}
Group=${ACTUAL_USER}
WorkingDirectory=${PARENT_ROOT}/inky
Environment="PATH=${PARENT_ROOT}/.venv/bin:/usr/local/bin:/usr/bin:/bin"
# The application will automatically use my.config.toml if it exists,
# otherwise it will fall back to config.example.toml
ExecStart=${PARENT_ROOT}/.venv/bin/python -m mvg_departures_inky.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mvg-departures-inky

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
chmod 644 "${SYSTEMD_DIR}/${SERVICE_NAME}.service"

# Reload systemd
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service (start on boot)
echo "Enabling service (will start on boot)..."
systemctl enable "${SERVICE_NAME}.service"

# Start service
echo "Starting service..."
if systemctl start "${SERVICE_NAME}.service"; then
    echo ""
    echo "✓ Service installed and started successfully!"
    echo ""
    echo "Service status:"
    systemctl status "${SERVICE_NAME}.service" --no-pager -l || true
    echo ""
    echo "Useful commands:"
    echo "  View logs:        sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  Check status:     sudo systemctl status ${SERVICE_NAME}"
    echo "  Stop service:     sudo systemctl stop ${SERVICE_NAME}"
    echo "  Start service:    sudo systemctl start ${SERVICE_NAME}"
    echo "  Restart service:  sudo systemctl restart ${SERVICE_NAME}"
    echo "  Uninstall:        sudo ${SCRIPT_DIR}/uninstall-service.sh"
else
    echo ""
    echo "⚠ Service installation succeeded but failed to start"
    echo "Check logs with: sudo journalctl -u ${SERVICE_NAME} -n 50"
    exit 1
fi
