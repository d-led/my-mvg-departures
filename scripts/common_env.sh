#!/bin/bash
# Common environment setup for scripts
# Source this file to get PYTHON, PIP, and RUN_CMD variables set up correctly
#
# Usage:
#   source "$SCRIPT_DIR/common_env.sh"
#
# After sourcing, you'll have:
#   - PYTHON: Path to Python executable
#   - PIP: Path to pip executable
#   - RUN_CMD: Command prefix for running Python modules (empty or "uv run")
#
# This script is idempotent - safe to source multiple times.

# Only set up if not already set (allows multiple sourcing - idempotent)
# Check if already loaded to prevent re-initialization
if [ -z "${COMMON_ENV_LOADED:-}" ]; then
    # Mark as loaded FIRST to prevent re-initialization even if detection fails
    export COMMON_ENV_LOADED=1
    
    # Detect virtual environment and command runner
    if [ -d ".venv" ]; then
        PYTHON=".venv/bin/python"
        PIP=".venv/bin/pip"
        RUN_CMD=""
        echo "Using existing .venv" >&2
    elif command -v uv &> /dev/null; then
        PYTHON="python3"
        PIP="uv pip"
        RUN_CMD="uv run"
        echo "Using uv" >&2
    else
        PYTHON="python3"
        PIP="pip3"
        RUN_CMD=""
        echo "Using system Python (ensure dependencies are installed)" >&2
    fi

    # Function to run Python command with or without uv
    # Only define if not already defined (allows function redefinition to be safe)
    if ! type run_python >/dev/null 2>&1; then
        run_python() {
            if [ -n "$RUN_CMD" ]; then
                # uv run handles buffering, but set PYTHONUNBUFFERED for consistency
                PYTHONUNBUFFERED=1 $RUN_CMD "$@"
            else
                # Always use -u flag for unbuffered output to show progress
                $PYTHON -u "$@"
            fi
        }
    fi

    # Function to run Python module with or without uv
    if ! type run_python_module >/dev/null 2>&1; then
        run_python_module() {
            if [ -n "$RUN_CMD" ]; then
                # uv run handles buffering, but set PYTHONUNBUFFERED for consistency
                PYTHONUNBUFFERED=1 $RUN_CMD "$@"
            else
                # Always use -u flag for unbuffered output to show progress
                $PYTHON -u -m "$@"
            fi
        }
    fi
fi

