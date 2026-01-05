#!/bin/bash
# Test script for MVG Departures
# Runs all CI checks: formatting, linting, type checking, and tests
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

# Function to run command with or without uv (for backward compatibility)
run_check() {
    run_python_module "$@"
}

echo "=========================================="
echo "Formatting..."
echo "=========================================="
echo ""

"$SCRIPT_DIR/reformat.sh"

# Run all CI checks
echo "=========================================="
echo "Running CI checks..."
echo "=========================================="
echo ""

# 1. Check code formatting with Black
echo "1. Checking code formatting with Black..."
run_python_module black --check src tests
echo "✓ Formatting check passed"
echo ""

# 2. Lint with Ruff
echo "2. Linting with Ruff..."
run_python_module ruff check src tests
echo "✓ Linting passed"
echo ""

# 3. Type check with mypy
echo "3. Type checking with mypy..."
run_python_module mypy src
echo "✓ Type checking passed"
echo ""

# 4. Run tests (excluding integration tests by default)
echo "4. Running tests..."
run_python_module pytest -m "not integration" "$@"
echo "✓ Tests passed"
echo ""

echo "=========================================="
echo "All checks passed! ✓"
echo "=========================================="



