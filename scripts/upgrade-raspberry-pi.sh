#!/bin/bash
# Upgrade script for Raspberry Pi deployment
# Run this script on the Raspberry Pi after pulling latest changes

set -e

APP_NAME="mvg-departures"
APP_DIR="/opt/${APP_NAME}"
APP_USER="${APP_NAME}"
VENV_DIR="${APP_DIR}/.venv"

echo "=========================================="
echo "Upgrading ${APP_NAME} on Raspberry Pi"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# Detect project root (assumes script is run from project directory or script is in project)
if [ -f "pyproject.toml" ]; then
    PROJECT_ROOT="$(pwd)"
elif [ -f "../pyproject.toml" ]; then
    PROJECT_ROOT="$(cd .. && pwd)"
else
    echo "Error: Could not find project root. Please run from project directory."
    exit 1
fi

echo "Project root: ${PROJECT_ROOT}"
echo "App directory: ${APP_DIR}"

# Check if app is installed
if [ ! -d "$APP_DIR" ]; then
    echo "Error: Application not found at ${APP_DIR}"
    echo "Please run setup-raspberry-pi.sh first to install the application."
    exit 1
fi

# Stop the service
echo "Stopping ${APP_NAME} service..."
systemctl stop "${APP_NAME}.service" || echo "Service was not running"

# Backup current config
if [ -f "${APP_DIR}/config.toml" ]; then
    echo "Backing up current config..."
    cp "${APP_DIR}/config.toml" "${APP_DIR}/config.toml.backup"
fi

# Copy updated application files
echo "Copying updated application files..."
cp -r "${PROJECT_ROOT}/src" "$APP_DIR/"
cp "${PROJECT_ROOT}/pyproject.toml" "$APP_DIR/"

# Copy README.md (required by pyproject.toml)
if [ -f "${PROJECT_ROOT}/README.md" ]; then
    cp "${PROJECT_ROOT}/README.md" "$APP_DIR/"
    echo "Copied README.md"
fi

# Update config file if my.config.toml exists (but preserve existing config.toml)
if [ -f "${PROJECT_ROOT}/my.config.toml" ] && [ ! -f "${APP_DIR}/config.toml" ]; then
    cp "${PROJECT_ROOT}/my.config.toml" "${APP_DIR}/config.toml"
    echo "Copied my.config.toml to ${APP_DIR}/config.toml"
fi

# Update dependencies
echo "Updating dependencies..."
cd "$APP_DIR"
"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -e . --quiet

# Set ownership
echo "Setting file ownership..."
chown -R "${APP_USER}:${APP_USER}" "$APP_DIR"

# Reload systemd (in case service file changed)
echo "Reloading systemd..."
systemctl daemon-reload

# Start the service
echo "Starting ${APP_NAME} service..."
systemctl start "${APP_NAME}.service"

# Wait a moment and check status
sleep 2
if systemctl is-active --quiet "${APP_NAME}.service"; then
    echo "Service started successfully"
else
    echo "Warning: Service may not have started correctly"
    echo "Check status with: sudo systemctl status ${APP_NAME}"
fi

echo ""
echo "=========================================="
echo "Upgrade complete!"
echo "=========================================="
echo ""
echo "Service status:"
systemctl status "${APP_NAME}.service" --no-pager -l || true
echo ""
echo "View logs with: sudo journalctl -u ${APP_NAME} -f"
echo ""

