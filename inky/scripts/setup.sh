#!/bin/bash
# Setup script for MVG Departures Inky Display (Hardware - Raspberry Pi)
# Sets up both parent project and inky project with hardware dependencies

set -euo pipefail

# Find project root (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INKY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARENT_ROOT="$(cd "${INKY_ROOT}/.." && pwd)"

cd "$INKY_ROOT"

echo "Setting up MVG Departures Inky Display (Hardware Mode)..." >&2
echo "" >&2

# Check Python version
if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 not found. Please install Python 3.12 or later." >&2
    exit 1
fi

PYTHON_VERSION=$(python3 "$PARENT_ROOT/scripts/get_python_version.py")
REQUIRED_VERSION="3.12"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "Warning: Python $PYTHON_VERSION detected. Python 3.12 or later is recommended." >&2
    echo "" >&2
fi

# Source common setup functions
source "${PARENT_ROOT}/scripts/setup-common.sh"

# Setup virtual environment (use parent's venv - unified!)
setup_venv "$PARENT_ROOT"

# Helper functions
_check_package_installed() {
    "$PYTHON" -c "import mvg_departures_inky" >/dev/null 2>&1
}

_print_usage_info() {
    echo "To use the commands, either:" >&2
    echo "  1. Activate the virtual environment:" >&2
    if [ -f "${VENV_PATH}/bin/activate" ]; then
        echo "     source ${PARENT_ROOT}/.venv/bin/activate" >&2
    else
        echo "     source ${PARENT_ROOT}/.venv/Script/activate" >&2
    fi
    echo "  2. Or use the full path:" >&2
    echo "     ${PARENT_ROOT}/.venv/bin/mvg-departures-inky" >&2
    echo "" >&2
    echo "You can now:" >&2
    echo "  - Run with real hardware: ./scripts/start.sh" >&2
    echo "  - Run in mock mode: ./scripts/run_mock.sh" >&2
    echo "  - Set CONFIG_FILE environment variable to use custom config:" >&2
    echo "    CONFIG_FILE=my.config.toml ./scripts/start.sh" >&2
    echo "" >&2
}

# Step 1: Install parent project
echo "Step 1: Installing parent project..." >&2
cd "$PARENT_ROOT"
if ! "$PYTHON" -c "import mvg_departures" >/dev/null 2>&1; then
    echo "Parent project not installed. Installing..." >&2
    if ! install_with_available_manager "$PARENT_ROOT" ".[dev]"; then
        echo "Warning: Failed to install with dev dependencies, trying core..." >&2
        if ! "$PIP" install -e . 2>&1; then
            echo "Error: Failed to install parent project" >&2
            exit 1
        fi
    fi
    echo "✓ Parent project installed." >&2
else
    echo "✓ Parent project already installed." >&2
fi
echo "" >&2

# Step 2: Install system dependencies (numpy via apt on Linux only)
echo "Step 2: Installing system dependencies..." >&2
install_numpy_for_pi
echo "" >&2

# Step 3: Install inky project with hardware dependencies
echo "Step 3: Installing Inky project with hardware dependencies..." >&2
cd "$INKY_ROOT"

if _check_package_installed; then
    echo "✓ Inky package already installed." >&2
    echo "" >&2
    echo "Setup complete!" >&2
    echo "" >&2
    _print_usage_info
    exit 0
fi

# Install inky project (always with hardware support on Linux)
if install_with_available_manager "$INKY_ROOT" ".[dev,hardware]"; then
    if "$PYTHON" -c "import mvg_departures_inky" >/dev/null 2>&1; then
        echo "✓ Inky package verified." >&2
    else
        echo "Warning: Inky package installation may have failed." >&2
    fi
else
    echo "Warning: Failed to install with hardware support, trying without..." >&2
    if install_with_available_manager "$INKY_ROOT" ".[dev]"; then
        echo "✓ Core dependencies installed (development mode)." >&2
        echo "  Hardware dependencies may be missing. For Raspberry Pi, try:" >&2
        echo "  $PIP install -e \".[hardware]\"" >&2
    else
        echo "Error: Failed to install package" >&2
        echo "  This script is for Raspberry Pi. For macOS/Windows, use: ./scripts/setup_dev.sh" >&2
        exit 1
    fi
fi

echo "" >&2
echo "✓ Setup complete! Hardware dependencies installed." >&2
echo "" >&2
_print_usage_info
