#!/bin/bash
# Reformat script for MVG Departures
# Automatically detects and uses .venv if available

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Source common environment setup
source "$SCRIPT_DIR/common_env.sh"

# Set BLACK command based on environment
if [ -n "$RUN_CMD" ]; then
    BLACK="$RUN_CMD black"
elif [ -d ".venv" ]; then
    BLACK=".venv/bin/black"
else
    BLACK="black"
fi

# Check if black is available using the actual command we'll use
if ! $BLACK --version &> /dev/null; then
    echo "black not found. Installing dependencies..."
    if [ -d ".venv" ]; then
        $PIP install -e ".[dev]"
    elif command -v uv &> /dev/null; then
        uv pip install -e ".[dev]"
    else
        echo "Warning: No .venv found and uv not available. Please run ./scripts/setup.sh first or install dependencies manually."
        exit 1
    fi
fi

# Run black to format code
echo "Reformatting code with black..."
$BLACK src tests

echo "✅ Code reformatted successfully!"

