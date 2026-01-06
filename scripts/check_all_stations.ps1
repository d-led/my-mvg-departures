# Check if all stations in a TOML config file can be queried

$ErrorActionPreference = "Stop"

if ($args.Count -eq 0) {
    Write-Host "Usage: $($MyInvocation.MyCommand.Name) <config.toml>" -ForegroundColor Yellow
    Write-Host "Example: $($MyInvocation.MyCommand.Name) config.toml" -ForegroundColor Yellow
    exit 1
}

$CONFIG_FILE = $args[0]

if (-not (Test-Path $CONFIG_FILE)) {
    Write-Host "Error: Config file '$CONFIG_FILE' not found" -ForegroundColor Red
    exit 1
}

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_DIR = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_DIR

# Activate virtual environment if it exists
if (Test-Path ".venv") {
    if ($IsWindows -or $env:OS -eq "Windows_NT") {
        & ".venv\Scripts\Activate.ps1"
    } else {
        & source ".venv/bin/activate"
    }
}

# Check for --raw flag
$RAW_FLAG = ""
if ($args.Count -gt 1 -and $args[1] -eq "--raw") {
    $RAW_FLAG = "--raw"
}

# Run Python script
$checkScript = Join-Path $SCRIPT_DIR "check_all_stations.py"

# Find Python command - prefer 'python' on Windows, 'python3' on Unix
$PYTHON_CMD = "python"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    $PYTHON_CMD = "python3"
}

if ($RAW_FLAG) {
    & $PYTHON_CMD $checkScript $CONFIG_FILE $RAW_FLAG
} else {
    & $PYTHON_CMD $checkScript $CONFIG_FILE
}

