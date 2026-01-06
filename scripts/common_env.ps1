# Common environment setup for scripts
# Source this file to get PYTHON, PIP, and RUN_CMD variables set up correctly
#
# Usage:
#   . "$SCRIPT_DIR/common_env.ps1"
#
# After sourcing, you'll have:
#   - $PYTHON: Path to Python executable
#   - $PIP: Path to pip executable
#   - $RUN_CMD: Command prefix for running Python modules (empty or "uv run")
#
# This script is idempotent - safe to source multiple times.

# Only set up if not already set (allows multiple sourcing - idempotent)
# Check if already loaded to prevent re-initialization
if (-not $env:COMMON_ENV_LOADED) {
    # Mark as loaded FIRST to prevent re-initialization even if detection fails
    $env:COMMON_ENV_LOADED = "1"
    
    # Detect virtual environment and command runner
    if (Test-Path ".venv") {
        if ($IsWindows -or $env:OS -eq "Windows_NT") {
            $script:PYTHON = Join-Path ".venv" "Scripts\python.exe"
            $script:PIP = Join-Path ".venv" "Scripts\pip.exe"
        } else {
            $script:PYTHON = Join-Path ".venv" "bin\python"
            $script:PIP = Join-Path ".venv" "bin\pip"
        }
        $script:RUN_CMD = ""
        Write-Host "Using existing .venv" -ForegroundColor Yellow
    } elseif (Get-Command uv -ErrorAction SilentlyContinue) {
        # On Windows, prefer 'python' over 'python3'
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $script:PYTHON = "python"
        } else {
            $script:PYTHON = "python3"
        }
        $script:PIP = "uv pip"
        $script:RUN_CMD = "uv run"
        Write-Host "Using uv" -ForegroundColor Yellow
    } else {
        # On Windows, prefer 'python' over 'python3'
        if (Get-Command python -ErrorAction SilentlyContinue) {
            $script:PYTHON = "python"
            $script:PIP = "pip"
        } else {
            $script:PYTHON = "python3"
            $script:PIP = "pip3"
        }
        $script:RUN_CMD = ""
        Write-Host "Using system Python (ensure dependencies are installed)" -ForegroundColor Yellow
    }
    
    # Export variables
    $env:PYTHON = $script:PYTHON
    $env:PIP = $script:PIP
    $env:RUN_CMD = $script:RUN_CMD
    
    # Function to run Python command with or without uv
    # Only define if not already defined (allows function redefinition to be safe)
    if (-not (Get-Command run_python -ErrorAction SilentlyContinue)) {
        function run_python {
            param([Parameter(ValueFromRemainingArguments)]$args)
            
            if ($RUN_CMD) {
                # uv run handles buffering, but set PYTHONUNBUFFERED for consistency
                $env:PYTHONUNBUFFERED = "1"
                & $RUN_CMD.Split(" ") $args
            } else {
                # Always use -u flag for unbuffered output to show progress
                & $PYTHON -u $args
            }
        }
    }
    
    # Function to run Python module with or without uv
    if (-not (Get-Command run_python_module -ErrorAction SilentlyContinue)) {
        function run_python_module {
            param([Parameter(ValueFromRemainingArguments)]$args)
            
            if ($RUN_CMD) {
                # uv run handles buffering, but set PYTHONUNBUFFERED for consistency
                $env:PYTHONUNBUFFERED = "1"
                & $RUN_CMD.Split(" ") -m $args
            } else {
                # Always use -u flag for unbuffered output to show progress
                & $PYTHON -u -m $args
            }
        }
    }
}

