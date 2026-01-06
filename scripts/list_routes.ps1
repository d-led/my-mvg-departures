# List routes for MVG stations
# Usage: .\scripts\list_routes.ps1 "Giesing" or .\scripts\list_routes.ps1 de:09162:100

$ErrorActionPreference = "Stop"

# Get the script directory
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

# Check if venv exists
if (Test-Path "$PROJECT_ROOT\.venv") {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $MVG_CONFIG = "$PROJECT_ROOT\.venv\Scripts\mvg-config.exe"
    } else {
        $MVG_CONFIG = "$PROJECT_ROOT\.venv\bin\mvg-config"
    }
} else {
    # Try to find mvg-config in PATH
    if (Get-Command mvg-config -ErrorAction SilentlyContinue) {
        $MVG_CONFIG = "mvg-config"
    } else {
        Write-Host "Error: Virtual environment not found and mvg-config not in PATH" -ForegroundColor Red
        Write-Host "Please run: .\scripts\setup.ps1" -ForegroundColor Yellow
        exit 1
    }
}

# Check if query is provided
if ($args.Count -eq 0) {
    Write-Host "Usage: $($MyInvocation.MyCommand.Name) <station_name_or_id>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) `"Giesing`"" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) de:09162:100" -ForegroundColor Yellow
    exit 1
}

# Run the command
& $MVG_CONFIG routes $args

