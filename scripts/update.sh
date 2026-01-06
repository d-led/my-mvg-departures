#!/bin/bash
# Update script for MVG Departures
# Updates all dependencies after pyproject.toml changes
# Supports: Poetry, uv, and pip (in that order of preference)

set -euo pipefail

# Find project root (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

echo "Updating MVG Departures dependencies..." >&2
echo "" >&2

# Determine virtual environment path
VENV_PATH="${PROJECT_ROOT}/.venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at ${VENV_PATH}" >&2
    echo "  Run ./scripts/setup.sh first to create it." >&2
    exit 1
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

# Upgrade pip first
echo "Upgrading pip..." >&2
"$PYTHON" -m pip install --upgrade pip --quiet >&2
echo "✓ pip upgraded." >&2
echo "" >&2

# Try to update using available package managers
UPDATE_SUCCESS=false

# Try Poetry first (if poetry.lock exists)
if [ -f "${PROJECT_ROOT}/poetry.lock" ] && command -v poetry >/dev/null 2>&1; then
    echo "Using Poetry to update dependencies..." >&2
    if poetry update --with dev 2>&1; then
        UPDATE_SUCCESS=true
        echo "✓ Dependencies updated with Poetry." >&2
    else
        echo "Warning: Poetry update failed, trying alternatives..." >&2
    fi
fi

# Try uv if Poetry didn't work
if [ "$UPDATE_SUCCESS" = false ]; then
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
        echo "Updating dependencies with uv..." >&2
        if [ -f "$UV" ]; then
            if "$UV" pip install -e ".[dev]" --upgrade 2>&1; then
                UPDATE_SUCCESS=true
                echo "✓ Dependencies updated with uv." >&2
            fi
        elif "$UV" pip install -e ".[dev]" --upgrade 2>&1; then
            UPDATE_SUCCESS=true
            echo "✓ Dependencies updated with uv." >&2
        fi
    fi
fi

# Fall back to pip
if [ "$UPDATE_SUCCESS" = false ]; then
    echo "Using pip to update dependencies..." >&2
    if "$PIP" install -e ".[dev]" --upgrade 2>&1; then
        UPDATE_SUCCESS=true
        echo "✓ Dependencies updated with pip." >&2
    else
        echo "Error: Failed to update dependencies" >&2
        exit 1
    fi
fi

echo "" >&2
echo "✓ Update complete!" >&2
echo "" >&2

