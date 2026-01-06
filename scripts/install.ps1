# Install MVG Departures as a system service
# Works from any directory
# Note: This script is designed for Linux/Unix systems. On Windows, use Windows Service Manager instead.

$ErrorActionPreference = "Stop"

# Source common functions
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
. "${SCRIPT_DIR}\deploy-common.ps1"

Write-Host "Installing ${APP_NAME} as system service..."
Write-Host ""

# Check if running as administrator (on Windows) or root (on Unix)
$isAdmin = $false
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} else {
    # On Unix, check if running as root
    $isAdmin = ($env:USER -eq "root") -or ([int](id -u) -eq 0)
}

if (-not $isAdmin) {
    Write-Host "This script must be run as administrator (Windows) or root (Unix)"
    exit 1
}

# Create app directory
Write-Host "Creating application directory..."
New-Item -ItemType Directory -Path $APP_DIR -Force | Out-Null

# Copy application files
Write-Host "Copying application files..."
$srcPath = Join-Path $PROJECT_ROOT "src"
if (Test-Path $srcPath) {
    Copy-Item -Path $srcPath -Destination $APP_DIR -Recurse -Force
} else {
    Write-Host "Error: Could not find src directory. Make sure you're running from the project root." -ForegroundColor Red
    exit 1
}

$pyprojectPath = Join-Path $PROJECT_ROOT "pyproject.toml"
if (Test-Path $pyprojectPath) {
    Copy-Item -Path $pyprojectPath -Destination $APP_DIR -Force
} else {
    Write-Host "Warning: Could not find pyproject.toml" -ForegroundColor Yellow
}

# Copy configuration files
$envExamplePath = Join-Path $PROJECT_ROOT "env.example"
if (Test-Path $envExamplePath) {
    $envPath = Join-Path $APP_DIR ".env"
    if (-not (Test-Path $envPath)) {
        Copy-Item -Path $envExamplePath -Destination $envPath
        Write-Host "Created ${envPath} from env.example"
        Write-Host "  Please edit ${envPath} to configure your stops"
    } else {
        Write-Host "  ${envPath} already exists, skipping"
    }
}

$configExamplePath = Join-Path $PROJECT_ROOT "config.example.toml"
if (Test-Path $configExamplePath) {
    $configPath = Join-Path $APP_DIR "config.toml"
    if (-not (Test-Path $configPath)) {
        Copy-Item -Path $configExamplePath -Destination $configPath
        Write-Host "Created ${configPath} from config.example.toml"
    }
}

# Create app user if it doesn't exist (Unix only)
if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    try {
        $userExists = Get-LocalUser -Name $APP_USER -ErrorAction Stop
    } catch {
        Write-Host "Creating user ${APP_USER}..."
        # Note: This requires appropriate permissions and may need to be done manually
        Write-Host "Warning: User creation may need to be done manually: useradd -r -s /bin/bash -d $APP_DIR $APP_USER" -ForegroundColor Yellow
    }
}

# Set up virtual environment
Write-Host "Setting up virtual environment..."
Set-Location $APP_DIR
if (-not (Test-Path ".venv")) {
    $pythonCmd = "python3.12"
    if (-not (Get-Command $pythonCmd -ErrorAction SilentlyContinue)) {
        $pythonCmd = "python3"
    }
    & $pythonCmd -m venv .venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Could not create virtual environment" -ForegroundColor Red
        exit 1
    }
}

Write-Host "Installing dependencies..."
& "${VENV_DIR}/bin/pip" install --upgrade pip --quiet
& "${VENV_DIR}/bin/pip" install -e . --quiet

# Install service script (Unix only)
if (-not ($IsWindows -or $env:OS -eq "Windows_NT")) {
    Write-Host "Installing service script..."
    $INITD_FILE = "/etc/init.d/${APP_NAME}"
    $initdSource = Join-Path $SCRIPT_DIR "mvg-departures.initd"
    Copy-Item -Path $initdSource -Destination $INITD_FILE -Force
    # Make executable
    chmod +x $INITD_FILE
    
    # Set ownership
    Write-Host "Setting file ownership..."
    chown -R "${APP_USER}:${APP_USER}" $APP_DIR 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Warning: Could not set ownership to ${APP_USER}" -ForegroundColor Yellow
    }
    
    # Update rc.d (systemd or init.d)
    Write-Host "Registering service..."
    if (Get-Command systemctl -ErrorAction SilentlyContinue) {
        # Systemd
        $SYSTEMD_FILE = "/etc/systemd/system/${APP_NAME}.service"
        $serviceContent = @"
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
"@
        Set-Content -Path $SYSTEMD_FILE -Value $serviceContent
        systemctl daemon-reload
        systemctl enable "${APP_NAME}.service"
        Write-Host "  Installed as systemd service"
    } elseif (Get-Command update-rc.d -ErrorAction SilentlyContinue) {
        & update-rc.d $APP_NAME defaults
        Write-Host "  Installed as init.d service (Debian/Ubuntu)"
    } elseif (Get-Command chkconfig -ErrorAction SilentlyContinue) {
        & chkconfig --add $APP_NAME
        Write-Host "  Installed as init.d service (RedHat/CentOS)"
    } else {
        Write-Host "  Warning: Could not register service (manual registration may be needed)" -ForegroundColor Yellow
    }
} else {
    Write-Host "Note: On Windows, you'll need to install as a Windows Service manually" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Installation complete!"
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Edit ${APP_DIR}/.env or ${APP_DIR}/config.toml to configure your stops"
Write-Host "2. Start the service:"
Write-Host "   Start-Process powershell -Verb RunAs -ArgumentList `"${SCRIPT_DIR}\start.ps1`""
Write-Host "   or: sudo ${SCRIPT_DIR}/start.sh (on Unix)"
Write-Host "   or: sudo service ${APP_NAME} start (on Unix)"
Write-Host "   or: sudo systemctl start ${APP_NAME} (on Unix)"
Write-Host "3. Check status:"
Write-Host "   ${SCRIPT_DIR}\status.ps1"
Write-Host "   or: sudo service ${APP_NAME} status (on Unix)"
Write-Host "4. View logs:"
Write-Host "   Get-Content ${LOGFILE} -Tail 50 -Wait (on Windows)"
Write-Host "   tail -f ${LOGFILE} (on Unix)"

