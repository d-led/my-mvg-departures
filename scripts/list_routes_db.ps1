# List routes for DB stations
# Usage: .\scripts\list_routes_db.ps1 "Augsburg Hbf" or .\scripts\list_routes_db.ps1 8000013

$ErrorActionPreference = "Stop"

# Get the script directory
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

# Check if venv exists
if (Test-Path "$PROJECT_ROOT\.venv") {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $DB_CONFIG = "$PROJECT_ROOT\.venv\Scripts\db-config.exe"
    } else {
        $DB_CONFIG = "$PROJECT_ROOT\.venv\bin\db-config"
    }
} else {
    # Try to find db-config in PATH
    if (Get-Command db-config -ErrorAction SilentlyContinue) {
        $DB_CONFIG = "db-config"
    } else {
        Write-Host "Error: Virtual environment not found and db-config not in PATH" -ForegroundColor Red
        Write-Host "Please run: .\scripts\setup.ps1" -ForegroundColor Yellow
        exit 1
    }
}

# Check if query is provided
if ($args.Count -eq 0) {
    Write-Host "Usage: $($MyInvocation.MyCommand.Name) <station_name_or_id>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) `"Augsburg Hbf`"" -ForegroundColor Yellow
    Write-Host "  $($MyInvocation.MyCommand.Name) 8000013" -ForegroundColor Yellow
    exit 1
}

# Run the command
& $DB_CONFIG routes $args

