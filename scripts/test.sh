#!/bin/bash
# Test script for MVG Departures
# Automatically detects and uses .venv if available

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Detect virtual environment
if [ -d ".venv" ]; then
    PYTHON=".venv/bin/python"
    PIP=".venv/bin/pip"
    PYTEST=".venv/bin/pytest"
    echo "Using existing .venv"
elif command -v uv &> /dev/null; then
    PYTHON="python3"
    PIP="uv pip"
    PYTEST="uv run pytest"
    echo "Using uv"
else
    PYTHON="python3"
    PIP="pip3"
    PYTEST="pytest"
    echo "Using system Python (ensure dependencies are installed)"
fi

# Check if pytest is available
if ! $PYTHON -m pytest --version &> /dev/null; then
    echo "pytest not found. Installing dependencies..."
    if [ -d ".venv" ]; then
        $PIP install -e ".[dev]"
    else
        echo "Warning: No .venv found. Please run ./scripts/setup.sh first or install dependencies manually."
        exit 1
    fi
fi

# Run tests
echo "Running tests..."
$PYTHON -m pytest "$@"

