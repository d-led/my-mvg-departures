# List routes for a VBB (Berlin) station
# Usage: .\scripts\list_routes_vbb.ps1 <station_name_or_id>

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

# Determine Python and vbb-config command
if (Test-Path "$PROJECT_ROOT\.venv") {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $PYTHON = "$PROJECT_ROOT\.venv\Scripts\python.exe"
        $VBB_CONFIG = "$PROJECT_ROOT\.venv\Scripts\vbb-config.exe"
    } else {
        $PYTHON = "$PROJECT_ROOT\.venv\bin\python"
        $VBB_CONFIG = "$PROJECT_ROOT\.venv\bin\vbb-config"
    }
} else {
    $PYTHON = "python3"
    # Try to find vbb-config in PATH
    if (Get-Command vbb-config -ErrorAction SilentlyContinue) {
        $VBB_CONFIG = "vbb-config"
    } else {
        $VBB_CONFIG = ""
    }
}

# Check if query is provided
if ($args.Count -eq 0) {
    Write-Host "Usage: $($MyInvocation.MyCommand.Name) <station_name>" -ForegroundColor Yellow
    Write-Host "Example: $($MyInvocation.MyCommand.Name) `"Zoologischer Garten`"" -ForegroundColor Yellow
    exit 1
}

$QUERY = $args -join " "

# If vbb-config doesn't exist, use Python module directly
if (-not $VBB_CONFIG -or -not (Test-Path $VBB_CONFIG)) {
    # Use Python module directly (requires package to be installed or PYTHONPATH set)
    # Set PYTHONPATH to include the src directory if it's not already set
    if (-not $env:PYTHONPATH -and (Test-Path "$PROJECT_ROOT\src")) {
        $env:PYTHONPATH = "$PROJECT_ROOT\src;$env:PYTHONPATH"
    }
    & $PYTHON -m mvg_departures.cli_vbb search $QUERY
} else {
    & $VBB_CONFIG search $QUERY
}

