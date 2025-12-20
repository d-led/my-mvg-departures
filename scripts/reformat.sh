#!/bin/bash
# Reformat script for MVG Departures
# Automatically detects and uses .venv if available

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Detect virtual environment
if [ -d ".venv" ]; then
    PYTHON=".venv/bin/python"
    BLACK=".venv/bin/black"
    echo "Using existing .venv"
elif command -v uv &> /dev/null; then
    PYTHON="python3"
    BLACK="uv run black"
    echo "Using uv"
else
    PYTHON="python3"
    BLACK="black"
    echo "Using system Python (ensure dependencies are installed)"
fi

# Check if black is available
if ! $PYTHON -m black --version &> /dev/null; then
    echo "black not found. Installing dependencies..."
    if [ -d ".venv" ]; then
        .venv/bin/pip install -e ".[dev]"
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

