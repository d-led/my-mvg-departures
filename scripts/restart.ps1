# Restart MVG Departures application
# Works from any directory

$ErrorActionPreference = "Stop"

# Source common functions
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
. "${SCRIPT_DIR}\deploy-common.ps1"

Write-Host "Restarting ${APP_NAME}..."

# Stop if running
if (is_running) {
    & "${SCRIPT_DIR}\stop.ps1"
    Start-Sleep -Seconds 2
}

# Start
& "${SCRIPT_DIR}\start.ps1"

