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

# Determine virtual environment path
VENV_PATH="${PROJECT_ROOT}/.venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_PATH" ]; then
    echo "Creating virtual environment at ${VENV_PATH}..." >&2
    python3 -m venv "$VENV_PATH"
    echo "✓ Virtual environment created." >&2
    echo "" >&2
else
    echo "✓ Virtual environment already exists at ${VENV_PATH}" >&2
    echo "" >&2
fi

# Determine Python and pip paths (cross-platform)
if [ -f "${VENV_PATH}/bin/python" ]; then
    PYTHON="${VENV_PATH}/bin/python"
    PIP="${VENV_PATH}/bin/pip"
    POETRY="${VENV_PATH}/bin/poetry"
    UV="${VENV_PATH}/bin/uv"
elif [ -f "${VENV_PATH}/Scripts/python.exe" ]; then
    PYTHON="${VENV_PATH}/Scripts/python.exe"
    PIP="${VENV_PATH}/Scripts/pip.exe"
    POETRY="${VENV_PATH}/Scripts/poetry.exe"
    UV="${VENV_PATH}/Scripts/uv.exe"
else
    echo "Error: Could not find Python in virtual environment" >&2
    exit 1
fi

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

# Upgrade pip first
echo "Upgrading pip..." >&2
"$PYTHON" -m pip install --upgrade pip --quiet >&2
echo "✓ pip upgraded." >&2
echo "" >&2

# Check if already installed
if _check_package_installed; then
    echo "✓ Package already installed." >&2
    echo "" >&2
    echo "Setup complete!" >&2
    echo "" >&2
    _print_usage_info
    exit 0
fi

# Try to install using available package managers
INSTALL_SUCCESS=false

# Try Poetry first (if poetry.lock exists)
if [ -f "${PROJECT_ROOT}/poetry.lock" ] && command -v poetry >/dev/null 2>&1; then
    echo "Using Poetry to install dependencies..." >&2
    if poetry install --with dev 2>&1; then
        INSTALL_SUCCESS=true
        echo "✓ Dependencies installed with Poetry." >&2
    else
        echo "Warning: Poetry installation failed, trying alternatives..." >&2
    fi
fi

# Try uv if Poetry didn't work
if [ "$INSTALL_SUCCESS" = false ]; then
    # Install or find uv
    UV_AVAILABLE=false
    
    if [ -f "$UV" ]; then
        UV_AVAILABLE=true
        echo "Using uv from virtual environment..." >&2
    elif command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then
        UV_AVAILABLE=true
        UV="uv"
        echo "Using system uv..." >&2
    else
        echo "Installing uv..." >&2
        if "$PYTHON" -m pip install uv --quiet >&2; then
            UV_AVAILABLE=true
            echo "✓ uv installed." >&2
        fi
    fi
    
    if [ "$UV_AVAILABLE" = true ]; then
        echo "Installing dependencies with uv..." >&2
        if [ -f "$UV" ]; then
            if "$UV" pip install -e ".[dev]" 2>&1; then
                INSTALL_SUCCESS=true
                echo "✓ Dependencies installed with uv." >&2
            fi
        elif "$UV" pip install -e ".[dev]" 2>&1; then
            INSTALL_SUCCESS=true
            echo "✓ Dependencies installed with uv." >&2
        fi
    fi
fi

# Fall back to pip
if [ "$INSTALL_SUCCESS" = false ]; then
    echo "Using pip to install dependencies..." >&2
    if "$PIP" install -e ".[dev]" 2>&1; then
        INSTALL_SUCCESS=true
        echo "✓ Dependencies installed with pip." >&2
    else
        echo "Warning: Failed to install with dev dependencies, trying core dependencies..." >&2
        if "$PIP" install -e . 2>&1; then
            echo "✓ Core dependencies installed. Dev dependencies may be missing." >&2
            echo "  You can install them later with: $PIP install -e \".[dev]\"" >&2
            INSTALL_SUCCESS=true
        else
            echo "Error: Failed to install package" >&2
            exit 1
        fi
    fi
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
