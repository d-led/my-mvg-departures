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
    # Get absolute path to project root (where .venv would be)
    # Try to find project root by looking for common_env.sh's parent directory
    SCRIPT_DIR_ABS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT_ABS="$(cd "$SCRIPT_DIR_ABS/.." && pwd)"
    
    if [ -d "$PROJECT_ROOT_ABS/.venv" ]; then
        export PYTHON="$PROJECT_ROOT_ABS/.venv/bin/python"
        export PIP="$PROJECT_ROOT_ABS/.venv/bin/pip"
        export RUN_CMD=""
        echo "Using existing .venv" >&2
    elif command -v uv &> /dev/null; then
        export PYTHON="python3"
        export PIP="uv pip"
        export RUN_CMD="uv run"
        echo "Using uv" >&2
    else
        export PYTHON="python3"
        export PIP="pip3"
        export RUN_CMD=""
        echo "Using system Python (ensure dependencies are installed)" >&2
    fi
fi

# Function to run Python command with or without uv
# Always define (even if already defined) to ensure it's available
run_python() {
    if [ -n "$RUN_CMD" ]; then
        # uv run handles buffering, but set PYTHONUNBUFFERED for consistency
        PYTHONUNBUFFERED=1 $RUN_CMD "$@"
    else
        # Always use -u flag for unbuffered output to show progress
        $PYTHON -u "$@"
    fi
}
# Export function so it's available in subshells
export -f run_python

# Function to run Python module with or without uv
# Always define (even if already defined) to ensure it's available
run_python_module() {
    if [ -n "$RUN_CMD" ]; then
        # uv run handles buffering, but set PYTHONUNBUFFERED for consistency
        PYTHONUNBUFFERED=1 $RUN_CMD "$@"
    else
        # Always use -u flag for unbuffered output to show progress
        $PYTHON -u -m "$@"
    fi
}
# Export function so it's available in subshells
export -f run_python_module
