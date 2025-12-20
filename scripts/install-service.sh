#!/bin/bash
# Installation script for init.d service

set -e

APP_NAME="mvg-departures"
APP_DIR="/opt/${APP_NAME}"
SERVICE_FILE="scripts/${APP_NAME}.initd"
INITD_FILE="/etc/init.d/${APP_NAME}"

echo "Installing ${APP_NAME} as init.d service..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Create app directory
mkdir -p "$APP_DIR"

# Copy files to app directory
echo "Copying application files..."
cp -r src "$APP_DIR/"
cp pyproject.toml "$APP_DIR/"
cp .env.example "$APP_DIR/.env"

# Create app user if it doesn't exist
if ! id "$APP_NAME" &>/dev/null; then
    echo "Creating user ${APP_NAME}..."
    useradd -r -s /bin/bash -d "$APP_DIR" "$APP_NAME"
fi

# Set up virtual environment
echo "Setting up virtual environment..."
cd "$APP_DIR"
if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv
fi

.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .

# Install service script
echo "Installing service script..."
cp "$(dirname "$0")/${APP_NAME}.initd" "$INITD_FILE"
chmod +x "$INITD_FILE"

# Set ownership
chown -R "${APP_NAME}:${APP_NAME}" "$APP_DIR"

# Update rc.d
if command -v update-rc.d &> /dev/null; then
    update-rc.d "$APP_NAME" defaults
elif command -v chkconfig &> /dev/null; then
    chkconfig --add "$APP_NAME"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit ${APP_DIR}/.env to configure your stops"
echo "2. Start the service: sudo service ${APP_NAME} start"
echo "3. Check status: sudo service ${APP_NAME} status"
echo "4. View logs: tail -f /var/log/${APP_NAME}.log"


