#!/bin/bash
# Test script for MVG Departures
# Runs all CI checks: formatting, linting, type checking, and tests
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

# Function to run command with or without uv
run_check() {
    if [ -n "$RUN_CMD" ]; then
        $RUN_CMD "$@"
    else
        $PYTHON -m "$@"
    fi
}

# Run all CI checks
echo "=========================================="
echo "Running CI checks..."
echo "=========================================="
echo ""

# 1. Check code formatting with Black
echo "1. Checking code formatting with Black..."
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD black --check src tests
else
    $PYTHON -m black --check src tests
fi
echo "✓ Formatting check passed"
echo ""

# 2. Lint with Ruff
echo "2. Linting with Ruff..."
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD ruff check src tests
else
    $PYTHON -m ruff check src tests
fi
echo "✓ Linting passed"
echo ""

# 3. Type check with mypy
echo "3. Type checking with mypy..."
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD mypy src
else
    $PYTHON -m mypy src
fi
echo "✓ Type checking passed"
echo ""

# 4. Run tests
echo "4. Running tests..."
if [ -n "$RUN_CMD" ]; then
    $RUN_CMD pytest "$@"
else
    $PYTHON -m pytest "$@"
fi
echo "✓ Tests passed"
echo ""

echo "=========================================="
echo "All checks passed! ✓"
echo "=========================================="



