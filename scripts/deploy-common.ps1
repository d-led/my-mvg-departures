# Common functions for deployment scripts
# This file is sourced by other deployment scripts

# Find the project root directory (where this script is located)
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$PROJECT_ROOT = Split-Path -Parent $SCRIPT_DIR

# Application configuration
$APP_NAME = "mvg-departures"
$APP_DIR = "/opt/${APP_NAME}"
$VENV_DIR = "${APP_DIR}/.venv"
$PIDFILE = "/var/run/${APP_NAME}.pid"
$LOGFILE = "/var/log/${APP_NAME}.log"
$APP_USER = "${APP_NAME}"

# Detect if running as installed service or development mode
function detect_mode {
    if ((Test-Path $APP_DIR) -and (Test-Path "${VENV_DIR}/bin/mvg-departures")) {
        return "service"
    } else {
        return "dev"
    }
}

# Get the Python executable and app script
function get_app_paths {
    $mode = detect_mode
    
    if ($mode -eq "service") {
        $script:PYTHON = "${VENV_DIR}/bin/python"
        $script:APP_SCRIPT = "${VENV_DIR}/bin/mvg-departures"
        $script:WORK_DIR = $APP_DIR
    } else {
        # Development mode - use project's venv or system python
        if (Test-Path "${PROJECT_ROOT}/.venv") {
            if ($IsWindows -or $env:OS -eq "Windows_NT") {
                $script:PYTHON = "${PROJECT_ROOT}/.venv/Scripts/python.exe"
            } else {
                $script:PYTHON = "${PROJECT_ROOT}/.venv/bin/python"
            }
        } elseif (Test-Path "${PROJECT_ROOT}/venv") {
            if ($IsWindows -or $env:OS -eq "Windows_NT") {
                $script:PYTHON = "${PROJECT_ROOT}/venv/Scripts/python.exe"
            } else {
                $script:PYTHON = "${PROJECT_ROOT}/venv/bin/python"
            }
        } else {
            # On Windows, prefer 'python' over 'python3'
            if (Get-Command python -ErrorAction SilentlyContinue) {
                $script:PYTHON = "python"
            } else {
                $script:PYTHON = "python3"
            }
        }
        $script:APP_SCRIPT = "${PYTHON} -m mvg_departures.main"
        $script:WORK_DIR = $PROJECT_ROOT
    }
    
    Set-Variable -Name PYTHON -Value $script:PYTHON -Scope Global
    Set-Variable -Name APP_SCRIPT -Value $script:APP_SCRIPT -Scope Global
    Set-Variable -Name WORK_DIR -Value $script:WORK_DIR -Scope Global
}

# Check if application is running
function is_running {
    if (Test-Path $PIDFILE) {
        $pid = Get-Content $PIDFILE -ErrorAction SilentlyContinue
        if ($pid) {
            try {
                $process = Get-Process -Id $pid -ErrorAction Stop
                return $true
            } catch {
                # Stale PID file
                Remove-Item $PIDFILE -Force -ErrorAction SilentlyContinue
            }
        }
    }
    return $false
}

# Get process PID (from PID file or by name)
function get_pid {
    if (Test-Path $PIDFILE) {
        return Get-Content $PIDFILE
    } else {
        # Try to find process by name (cross-platform)
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            try {
                $processes = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*mvg_departures.main*" }
                if ($processes) {
                    return $processes[0].ProcessId
                }
            } catch {
                # Fallback: try to find python processes
                $processes = Get-Process python* -ErrorAction SilentlyContinue | Where-Object { $_.Path -like "*mvg*" }
                if ($processes) {
                    return $processes[0].Id
                }
            }
        } else {
            # Unix: use pgrep if available
            if (Get-Command pgrep -ErrorAction SilentlyContinue) {
                $pid = pgrep -f "mvg_departures.main" | Select-Object -First 1
                if ($pid) {
                    return $pid
                }
            }
        }
        return $null
    }
}

