#!/bin/bash
# Setup script for MVG Departures
# Creates virtual environment and installs all dependencies
# Supports: Poetry, uv, and pip (in that order of preference)

set -euo pipefail

# Find project root (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Setting up MVG Departures..." >&2
echo "" >&2

# Check Python version
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found. Please install Python 3.12 or later." >&2
    exit 1
fi

PYTHON_VERSION=$(python3 "$SCRIPT_DIR/get_python_version.py")
REQUIRED_VERSION="3.12"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Warning: Python $PYTHON_VERSION detected. Python 3.12 or later is recommended." >&2
    echo "" >&2
fi

# Source common setup functions
source "${SCRIPT_DIR}/setup-common.sh"

# Setup virtual environment
setup_venv "$PROJECT_ROOT"

# Helper functions
_check_package_installed() {
    "$PYTHON" "$SCRIPT_DIR/check_package_installed.py" >/dev/null 2>&1
}

_print_usage_info() {
    echo "To use the commands, either:" >&2
    echo "  1. Activate the virtual environment:" >&2
    if [ -f "${VENV_PATH}/bin/activate" ]; then
        echo "     source .venv/bin/activate" >&2
    else
        echo "     source .venv/Script/activate" >&2
    fi
    echo "  2. Or use the full path:" >&2
    echo "     .venv/bin/mvg-config search \"Station Name\"" >&2
    echo "" >&2
    echo "You can now:" >&2
    echo "  - Run the application: ./scripts/start.sh" >&2
    echo "  - Use mvg-config: .venv/bin/mvg-config search \"Station Name\"" >&2
    echo "  - Run tests: .venv/bin/pytest" >&2
    echo "  - Run linters: .venv/bin/ruff check . && .venv/bin/mypy src/" >&2
    echo "  - Analyze complexity: ./scripts/analyze_complexity.sh" >&2
    echo "" >&2
}

# Check if already installed
if _check_package_installed; then
    echo "✓ Package already installed." >&2
    echo "" >&2
    echo "Setup complete!" >&2
    echo "" >&2
    _print_usage_info
    exit 0
fi

# Install main project
if ! install_with_available_manager "$PROJECT_ROOT" ".[dev]"; then
    echo "Warning: Failed to install with dev dependencies, trying core dependencies..." >&2
    if ! "$PIP" install -e . 2>&1; then
        echo "Error: Failed to install package" >&2
        exit 1
    fi
    echo "✓ Core dependencies installed. Dev dependencies may be missing." >&2
    echo "  You can install them later with: $PIP install -e \".[dev]\"" >&2
fi

# Verify installation
if ! _check_package_installed; then
    echo "Warning: Package installation may have failed. Please check the output above." >&2
    echo "  You can try manually: $PIP install -e \".[dev]\"" >&2
    exit 1
fi

echo "" >&2
echo "✓ Setup complete!" >&2
echo "" >&2
_print_usage_info
