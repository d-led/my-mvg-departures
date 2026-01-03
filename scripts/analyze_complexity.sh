#!/bin/bash
# Shell script wrapper for complexity analysis tool
#
# Usage:
#   ./scripts/analyze_complexity.sh [directory]
#
# If no directory is provided, defaults to src/mvg_departures

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ANALYZE_SCRIPT="$SCRIPT_DIR/analyze_complexity.py"

cd "$PROJECT_ROOT"

# Detect virtual environment and command runner (same pattern as test.sh)
if [ -d ".venv" ]; then
    PYTHON=".venv/bin/python"
    RUN_CMD=""
    echo "Using existing .venv"
elif command -v uv &> /dev/null; then
    PYTHON="python3"
    RUN_CMD="uv run"
    echo "Using uv"
else
    PYTHON="python3"
    RUN_CMD=""
    echo "Using system Python (ensure dependencies are installed)"
fi

# Function to run command with or without uv
run_python() {
    if [ -n "$RUN_CMD" ]; then
        $RUN_CMD "$@"
    else
        $PYTHON "$@"
    fi
}

# Default to both src/mvg_departures and scripts if no argument provided
# If argument is provided, use it; otherwise analyze both source and scripts
if [[ $# -eq 0 ]]; then
    # Analyze both source code and scripts
    echo "Analyzing source code and scripts..."
    run_python "$ANALYZE_SCRIPT" "$PROJECT_ROOT/src/mvg_departures"
    echo ""
    echo "=================================================================================="
    echo "SCRIPTS ANALYSIS"
    echo "=================================================================================="
    run_python "$ANALYZE_SCRIPT" "$PROJECT_ROOT/scripts"
    exit 0
else
    TARGET_DIR="${1}"
fi

# Convert to absolute path if relative
if [[ ! "$TARGET_DIR" = /* ]]; then
    TARGET_DIR="$PROJECT_ROOT/$TARGET_DIR"
fi

# Check if Python script exists
if [[ ! -f "$ANALYZE_SCRIPT" ]]; then
    echo "Error: Analysis script not found at $ANALYZE_SCRIPT" >&2
    exit 1
fi

# Check if target directory exists
if [[ ! -d "$TARGET_DIR" ]]; then
    echo "Error: Target directory not found: $TARGET_DIR" >&2
    exit 1
fi

# Run the analysis script
run_python "$ANALYZE_SCRIPT" "$TARGET_DIR"

