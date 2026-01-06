# Upgrade script for Raspberry Pi deployment
# Run this script on the Raspberry Pi after pulling latest changes
# Note: This script is designed for Linux/Unix systems (Raspberry Pi).

$ErrorActionPreference = "Stop"

$APP_NAME = "mvg-departures"
$APP_DIR = "/opt/${APP_NAME}"
$APP_USER = "${APP_NAME}"
$VENV_DIR = "${APP_DIR}/.venv"

Write-Host "=========================================="
Write-Host "Upgrading ${APP_NAME} on Raspberry Pi"
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
Write-Host "App directory: ${APP_DIR}"

# Check if app is installed
if (-not (Test-Path $APP_DIR)) {
    Write-Host "Error: Application not found at ${APP_DIR}" -ForegroundColor Red
    Write-Host "Please run setup-raspberry-pi.ps1 first to install the application." -ForegroundColor Yellow
    exit 1
}

# Stop the service
Write-Host "Stopping ${APP_NAME} service..."
systemctl stop "${APP_NAME}.service" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Service was not running"
}

# Backup current config
$configPath = Join-Path $APP_DIR "config.toml"
if (Test-Path $configPath) {
    Write-Host "Backing up current config..."
    Copy-Item -Path $configPath -Destination "${configPath}.backup"
}

# Copy updated application files
Write-Host "Copying updated application files..."
$srcPath = Join-Path $PROJECT_ROOT "src"
Copy-Item -Path $srcPath -Destination $APP_DIR -Recurse -Force
$pyprojectPath = Join-Path $PROJECT_ROOT "pyproject.toml"
Copy-Item -Path $pyprojectPath -Destination $APP_DIR -Force

# Copy README.md (required by pyproject.toml)
$readmePath = Join-Path $PROJECT_ROOT "README.md"
if (Test-Path $readmePath) {
    Copy-Item -Path $readmePath -Destination $APP_DIR
    Write-Host "Copied README.md"
}

# Update config file if my.config.toml exists (but preserve existing config.toml)
$myConfigPath = Join-Path $PROJECT_ROOT "my.config.toml"
if ((Test-Path $myConfigPath) -and (-not (Test-Path $configPath))) {
    Copy-Item -Path $myConfigPath -Destination $configPath
    Write-Host "Copied my.config.toml to ${configPath}"
}

# Update dependencies
Write-Host "Updating dependencies..."
Set-Location $APP_DIR
& "${VENV_DIR}/bin/pip" install --upgrade pip --quiet
& "${VENV_DIR}/bin/pip" install -e . --quiet

# Set ownership (Unix only)
if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    Write-Host "Setting file ownership..."
    chown -R "${APP_USER}:${APP_USER}" $APP_DIR
}

# Reload systemd (in case service file changed)
Write-Host "Reloading systemd..."
systemctl daemon-reload

# Start the service
Write-Host "Starting ${APP_NAME} service..."
systemctl start "${APP_NAME}.service"

# Wait a moment and check status
Start-Sleep -Seconds 2
$isActive = systemctl is-active "${APP_NAME}.service"
if ($isActive -eq "active") {
    Write-Host "Service started successfully" -ForegroundColor Green
} else {
    Write-Host "Warning: Service may not have started correctly" -ForegroundColor Yellow
    Write-Host "Check status with: sudo systemctl status ${APP_NAME}" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Upgrade complete!"
Write-Host "=========================================="
Write-Host ""
Write-Host "Service status:"
systemctl status "${APP_NAME}.service" --no-pager -l
Write-Host ""
Write-Host "View logs with: sudo journalctl -u ${APP_NAME} -f"
Write-Host ""

