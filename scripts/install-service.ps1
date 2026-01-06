# Installation script for init.d service
# Note: This script is designed for Linux/Unix systems. On Windows, use Windows Service Manager instead.

$ErrorActionPreference = "Stop"

$APP_NAME = "mvg-departures"
$APP_DIR = "/opt/${APP_NAME}"
$SERVICE_FILE = "scripts\${APP_NAME}.initd"
$INITD_FILE = "/etc/init.d/${APP_NAME}"

Write-Host "Installing ${APP_NAME} as init.d service..."

# Check if running as root
$isAdmin = $false
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} else {
    $isAdmin = ($env:USER -eq "root") -or ([int](id -u) -eq 0)
}

if (-not $isAdmin) {
    Write-Host "Please run as root (use sudo)" -ForegroundColor Red
    exit 1
}

# Create app directory
New-Item -ItemType Directory -Path $APP_DIR -Force | Out-Null

# Copy files to app directory
Write-Host "Copying application files..."
Copy-Item -Path "src" -Destination $APP_DIR -Recurse -Force
Copy-Item -Path "pyproject.toml" -Destination $APP_DIR -Force
$envExamplePath = ".env.example"
if (Test-Path $envExamplePath) {
    Copy-Item -Path $envExamplePath -Destination (Join-Path $APP_DIR ".env")
}

# Create app user if it doesn't exist (Unix only)
if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    try {
        $userExists = id $APP_NAME 2>$null
    } catch {
        Write-Host "Creating user ${APP_NAME}..."
        # Note: This requires appropriate permissions
        Write-Host "Please run manually: useradd -r -s /bin/bash -d $APP_DIR $APP_NAME" -ForegroundColor Yellow
    }
}

# Set up virtual environment
Write-Host "Setting up virtual environment..."
Set-Location $APP_DIR
if (-not (Test-Path ".venv")) {
    # Try to find the best Python version available
    $pythonCmd = $null
    if (Get-Command python3.12 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3.12"
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } else {
        Write-Host "Error: Python not found. Please install Python 3.12 or later." -ForegroundColor Red
        exit 1
    }
    & $pythonCmd -m venv .venv
}

& ".venv\bin\pip" install --upgrade pip
& ".venv\bin\pip" install -e .

# Install service script (Unix only)
if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    Write-Host "Installing service script..."
    $initdSource = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "${APP_NAME}.initd"
    Copy-Item -Path $initdSource -Destination $INITD_FILE -Force
    chmod +x $INITD_FILE
    
    # Set ownership
    chown -R "${APP_NAME}:${APP_NAME}" $APP_DIR
    
    # Update rc.d
    if (Get-Command update-rc.d -ErrorAction SilentlyContinue) {
        & update-rc.d $APP_NAME defaults
    } elseif (Get-Command chkconfig -ErrorAction SilentlyContinue) {
        & chkconfig --add $APP_NAME
    }
} else {
    Write-Host "Note: On Windows, you'll need to install as a Windows Service manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Installation complete!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit ${APP_DIR}/.env to configure your stops"
Write-Host "2. Start the service: sudo service ${APP_NAME} start"
Write-Host "3. Check status: sudo service ${APP_NAME} status"
Write-Host "4. View logs: Get-Content /var/log/${APP_NAME}.log -Tail 50 -Wait"

