# Shell script wrapper for complexity analysis tool
#
# Usage:
#   .\scripts\analyze_complexity.ps1 [directory]
#
# If no directory is provided, defaults to src/mvg_departures

$ErrorActionPreference = "Stop"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR
$ANALYZE_SCRIPT = Join-Path $SCRIPT_DIR "analyze_complexity.py"

Set-Location $PROJECT_ROOT

# Source common environment setup
. "$SCRIPT_DIR\common_env.ps1"

# Debug: show argument count and what we received
Write-Host "DEBUG: analyze_complexity.ps1 called with $($args.Count) arguments: $($args -join ' ')" -ForegroundColor Yellow

# Default to both src/mvg_departures and scripts if no argument provided
# If argument is provided, use it; otherwise analyze both source and scripts
if ($args.Count -eq 0) {
    # Analyze both source code and scripts
    Write-Host "Analyzing source code and scripts..."
    $sourcePath = Join-Path $PROJECT_ROOT "src\mvg_departures"
    if (-not (Test-Path $sourcePath)) {
        $sourcePath = Join-Path $PROJECT_ROOT "src/mvg_departures"
    }
    run_python $ANALYZE_SCRIPT $sourcePath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Write-Host ""
    Write-Host "=================================================================================="
    Write-Host "SCRIPTS ANALYSIS"
    Write-Host "=================================================================================="
    $scriptsPath = Join-Path $PROJECT_ROOT "scripts"
    run_python $ANALYZE_SCRIPT $scriptsPath
    if ($LASTEXITCODE -ne 0) {
        exit $LASTEXITCODE
    }
    Write-Host ""
    Write-Host "=================================================================================="
    Write-Host "DEAD CODE DETECTION (vulture)"
    Write-Host "=================================================================================="
    Write-Host "Checking source code..."
    run_python_module vulture "$PROJECT_ROOT\src\mvg_departures" --min-confidence 80
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ No dead code found in source" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "Checking scripts..."
    run_python_module vulture "$PROJECT_ROOT\scripts" --min-confidence 80
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ No dead code found in scripts" -ForegroundColor Green
    }
    exit 0
} else {
    $TARGET_DIR = $args[0]
}

# Convert to absolute path if relative
if (-not ([System.IO.Path]::IsPathRooted($TARGET_DIR))) {
    $TARGET_DIR = Join-Path $PROJECT_ROOT $TARGET_DIR
}

# Check if Python script exists
if (-not (Test-Path $ANALYZE_SCRIPT)) {
    Write-Host "Error: Analysis script not found at $ANALYZE_SCRIPT" -ForegroundColor Red
    exit 1
}

# Check if target directory exists
if (-not (Test-Path $TARGET_DIR)) {
    Write-Host "Error: Target directory not found: $TARGET_DIR" -ForegroundColor Red
    exit 1
}

# Run the analysis script (unbuffered output handled by run_python)
run_python $ANALYZE_SCRIPT $TARGET_DIR

