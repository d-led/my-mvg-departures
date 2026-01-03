#!/bin/bash
# Integration test script for MVG Departures
# Runs only integration tests that require network access
# Automatically detects and uses .venv if available

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Source common environment setup
source "$SCRIPT_DIR/common_env.sh"

# Check if dependencies are installed
if ! run_python_module pytest --version &> /dev/null 2>&1; then
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

