# Stop MVG Departures application
# Works from any directory

$ErrorActionPreference = "Stop"

# Source common functions
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
. "${SCRIPT_DIR}\deploy-common.ps1"

# Check if running
if (-not (is_running)) {
    Write-Host "${APP_NAME} is not running"
    exit 0
}

$pid = get_pid
$mode = detect_mode

# Check if running as administrator (Windows) or root (Unix)
$isAdmin = $false
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    $isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
} else {
    $isAdmin = ($env:USER -eq "root") -or ([int](id -u) -eq 0)
}

if (($mode -eq "service") -and (-not $isAdmin)) {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        Write-Host "Service mode requires administrator privileges. Use: Start-Process powershell -Verb RunAs -ArgumentList `"$PSCommandPath`""
    } else {
        Write-Host "Service mode requires root privileges. Use: sudo $PSCommandPath"
    }
    exit 1
}

Write-Host "Stopping ${APP_NAME} (PID: $pid)..."

# Try graceful shutdown first
try {
    Stop-Process -Id $pid -ErrorAction Stop
} catch {
    # Process may already be stopped
}

# Wait for process to stop
$count = 0
while ($count -lt 10) {
    try {
        $process = Get-Process -Id $pid -ErrorAction Stop
        Start-Sleep -Seconds 1
        $count++
    } catch {
        break
    }
}

# Force kill if still running
try {
    $process = Get-Process -Id $pid -ErrorAction Stop
    Write-Host "Force killing ${APP_NAME}..."
    Stop-Process -Id $pid -Force -ErrorAction Stop
    Start-Sleep -Seconds 1
} catch {
    # Process already stopped
}

# Clean up PID file
if (Test-Path $PIDFILE) {
    Remove-Item $PIDFILE -Force
}

# Verify stopped
try {
    $process = Get-Process -Id $pid -ErrorAction Stop
    Write-Host "Warning: Process may still be running" -ForegroundColor Yellow
    exit 1
} catch {
    Write-Host "${APP_NAME} stopped"
    exit 0
}

