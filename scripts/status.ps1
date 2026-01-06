# Check status of MVG Departures application
# Works from any directory

# Source common functions
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
. "${SCRIPT_DIR}\deploy-common.ps1"

get_app_paths

$mode = detect_mode

Write-Host "Mode: $mode"
Write-Host ""

if (is_running) {
    $pid = get_pid
    Write-Host "Status: RUNNING"
    Write-Host "PID: $pid"
    
    # Show process info
    try {
        $process = Get-Process -Id $pid -ErrorAction Stop
        Write-Host ""
        Write-Host "Process info:"
        Write-Host "  PID: $($process.Id)"
        Write-Host "  CPU: $($process.CPU)"
        Write-Host "  Memory: $([math]::Round($process.WorkingSet64 / 1MB, 2)) MB"
        Write-Host "  Start Time: $($process.StartTime)"
    } catch {
        # Process info not available
    }
    
    # Show log tail if available
    if (Test-Path $LOGFILE) {
        Write-Host ""
        Write-Host "Recent log entries:"
        Get-Content $LOGFILE -Tail 5 -ErrorAction SilentlyContinue
    }
    
    exit 0
} else {
    Write-Host "Status: STOPPED"
    
    # Check for stale PID file
    if (Test-Path $PIDFILE) {
        Write-Host "Warning: Stale PID file found at $PIDFILE" -ForegroundColor Yellow
    }
    
    exit 1
}

