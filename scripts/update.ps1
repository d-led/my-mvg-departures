# Update script for MVG Departures
# Updates all dependencies after pyproject.toml changes
# Supports: Poetry, uv, and pip (in that order of preference)

$ErrorActionPreference = "Stop"

# Find project root (where this script is located)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_ROOT

Write-Host "Updating MVG Departures dependencies..." -ForegroundColor Yellow
Write-Host ""

# Determine virtual environment path
$VENV_PATH = Join-Path $PROJECT_ROOT ".venv"

if (-not (Test-Path $VENV_PATH)) {
    Write-Host "Error: Virtual environment not found at ${VENV_PATH}" -ForegroundColor Red
    Write-Host "  Run .\scripts\setup.ps1 first to create it." -ForegroundColor Yellow
    exit 1
}

# Determine Python and pip paths (cross-platform)
if ($IsWindows -or $env:OS -eq "Windows_NT") {
    $PYTHON = Join-Path $VENV_PATH "Scripts\python.exe"
    $PIP = Join-Path $VENV_PATH "Scripts\pip.exe"
    $POETRY = Join-Path $VENV_PATH "Scripts\poetry.exe"
    $UV = Join-Path $VENV_PATH "Scripts\uv.exe"
} else {
    $PYTHON = Join-Path $VENV_PATH "bin\python"
    $PIP = Join-Path $VENV_PATH "bin\pip"
    $POETRY = Join-Path $VENV_PATH "bin\poetry"
    $UV = Join-Path $VENV_PATH "bin\uv"
}

if (-not (Test-Path $PYTHON)) {
    Write-Host "Error: Could not find Python in virtual environment" -ForegroundColor Red
    exit 1
}

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $PYTHON -m pip install --upgrade pip --quiet 2>$null
Write-Host "✓ pip upgraded." -ForegroundColor Green
Write-Host ""

# Try to update using available package managers
$UPDATE_SUCCESS = $false

# Try Poetry first (if poetry.lock exists)
$poetryLockPath = Join-Path $PROJECT_ROOT "poetry.lock"
if ((Test-Path $poetryLockPath) -and (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Host "Using Poetry to update dependencies..." -ForegroundColor Yellow
    poetry update --with dev 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) {
        $UPDATE_SUCCESS = $true
        Write-Host "✓ Dependencies updated with Poetry." -ForegroundColor Green
    } else {
        Write-Host "Warning: Poetry update failed, trying alternatives..." -ForegroundColor Yellow
    }
}

# Try uv if Poetry didn't work
if (-not $UPDATE_SUCCESS) {
    $UV_AVAILABLE = $false
    
    if (Test-Path $UV) {
        $UV_AVAILABLE = $true
        Write-Host "Using uv from virtual environment..." -ForegroundColor Yellow
    } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        $UV_AVAILABLE = $true
        $UV = "uv"
        Write-Host "Using system uv..." -ForegroundColor Yellow
    } else {
        Write-Host "Installing uv..." -ForegroundColor Yellow
        & $PYTHON -m pip install uv --quiet 2>$null
        if ($LASTEXITCODE -eq 0) {
            $UV_AVAILABLE = $true
            Write-Host "✓ uv installed." -ForegroundColor Green
        }
    }
    
    if ($UV_AVAILABLE) {
        Write-Host "Updating dependencies with uv..." -ForegroundColor Yellow
        if (Test-Path $UV) {
            & $UV pip install -e ".[dev]" --upgrade 2>&1 | Out-Host
            if ($LASTEXITCODE -eq 0) {
                $UPDATE_SUCCESS = $true
                Write-Host "✓ Dependencies updated with uv." -ForegroundColor Green
            }
        } else {
            & $UV pip install -e ".[dev]" --upgrade 2>&1 | Out-Host
            if ($LASTEXITCODE -eq 0) {
                $UPDATE_SUCCESS = $true
                Write-Host "✓ Dependencies updated with uv." -ForegroundColor Green
            }
        }
    }
}

# Fall back to pip
if (-not $UPDATE_SUCCESS) {
    Write-Host "Using pip to update dependencies..." -ForegroundColor Yellow
    & $PIP install -e ".[dev]" --upgrade 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) {
        $UPDATE_SUCCESS = $true
        Write-Host "✓ Dependencies updated with pip." -ForegroundColor Green
    } else {
        Write-Host "Error: Failed to update dependencies" -ForegroundColor Red
        exit 1
    }
}

Write-Host ""
Write-Host "✓ Update complete!" -ForegroundColor Green
Write-Host ""

