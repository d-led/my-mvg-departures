#!/bin/bash
# Integration test script for MVG Departures
# Runs only integration tests that require network access
# Automatically detects and uses .venv if available

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Detect virtual environment and command runner
if [ -d ".venv" ]; then
    PYTHON=".venv/bin/python"
    PIP=".venv/bin/pip"
    RUN_CMD=""
    echo "Using existing .venv"
elif command -v uv &> /dev/null; then
    PYTHON="python3"
    PIP="uv pip"
    RUN_CMD="uv run"
    echo "Using uv"
else
    PYTHON="python3"
    PIP="pip3"
    RUN_CMD=""
    echo "Using system Python (ensure dependencies are installed)"
fi

# Check if dependencies are installed
if ! $PYTHON -m pytest --version &> /dev/null 2>&1; then
    echo "Dependencies not found. Installing..."
    if [ -d ".venv" ]; then
        $PIP install -e ".[dev]"
    else
        echo "Warning: No .venv found. Please run ./scripts/setup.sh first or install dependencies manually."
        exit 1
    fi
fi

echo "=========================================="
echo "Running Integration Tests..."
echo "=========================================="
echo ""
echo "Note: Integration tests require network access and may take longer to run."
echo ""

# Run integration tests
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD pytest -m integration -v "$@"
else
    $PYTHON -m pytest -m integration -v "$@"
fi

echo ""
echo "=========================================="
echo "Integration tests completed! ✓"
echo "=========================================="

