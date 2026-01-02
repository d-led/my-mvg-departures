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

# Default to src/mvg_departures if no argument provided
TARGET_DIR="${1:-$PROJECT_ROOT/src/mvg_departures}"

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
cd "$PROJECT_ROOT"
exec python3 "$ANALYZE_SCRIPT" "$TARGET_DIR"

