#!/bin/bash
# Install MVG Departures as a system service
# Works from any directory

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/deploy-common.sh"

echo "Installing ${APP_NAME} as system service..."
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root (use sudo)"
    exit 1
fi

# Create app directory
echo "Creating application directory..."
mkdir -p "$APP_DIR"

# Copy application files
echo "Copying application files..."
cp -r "${PROJECT_ROOT}/src" "$APP_DIR/" 2>/dev/null || {
    echo "Error: Could not find src directory. Make sure you're running from the project root."
    exit 1
}
cp "${PROJECT_ROOT}/pyproject.toml" "$APP_DIR/" 2>/dev/null || {
    echo "Warning: Could not find pyproject.toml"
}

# Copy configuration files
if [ -f "${PROJECT_ROOT}/env.example" ]; then
    if [ ! -f "${APP_DIR}/.env" ]; then
        cp "${PROJECT_ROOT}/env.example" "${APP_DIR}/.env"
        echo "Created ${APP_DIR}/.env from env.example"
        echo "  Please edit ${APP_DIR}/.env to configure your stops"
    else
        echo "  ${APP_DIR}/.env already exists, skipping"
    fi
fi

if [ -f "${PROJECT_ROOT}/config.example.toml" ]; then
    if [ ! -f "${APP_DIR}/config.toml" ]; then
        cp "${PROJECT_ROOT}/config.example.toml" "${APP_DIR}/config.toml"
        echo "Created ${APP_DIR}/config.toml from config.example.toml"
    fi
fi

# Create app user if it doesn't exist
if ! id "$APP_USER" &>/dev/null; then
    echo "Creating user ${APP_USER}..."
    useradd -r -s /bin/bash -d "$APP_DIR" "$APP_USER" 2>/dev/null || {
        echo "Warning: Could not create user ${APP_USER}"
    }
fi

# Set up virtual environment
echo "Setting up virtual environment..."
cd "$APP_DIR"
if [ ! -d ".venv" ]; then
    python3.12 -m venv .venv || python3 -m venv .venv || {
        echo "Error: Could not create virtual environment"
        exit 1
    }
fi

echo "Installing dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -e . --quiet

# Install service script
echo "Installing service script..."
INITD_FILE="/etc/init.d/${APP_NAME}"
cp "${SCRIPT_DIR}/mvg-departures.initd" "$INITD_FILE"
chmod +x "$INITD_FILE"

# Set ownership
echo "Setting file ownership..."
chown -R "${APP_USER}:${APP_USER}" "$APP_DIR" 2>/dev/null || {
    echo "Warning: Could not set ownership to ${APP_USER}"
}

# Update rc.d (systemd or init.d)
echo "Registering service..."
if systemctl &>/dev/null; then
    # Systemd
    SYSTEMD_FILE="/etc/systemd/system/${APP_NAME}.service"
    cat > "$SYSTEMD_FILE" <<EOF
[Unit]
Description=MVG Departures Display Service
After=network.target

[Service]
Type=forking
User=${APP_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${INITD_FILE} start
ExecStop=${INITD_FILE} stop
ExecReload=${INITD_FILE} restart
PIDFile=${PIDFILE}
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF
    systemctl daemon-reload
    systemctl enable "${APP_NAME}.service"
    echo "  Installed as systemd service"
elif command -v update-rc.d &> /dev/null; then
    update-rc.d "$APP_NAME" defaults
    echo "  Installed as init.d service (Debian/Ubuntu)"
elif command -v chkconfig &> /dev/null; then
    chkconfig --add "$APP_NAME"
    echo "  Installed as init.d service (RedHat/CentOS)"
else
    echo "  Warning: Could not register service (manual registration may be needed)"
fi

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit ${APP_DIR}/.env or ${APP_DIR}/config.toml to configure your stops"
echo "2. Start the service:"
echo "   sudo ${SCRIPT_DIR}/start.sh"
echo "   or: sudo service ${APP_NAME} start"
echo "   or: sudo systemctl start ${APP_NAME}"
echo "3. Check status:"
echo "   ${SCRIPT_DIR}/status.sh"
echo "   or: sudo service ${APP_NAME} status"
echo "4. View logs:"
echo "   tail -f ${LOGFILE}"


