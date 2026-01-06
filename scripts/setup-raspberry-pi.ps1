# Setup script for Raspberry Pi deployment
# Run this script on the Raspberry Pi after transferring the project files
# Note: This script is designed for Linux/Unix systems (Raspberry Pi). On Windows, use setup.ps1 instead.

$ErrorActionPreference = "Stop"

$APP_NAME = "mvg-departures"
$APP_DIR = "/opt/${APP_NAME}"
$APP_USER = "${APP_NAME}"
$VENV_DIR = "${APP_DIR}/.venv"
$PIDFILE = "/var/run/${APP_NAME}.pid"
$LOGFILE = "/var/log/${APP_NAME}.log"
$SERVICE_FILE = "/etc/systemd/system/${APP_NAME}.service"

Write-Host "=========================================="
Write-Host "Setting up ${APP_NAME} on Raspberry Pi"
Write-Host "=========================================="
Write-Host ""

# Check if running as root
$isAdmin = $false
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} else {
    $isAdmin = ($env:USER -eq "root") -or ([int](id -u) -eq 0)
}

if (-not $isAdmin) {
    Write-Host "This script must be run as root (use sudo)" -ForegroundColor Red
    exit 1
}

# Detect project root (assumes script is run from project directory or script is in project)
if (Test-Path "pyproject.toml") {
    $PROJECT_ROOT = (Get-Location).Path
} elseif (Test-Path "..\pyproject.toml") {
    $PROJECT_ROOT = (Resolve-Path "..").Path
} else {
    Write-Host "Error: Could not find project root. Please run from project directory." -ForegroundColor Red
    exit 1
}

Write-Host "Project root: ${PROJECT_ROOT}"

# Create app directory
Write-Host "Creating application directory at ${APP_DIR}..."
New-Item -ItemType Directory -Path $APP_DIR -Force | Out-Null

# Copy application files
Write-Host "Copying application files..."
$srcPath = Join-Path $PROJECT_ROOT "src"
Copy-Item -Path $srcPath -Destination $APP_DIR -Recurse -Force
$pyprojectPath = Join-Path $PROJECT_ROOT "pyproject.toml"
Copy-Item -Path $pyprojectPath -Destination $APP_DIR -Force

# Copy README.md (required by pyproject.toml)
$readmePath = Join-Path $PROJECT_ROOT "README.md"
if (Test-Path $readmePath) {
    Copy-Item -Path $readmePath -Destination $APP_DIR
    Write-Host "Copied README.md"
} else {
    Write-Host "Warning: README.md not found, package installation may fail" -ForegroundColor Yellow
}

# Copy my.config.toml as config.toml
$myConfigPath = Join-Path $PROJECT_ROOT "my.config.toml"
if (Test-Path $myConfigPath) {
    Copy-Item -Path $myConfigPath -Destination (Join-Path $APP_DIR "config.toml")
    Write-Host "Copied my.config.toml to ${APP_DIR}/config.toml"
} else {
    Write-Host "Warning: my.config.toml not found in ${PROJECT_ROOT}" -ForegroundColor Yellow
    Write-Host "Looking for config files..."
    # Try to find it in common locations
    $parentConfigPath = Join-Path (Split-Path -Parent $PROJECT_ROOT) "my.config.toml"
    if (Test-Path $parentConfigPath) {
        Copy-Item -Path $parentConfigPath -Destination (Join-Path $APP_DIR "config.toml")
        Write-Host "Found and copied my.config.toml from parent directory"
    } else {
        $exampleConfigPath = Join-Path $PROJECT_ROOT "config.example.toml"
        if (Test-Path $exampleConfigPath) {
            Copy-Item -Path $exampleConfigPath -Destination (Join-Path $APP_DIR "config.toml")
            Write-Host "Using config.example.toml as fallback"
        } else {
            Write-Host "Error: No config file found. Please ensure my.config.toml exists in the project root." -ForegroundColor Red
            exit 1
        }
    }
}

# Create app user if it doesn't exist (Unix only)
if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    try {
        $userExists = id $APP_USER 2>$null
        Write-Host "User ${APP_USER} already exists"
    } catch {
        Write-Host "Creating user ${APP_NAME}..."
        # Note: This requires appropriate permissions
        Write-Host "Please run manually: useradd -r -s /bin/bash -d $APP_DIR $APP_USER" -ForegroundColor Yellow
    }
}

# Set up virtual environment
Write-Host "Setting up Python virtual environment..."
Set-Location $APP_DIR

# Check Python version
$PYTHON_CMD = "python3"
if (Get-Command python3.12 -ErrorAction SilentlyContinue) {
    $PYTHON_CMD = "python3.12"
} elseif (Get-Command python3.11 -ErrorAction SilentlyContinue) {
    $PYTHON_CMD = "python3.11"
}

Write-Host "Using Python: $(& $PYTHON_CMD --version)"

if (-not (Test-Path ".venv")) {
    & $PYTHON_CMD -m venv .venv
    Write-Host "Created virtual environment"
} else {
    Write-Host "Virtual environment already exists"
}

Write-Host "Installing dependencies..."
& "${VENV_DIR}/bin/pip" install --upgrade pip --quiet
& "${VENV_DIR}/bin/pip" install -e . --quiet

# Create .env file with necessary environment variables
Write-Host "Creating .env file..."
$envContent = @"
# Server configuration - bind to all interfaces
HOST=0.0.0.0
PORT=8000

# Configuration file
CONFIG_FILE=${APP_DIR}/config.toml
"@
Set-Content -Path (Join-Path $APP_DIR ".env") -Value $envContent

# Set ownership (Unix only)
if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    Write-Host "Setting file ownership..."
    chown -R "${APP_USER}:${APP_USER}" $APP_DIR
}

# Create systemd service file
Write-Host "Creating systemd service..."
$serviceContent = @"
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
"@
Set-Content -Path $SERVICE_FILE -Value $serviceContent

# Reload systemd and enable service
Write-Host "Enabling systemd service..."
systemctl daemon-reload
systemctl enable "${APP_NAME}.service"

# Configure firewall (ufw)
Write-Host "Configuring firewall..."
if (Get-Command ufw -ErrorAction SilentlyContinue) {
    $ufwStatus = ufw status
    if ($ufwStatus -match "Status: active") {
        Write-Host "Opening port 8000 in firewall..."
        ufw allow 8000/tcp
        Write-Host "Firewall rule added"
    } else {
        Write-Host "UFW is not active, skipping firewall configuration"
    }
} elseif (Get-Command firewall-cmd -ErrorAction SilentlyContinue) {
    Write-Host "Opening port 8000 in firewalld..."
    firewall-cmd --permanent --add-port=8000/tcp
    firewall-cmd --reload
    Write-Host "Firewall rule added"
} else {
    Write-Host "No firewall detected (ufw or firewalld), please configure manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Installation complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Configuration:"
Write-Host "  Config file: ${APP_DIR}/config.toml"
Write-Host "  Environment: ${APP_DIR}/.env"
Write-Host "  Logs: journalctl -u ${APP_NAME} -f"
Write-Host ""
Write-Host "Service management:"
Write-Host "  Start:   sudo systemctl start ${APP_NAME}"
Write-Host "  Stop:    sudo systemctl stop ${APP_NAME}"
Write-Host "  Restart: sudo systemctl restart ${APP_NAME}"
Write-Host "  Status:  sudo systemctl status ${APP_NAME}"
Write-Host "  Logs:    sudo journalctl -u ${APP_NAME} -f"
Write-Host ""
Write-Host "The service is enabled and will start automatically on boot."
Write-Host "To start it now, run: sudo systemctl start ${APP_NAME}"
Write-Host ""

