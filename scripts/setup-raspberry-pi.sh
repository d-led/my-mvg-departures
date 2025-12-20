#!/bin/bash
# Setup script for Raspberry Pi deployment
# Run this script on the Raspberry Pi after transferring the project files

set -e

APP_NAME="mvg-departures"
APP_DIR="/opt/${APP_NAME}"
APP_USER="${APP_NAME}"
VENV_DIR="${APP_DIR}/.venv"
PIDFILE="/var/run/${APP_NAME}.pid"
LOGFILE="/var/log/${APP_NAME}.log"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

echo "=========================================="
echo "Setting up ${APP_NAME} on Raspberry Pi"
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

# Create app directory
echo "Creating application directory at ${APP_DIR}..."
mkdir -p "$APP_DIR"

# Copy application files
echo "Copying application files..."
cp -r "${PROJECT_ROOT}/src" "$APP_DIR/"
cp "${PROJECT_ROOT}/pyproject.toml" "$APP_DIR/"

# Copy my.config.toml as config.toml
if [ -f "${PROJECT_ROOT}/my.config.toml" ]; then
    cp "${PROJECT_ROOT}/my.config.toml" "${APP_DIR}/config.toml"
    echo "Copied my.config.toml to ${APP_DIR}/config.toml"
else
    echo "Warning: my.config.toml not found, using config.example.toml if available"
    if [ -f "${PROJECT_ROOT}/config.example.toml" ]; then
        cp "${PROJECT_ROOT}/config.example.toml" "${APP_DIR}/config.toml"
    fi
fi

# Create app user if it doesn't exist
if ! id "$APP_USER" &>/dev/null; then
    echo "Creating user ${APP_USER}..."
    useradd -r -s /bin/bash -d "$APP_DIR" "$APP_USER"
else
    echo "User ${APP_USER} already exists"
fi

# Set up virtual environment
echo "Setting up Python virtual environment..."
cd "$APP_DIR"

# Check Python version
PYTHON_CMD="python3"
if command -v python3.12 &>/dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3.11 &>/dev/null; then
    PYTHON_CMD="python3.11"
fi

echo "Using Python: $(${PYTHON_CMD} --version)"

if [ ! -d ".venv" ]; then
    ${PYTHON_CMD} -m venv .venv
    echo "Created virtual environment"
else
    echo "Virtual environment already exists"
fi

echo "Installing dependencies..."
"${VENV_DIR}/bin/pip" install --upgrade pip --quiet
"${VENV_DIR}/bin/pip" install -e . --quiet

# Create .env file with necessary environment variables
echo "Creating .env file..."
cat > "${APP_DIR}/.env" <<EOF
# Server configuration - bind to all interfaces
HOST=0.0.0.0
PORT=8000

# Configuration file
CONFIG_FILE=${APP_DIR}/config.toml
EOF

# Set ownership
echo "Setting file ownership..."
chown -R "${APP_USER}:${APP_USER}" "$APP_DIR"

# Create systemd service file
echo "Creating systemd service..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=MVG Departures Display Service
After=network.target

[Service]
Type=simple
User=${APP_USER}
Group=${APP_USER}
WorkingDirectory=${APP_DIR}
Environment="PATH=${VENV_DIR}/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=${APP_DIR}/.env
ExecStart=${VENV_DIR}/bin/python -m mvg_departures.main
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${APP_NAME}

[Install]
WantedBy=multi-user.target
EOF

# Reload systemd and enable service
echo "Enabling systemd service..."
systemctl daemon-reload
systemctl enable "${APP_NAME}.service"

# Configure firewall (ufw)
echo "Configuring firewall..."
if command -v ufw &>/dev/null; then
    if ufw status | grep -q "Status: active"; then
        echo "Opening port 8000 in firewall..."
        ufw allow 8000/tcp
        echo "Firewall rule added"
    else
        echo "UFW is not active, skipping firewall configuration"
    fi
elif command -v firewall-cmd &>/dev/null; then
    echo "Opening port 8000 in firewalld..."
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --reload
    echo "Firewall rule added"
else
    echo "No firewall detected (ufw or firewalld), please configure manually"
fi

echo ""
echo "=========================================="
echo "Installation complete!"
echo "=========================================="
echo ""
echo "Configuration:"
echo "  Config file: ${APP_DIR}/config.toml"
echo "  Environment: ${APP_DIR}/.env"
echo "  Logs: journalctl -u ${APP_NAME} -f"
echo ""
echo "Service management:"
echo "  Start:   sudo systemctl start ${APP_NAME}"
echo "  Stop:    sudo systemctl stop ${APP_NAME}"
echo "  Restart: sudo systemctl restart ${APP_NAME}"
echo "  Status:  sudo systemctl status ${APP_NAME}"
echo "  Logs:    sudo journalctl -u ${APP_NAME} -f"
echo ""
echo "The service is enabled and will start automatically on boot."
echo "To start it now, run: sudo systemctl start ${APP_NAME}"
echo ""

