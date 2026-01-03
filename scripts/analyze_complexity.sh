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

# Source common environment setup
source "$SCRIPT_DIR/common_env.sh"

# Debug: show argument count and what we received
echo "DEBUG: analyze_complexity.sh called with $# arguments: $*" >&2

# Default to both src/mvg_departures and scripts if no argument provided
# If argument is provided, use it; otherwise analyze both source and scripts
if [[ $# -eq 0 ]]; then
    # Analyze both source code and scripts
    echo "Analyzing source code and scripts..."
    run_python "$ANALYZE_SCRIPT" "$PROJECT_ROOT/src/mvg_departures" || exit $?
    echo ""
    echo "=================================================================================="
    echo "SCRIPTS ANALYSIS"
    echo "=================================================================================="
    run_python "$ANALYZE_SCRIPT" "$PROJECT_ROOT/scripts" || exit $?
    echo ""
    echo "=================================================================================="
    echo "DEAD CODE DETECTION (vulture)"
    echo "=================================================================================="
    echo "Checking source code..."
    if run_python_module vulture "$PROJECT_ROOT/src/mvg_departures" --min-confidence 80; then
        echo "✓ No dead code found in source"
    fi
    echo ""
    echo "Checking scripts..."
    if run_python_module vulture "$PROJECT_ROOT/scripts" --min-confidence 80; then
        echo "✓ No dead code found in scripts"
    fi
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

# Run the analysis script (unbuffered output handled by run_python)
run_python "$ANALYZE_SCRIPT" "$TARGET_DIR"

