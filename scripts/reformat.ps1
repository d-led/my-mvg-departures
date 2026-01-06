# Reformat script for MVG Departures
# Automatically detects and uses .venv if available

$ErrorActionPreference = "Stop"

# Get the directory where this script is located
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_ROOT

# Source common environment setup
. "$SCRIPT_DIR\common_env.ps1"

# Set BLACK command based on environment
if ($RUN_CMD) {
    $BLACK_CMD = @($RUN_CMD.Split(" ")) + @("black")
} elseif (Test-Path ".venv") {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        $BLACK_CMD = @(Join-Path ".venv" "Scripts\black.exe")
    } else {
        $BLACK_CMD = @(Join-Path ".venv" "bin\black")
    }
} else {
    $BLACK_CMD = @("black")
}

# Check if black is available using the actual command we'll use
try {
    & $BLACK_CMD[0] --version 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "black not found"
    }
} catch {
    Write-Host "black not found. Installing dependencies..."
    if (Test-Path ".venv") {
        & $PIP install -e ".[dev]"
    } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        uv pip install -e ".[dev]"
    } else {
        Write-Host "Warning: No .venv found and uv not available. Please run .\scripts\setup.ps1 first or install dependencies manually." -ForegroundColor Yellow
        exit 1
    }
}

# Run black to format code
Write-Host "Reformatting code with black..."
& $BLACK_CMD[0] src tests

Write-Host "✅ Code reformatted successfully!" -ForegroundColor Green

