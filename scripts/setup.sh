#!/bin/bash
# Setup script for MVG Departures
# Creates virtual environment and installs all dependencies

set -e

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

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
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
    echo "Virtual environment created." >&2
    echo "" >&2
else
    echo "Virtual environment already exists at ${VENV_PATH}" >&2
    echo "" >&2
fi

# Determine Python and pip paths
if [ -f "${VENV_PATH}/bin/python" ]; then
    PYTHON="${VENV_PATH}/bin/python"
    PIP="${VENV_PATH}/bin/pip"
    UV="${VENV_PATH}/bin/uv"
else
    PYTHON="${VENV_PATH}/Scripts/python.exe"
    PIP="${VENV_PATH}/Scripts/pip.exe"
    UV="${VENV_PATH}/Scripts/uv.exe"
fi

# Install uv if not available
if [ ! -f "$UV" ] && (! command -v uv >/dev/null 2>&1 || ! uv --version >/dev/null 2>&1); then
    echo "Installing uv..." >&2
    # Install uv into the virtual environment using pip
    "$PYTHON" -m pip install uv >/dev/null 2>&1
    echo "uv installed in virtual environment." >&2
    echo "" >&2
elif [ -f "$UV" ]; then
    echo "uv found in virtual environment." >&2
    echo "" >&2
elif command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then
    echo "Using system uv..." >&2
    echo "" >&2
else
    # Last resort: install uv system-wide
    echo "Installing uv system-wide..." >&2
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1
    export PATH="$HOME/.cargo/bin:$PATH"
    echo "uv installed." >&2
    echo "" >&2
fi

# Upgrade pip
echo "Upgrading pip..." >&2
"$PYTHON" -m pip install --upgrade pip >/dev/null 2>&1
echo "pip upgraded." >&2
echo "" >&2

# Install package and dependencies
echo "Installing package and dependencies..." >&2
echo "" >&2

# Try uv first, then pip
INSTALL_SUCCESS=false

if command -v uv >/dev/null 2>&1 && uv --version >/dev/null 2>&1; then
    echo "Using uv to install dependencies..." >&2
    if [ -f "$UV" ]; then
        if "$UV" pip install -e ".[dev]"; then
            INSTALL_SUCCESS=true
        elif uv pip install -e ".[dev]"; then
            INSTALL_SUCCESS=true
        fi
    elif uv pip install -e ".[dev]"; then
        INSTALL_SUCCESS=true
    fi
fi

if [ "$INSTALL_SUCCESS" = false ]; then
    echo "Using pip to install dependencies..." >&2
    if ! "$PIP" install -e ".[dev]"; then
        echo "Error: Failed to install dependencies" >&2
        echo "Trying to install core dependencies first..." >&2
        "$PIP" install -e . || {
            echo "Error: Failed to install package" >&2
            exit 1
        }
    fi
fi

echo "" >&2
echo "Setup complete!" >&2
echo "" >&2
echo "To use the commands, either:" >&2
echo "  1. Activate the virtual environment:" >&2
echo "     source .venv/bin/activate" >&2
echo "  2. Or use the full path:" >&2
echo "     .venv/bin/mvg-config search \"Station Name\"" >&2
echo "" >&2
echo "You can now:" >&2
echo "  - Run the application: ./scripts/start.sh" >&2
echo "  - Use mvg-config: .venv/bin/mvg-config search \"Station Name\"" >&2
echo "  - Run tests: .venv/bin/pytest" >&2
echo "  - Run linters: .venv/bin/ruff check . && .venv/bin/mypy src/" >&2
echo "" >&2

