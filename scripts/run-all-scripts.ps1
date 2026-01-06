# Run all utility scripts to verify they work correctly
# This is a smoke test to ensure scripts are functional

# Handle Ctrl-C gracefully - allow interruption
$INTERRUPTED = $false
$ErrorActionPreference = "Continue"

$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

Set-Location $PROJECT_ROOT

# Colors for output
function Write-Red { param($text) Write-Host $text -ForegroundColor Red }
function Write-Green { param($text) Write-Host $text -ForegroundColor Green }
function Write-Yellow { param($text) Write-Host $text -ForegroundColor Yellow }

# Track results
$script:PASSED = 0
$script:FAILED = 0
$script:SKIPPED = 0
$script:FLAKY_PASSED = 0
$script:FLAKY_FAILED = 0
$script:FAILED_SCRIPTS = @()
$script:FLAKY_FAILED_SCRIPTS = @()

# Function to run a script and track results
function run_script {
    param(
        [string]$script_name,
        [string]$description,
        [string[]]$args_array = @()
    )
    
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "Testing: $script_name"
    Write-Host "Description: $description"
    if ($args_array.Count -gt 0) {
        Write-Host "Arguments: $($args_array -join ' ')"
    }
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    $scriptPath = Join-Path $SCRIPT_DIR $script_name
    if (-not (Test-Path $scriptPath)) {
        Write-Yellow "⚠ SKIPPED: Script not found"
        $script:SKIPPED++
        return
    }
    
    # Run script directly - output will be shown in real-time
    $script_exit_code = 0
    try {
        if ($args_array.Count -gt 0) {
            & $scriptPath $args_array
            $script_exit_code = $LASTEXITCODE
        } else {
            & $scriptPath
            $script_exit_code = $LASTEXITCODE
        }
    } catch {
        $script_exit_code = 1
    }
    
    if ($script_exit_code -eq 0) {
        Write-Green "✓ PASSED"
        $script:PASSED++
    } else {
        Write-Red "✗ FAILED (exit code: $script_exit_code)"
        $script:FAILED++
        $script:FAILED_SCRIPTS += $script_name
    }
}

# Function to run a flaky script (expected to potentially fail, doesn't affect exit code)
function run_script_flaky {
    param(
        [string]$script_name,
        [string]$description,
        [string[]]$args_array = @()
    )
    
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "Testing: $script_name (FLAKY - failure expected)"
    Write-Host "Description: $description"
    if ($args_array.Count -gt 0) {
        Write-Host "Arguments: $($args_array -join ' ')"
    }
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    $scriptPath = Join-Path $SCRIPT_DIR $script_name
    if (-not (Test-Path $scriptPath)) {
        Write-Yellow "⚠ SKIPPED: Script not found"
        $script:SKIPPED++
        return
    }
    
    $script_exit_code = 0
    try {
        if ($args_array.Count -gt 0) {
            & $scriptPath $args_array
            $script_exit_code = $LASTEXITCODE
        } else {
            & $scriptPath
            $script_exit_code = $LASTEXITCODE
        }
    } catch {
        $script_exit_code = 1
    }
    
    if ($script_exit_code -eq 0) {
        Write-Green "✓ PASSED"
        $script:FLAKY_PASSED++
    } else {
        Write-Yellow "⚠ XFAIL (exit code: $script_exit_code) - expected, API is flaky"
        $script:FLAKY_FAILED++
        $script:FLAKY_FAILED_SCRIPTS += $script_name
    }
}

# Check if config.example.toml exists
$CONFIG_FILE = "config.example.toml"
if (-not (Test-Path $CONFIG_FILE)) {
    Write-Yellow "Warning: $CONFIG_FILE not found. Some tests will be skipped."
    $CONFIG_FILE = ""
}

Write-Host "════════════════════════════════════════════════════════════════════════════════"
Write-Host "Running all utility scripts smoke tests"
Write-Host "════════════════════════════════════════════════════════════════════════════════"

# 1. Check all stations script
if ($CONFIG_FILE) {
    run_script "check_all_stations.ps1" "Check if all stations in config can be queried" @($CONFIG_FILE)
} else {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    Write-Host "Testing: check_all_stations.ps1"
    Write-Yellow "⚠ SKIPPED: config.example.toml not found"
    $script:SKIPPED++
}

# 2. Analyze complexity script
run_script "analyze_complexity.ps1" "Analyze code complexity metrics"

# 3. List routes (MVG)
run_script "list_routes.ps1" "List routes for MVG station" @("Balanstr.")

# 4. List departures (MVG) - base station
run_script "list_departures.ps1" "List live departures for MVG station" @("de:09162:6", "--limit", "10")

# 5. List departures (MVG) - specific stop point
run_script "list_departures.ps1" "List departures for specific stop point (Rotkreuzplatz)" @("de:09162:6:1:1", "--limit", "10")

# 6. List routes VBB
run_script "list_routes_vbb.ps1" "List routes for VBB station" @("blissestr.")

# 7. List routes DB (flaky - API often returns 503)
run_script_flaky "list_routes_db.ps1" "List routes for DB station (API is flaky)" @("blissestr.")

# Print summary
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════════════════════"
Write-Host "SUMMARY"
Write-Host "════════════════════════════════════════════════════════════════════════════════"
Write-Green "Passed: $($script:PASSED)"
if ($script:FAILED -gt 0) {
    Write-Red "Failed: $($script:FAILED)"
    Write-Host "Failed scripts:"
    foreach ($script in $script:FAILED_SCRIPTS) {
        Write-Host "  - $script"
    }
} else {
    Write-Green "Failed: $($script:FAILED)"
}
if ($script:SKIPPED -gt 0) {
    Write-Yellow "Skipped: $($script:SKIPPED)"
}
if ($script:FLAKY_PASSED -gt 0 -or $script:FLAKY_FAILED -gt 0) {
    Write-Yellow "Flaky tests: $($script:FLAKY_PASSED) passed, $($script:FLAKY_FAILED) xfailed"
    if ($script:FLAKY_FAILED -gt 0) {
        Write-Host "  (xfailed scripts - expected failures, don't affect exit code):"
        foreach ($script in $script:FLAKY_FAILED_SCRIPTS) {
            Write-Host "    - $script"
        }
    }
}
Write-Host ""

# Exit with error if any non-flaky script failed
if ($script:FAILED -gt 0) {
    exit 1
}

exit 0

