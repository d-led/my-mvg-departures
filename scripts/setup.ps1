# Setup script for MVG Departures
# Creates virtual environment and installs all dependencies
# Supports: Poetry, uv, and pip (in that order of preference)

$ErrorActionPreference = "Stop"

# Find project root (where this script is located)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_ROOT

Write-Host "Setting up MVG Departures..." -ForegroundColor Yellow
Write-Host ""

# Check Python version - On Windows, use 'python' instead of 'python3'
$PYTHON_CMD = $null
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PYTHON_CMD = "python"
} elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
    $PYTHON_CMD = "python3"
} else {
    Write-Host "Error: Python not found. Please install Python 3.12 or later from:" -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Alternatively, you can install Python using a package manager:" -ForegroundColor Yellow
    Write-Host "  - winget: winget install Python.Python.3.12" -ForegroundColor Cyan
    Write-Host "  - scoop: scoop install python" -ForegroundColor Cyan
    Write-Host "  - chocolatey: choco install python" -ForegroundColor Cyan
    exit 1
}

$getVersionScript = Join-Path $SCRIPT_DIR "get_python_version.py"
$PYTHON_VERSION = & $PYTHON_CMD $getVersionScript
if (-not $PYTHON_VERSION) {
    Write-Host "Error: Failed to get Python version." -ForegroundColor Red
    exit 1
}

$REQUIRED_VERSION = "3.12"

# Compare versions
$versionParts = $PYTHON_VERSION.Split(".")
$requiredParts = $REQUIRED_VERSION.Split(".")
$versionNum = [int]$versionParts[0] * 100 + [int]$versionParts[1]
$requiredNum = [int]$requiredParts[0] * 100 + [int]$requiredParts[1]

if ($versionNum -lt $requiredNum) {
    Write-Host "Warning: Python $PYTHON_VERSION detected. Python 3.12 or later is recommended." -ForegroundColor Yellow
    Write-Host ""
}

# Determine virtual environment path
$VENV_PATH = Join-Path $PROJECT_ROOT ".venv"

# Create virtual environment if it doesn't exist
if (-not (Test-Path $VENV_PATH)) {
    Write-Host "Creating virtual environment at ${VENV_PATH}..." -ForegroundColor Yellow
    & $PYTHON_CMD -m venv $VENV_PATH
    Write-Host "Virtual environment created." -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "Virtual environment already exists at ${VENV_PATH}" -ForegroundColor Green
    Write-Host ""
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

# Helper functions
function _check_package_installed {
    $checkScript = Join-Path $SCRIPT_DIR "check_package_installed.py"
    & $PYTHON $checkScript 2>$null
    return $LASTEXITCODE -eq 0
}

function _print_usage_info {
    Write-Host "To use the commands, either:" -ForegroundColor Yellow
    Write-Host "  1. Activate the virtual environment:" -ForegroundColor Yellow
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        Write-Host "     .venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    } else {
        Write-Host "     source .venv/bin/activate" -ForegroundColor Yellow
    }
    Write-Host "  2. Or use the full path:" -ForegroundColor Yellow
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        Write-Host "     .venv\Scripts\mvg-config search `"Station Name`"" -ForegroundColor Yellow
    } else {
        Write-Host "     .venv/bin/mvg-config search `"Station Name`"" -ForegroundColor Yellow
    }
    Write-Host ""
    Write-Host "You can now:" -ForegroundColor Yellow
    Write-Host "  - Run the application: .\scripts\start.ps1" -ForegroundColor Yellow
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        Write-Host "  - Use mvg-config: .venv\Scripts\mvg-config search `"Station Name`"" -ForegroundColor Yellow
        Write-Host "  - Run tests: .venv\Scripts\pytest" -ForegroundColor Yellow
        Write-Host "  - Run linters: .venv\Scripts\ruff check . ; .venv\Scripts\mypy src\" -ForegroundColor Yellow
    } else {
        Write-Host "  - Use mvg-config: .venv/bin/mvg-config search `"Station Name`"" -ForegroundColor Yellow
        Write-Host "  - Run tests: .venv/bin/pytest" -ForegroundColor Yellow
        Write-Host "  - Run linters: .venv/bin/ruff check . && .venv/bin/mypy src/" -ForegroundColor Yellow
    }
    Write-Host "  - Analyze complexity: .\scripts\analyze_complexity.ps1" -ForegroundColor Yellow
    Write-Host ""
}

# Upgrade pip first
Write-Host "Upgrading pip..." -ForegroundColor Yellow
& $PYTHON -m pip install --upgrade pip --quiet 2>$null
Write-Host "✓ pip upgraded." -ForegroundColor Green
Write-Host ""

# Check if already installed
if (_check_package_installed) {
    Write-Host "✓ Package already installed." -ForegroundColor Green
    Write-Host ""
    Write-Host "Setup complete!" -ForegroundColor Green
    Write-Host ""
    _print_usage_info
    exit 0

# Try to install using available package managers
$INSTALL_SUCCESS = $false

# Try Poetry first (if poetry.lock exists)
$poetryLockPath = Join-Path $PROJECT_ROOT "poetry.lock"
if ((Test-Path $poetryLockPath) -and (Get-Command poetry -ErrorAction SilentlyContinue)) {
    Write-Host "Using Poetry to install dependencies..." -ForegroundColor Yellow
    poetry install --with dev 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) {
        $INSTALL_SUCCESS = $true
        Write-Host "✓ Dependencies installed with Poetry." -ForegroundColor Green
    } else {
        Write-Host "Warning: Poetry installation failed, trying alternatives..." -ForegroundColor Yellow
    }
}

# Try uv if Poetry didn't work
if (-not $INSTALL_SUCCESS) {
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
        Write-Host "Installing dependencies with uv..." -ForegroundColor Yellow
        if (Test-Path $UV) {
            & $UV pip install -e ".[dev]" 2>&1 | Out-Host
            if ($LASTEXITCODE -eq 0) {
                $INSTALL_SUCCESS = $true
                Write-Host "✓ Dependencies installed with uv." -ForegroundColor Green
            }
        } else {
            & $UV pip install -e ".[dev]" 2>&1 | Out-Host
            if ($LASTEXITCODE -eq 0) {
                $INSTALL_SUCCESS = $true
                Write-Host "✓ Dependencies installed with uv." -ForegroundColor Green
            }
        }
    }

# Fall back to pip
if (-not $INSTALL_SUCCESS) {
    Write-Host "Using pip to install dependencies..." -ForegroundColor Yellow
    & $PIP install -e ".[dev]" 2>&1 | Out-Host
    if ($LASTEXITCODE -eq 0) {
        $INSTALL_SUCCESS = $true
        Write-Host "✓ Dependencies installed with pip." -ForegroundColor Green
    } else {
        Write-Host "Warning: Failed to install with dev dependencies, trying core dependencies..." -ForegroundColor Yellow
        & $PIP install -e . 2>&1 | Out-Host
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ Core dependencies installed. Dev dependencies may be missing." -ForegroundColor Green
            Write-Host "  You can install them later with: $PIP install -e `".[dev]`"" -ForegroundColor Yellow
            $INSTALL_SUCCESS = $true
        } else {
            Write-Host "Error: Failed to install package" -ForegroundColor Red
            exit 1
        }
    }

# Verify installation
if (-not (_check_package_installed)) {
    Write-Host "Warning: Package installation may have failed. Please check the output above." -ForegroundColor Yellow
    Write-Host "  You can try manually: $PIP install -e `".[dev]`"" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
_print_usage_info

