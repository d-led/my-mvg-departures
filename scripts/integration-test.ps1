# Integration test script for MVG Departures
# Runs only integration tests that require network access
# Automatically detects and uses .venv if available

$ErrorActionPreference = "Stop"

# Get the directory where this script is located
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_ROOT

# Source common environment setup
. "$SCRIPT_DIR\common_env.ps1"

# Check if dependencies are installed
try {
    run_python_module pytest --version 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "pytest not found"
    }
} catch {
    Write-Host "Dependencies not found. Installing..."
    if (Test-Path ".venv") {
        & $PIP install -e ".[dev]"
    } else {
        Write-Host "Warning: No .venv found. Please run .\scripts\setup.ps1 first or install dependencies manually." -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "=========================================="
Write-Host "Running Integration Tests..."
Write-Host "=========================================="
Write-Host ""
Write-Host "Note: Integration tests require network access and may take longer to run."
Write-Host ""

# Run integration tests
if ($RUN_CMD) {
    & $RUN_CMD.Split(" ") pytest -m integration -v $args
} else {
    & $PYTHON -m pytest -m integration -v $args
}

Write-Host ""
Write-Host "=========================================="
Write-Host "Integration tests completed!" -ForegroundColor Green
Write-Host "=========================================="

