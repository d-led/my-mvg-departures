# List live departures for MVG stations
# Usage: .\scripts\list_departures.ps1 "Giesing" or .\scripts\list_departures.ps1 de:09162:100
#        .\scripts\list_departures.ps1 de:09162:1108:4:4  # Filter by specific stop point

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
    Write-Host "Usage: $($MyInvocation.MyCommand.Name) <station_name_or_id> [--limit N] [--json]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) `"Donnersbergerstr.`"          # Search by name" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) de:09162:100                  # By station ID" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) de:09162:100:2:2              # By specific stop point" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) de:09162:100 --limit 50       # Limit results" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) de:09162:100 --json           # Output as JSON" -ForegroundColor Yellow
    exit 1
}

# Run the command
& $MVG_CONFIG departures $args

