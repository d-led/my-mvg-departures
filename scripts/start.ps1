# Simple start script for MVG Departures
# Works from any directory, automatically handles venv and dependencies

$ErrorActionPreference = "Stop"

# Find project root (where this script is located)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_ROOT

# Find virtual environment
$VENV_PATH = $null
$venvNames = @(".venv", "venv", "env", ".env")

foreach ($venvName in $venvNames) {
    $venvPath = Join-Path $PROJECT_ROOT $venvName
    if (Test-Path $venvPath) {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            $pythonPath = Join-Path $venvPath "Scripts\python.exe"
            if (Test-Path $pythonPath) {
                $VENV_PATH = $venvPath
                break
            }
        } else {
            $pythonPath = Join-Path $venvPath "bin\python"
            if (Test-Path $pythonPath) {
                $VENV_PATH = $venvPath
                break
            }
        }
    }
}

# Determine Python executable
if ($VENV_PATH) {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $PYTHON = Join-Path $VENV_PATH "Scripts\python.exe"
        $PIP = Join-Path $VENV_PATH "Scripts\pip.exe"
        $UV = Join-Path $VENV_PATH "Scripts\uv.exe"
    } else {
        $PYTHON = Join-Path $VENV_PATH "bin\python"
        $PIP = Join-Path $VENV_PATH "bin\pip"
        $UV = Join-Path $VENV_PATH "bin\uv"
    }
    Write-Host "Using virtual environment: $VENV_PATH" -ForegroundColor Yellow
} else {
    # On Windows, prefer 'python' over 'python3'
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $PYTHON = "python"
        $PIP = "pip"
    } else {
        $PYTHON = "python3"
        $PIP = "pip3"
    }
    $UV = "uv"
    Write-Host "No virtual environment found, using system Python" -ForegroundColor Yellow
}

# Check if package is installed by trying to import it
$checkScript = Join-Path $SCRIPT_DIR "check_package_installed.py"
$packageInstalled = $false
try {
    & $PYTHON $checkScript 2>$null
    if ($LASTEXITCODE -eq 0) {
        $packageInstalled = $true
    }
} catch {
    $packageInstalled = $false
}

if (-not $packageInstalled) {
    Write-Host "Package not installed. Installing..." -ForegroundColor Yellow
    Write-Host ""
    
    # Try uv first, then pip
    $installed = $false
    if (Get-Command $UV -ErrorAction SilentlyContinue) {
        try {
            Write-Host "Installing with uv..." -ForegroundColor Yellow
            & $UV pip install -e .
            if ($LASTEXITCODE -eq 0) {
                $installed = $true
            }
        } catch {
            Write-Host "uv failed, trying pip..." -ForegroundColor Yellow
        }
    }
    
    if (-not $installed) {
        try {
            Write-Host "Installing with pip..." -ForegroundColor Yellow
            & $PIP install -e .
            if ($LASTEXITCODE -eq 0) {
                $installed = $true
            } else {
                Write-Host "Error: Failed to install package" -ForegroundColor Red
                exit 1
            }
        } catch {
            Write-Host "Error: Failed to install package" -ForegroundColor Red
            exit 1
        }
    }
    
    Write-Host "Package installed successfully!" -ForegroundColor Green
    Write-Host ""
}

# Run the application
Write-Host "Starting MVG Departures..." -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop" -ForegroundColor Yellow
Write-Host ""

& $PYTHON -m mvg_departures.main

