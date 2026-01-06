# Test script for MVG Departures
# Runs all CI checks: formatting, linting, type checking, and tests
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
Write-Host "Formatting..."
Write-Host "=========================================="
Write-Host ""

& "$SCRIPT_DIR\reformat.ps1"

# Run all CI checks
Write-Host "=========================================="
Write-Host "Running CI checks..."
Write-Host "=========================================="
Write-Host ""

# 1. Check code formatting with Black
Write-Host "1. Checking code formatting with Black..."
run_python_module black --check src tests
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Formatting check passed" -ForegroundColor Green
} else {
    Write-Host "✗ Formatting check failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 2. Lint with Ruff
Write-Host "2. Linting with Ruff..."
run_python_module ruff check src tests
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Linting passed" -ForegroundColor Green
} else {
    Write-Host "✗ Linting failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 3. Type check with mypy
Write-Host "3. Type checking with mypy..."
run_python_module mypy src
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Type checking passed" -ForegroundColor Green
} else {
    Write-Host "✗ Type checking failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 4. Run tests (excluding integration tests by default)
Write-Host "4. Running tests..."
run_python_module pytest -m "not integration" $args
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Tests passed" -ForegroundColor Green
} else {
    Write-Host "✗ Tests failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "=========================================="
Write-Host "All checks passed!" -ForegroundColor Green
Write-Host "=========================================="

