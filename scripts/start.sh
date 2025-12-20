#!/bin/bash
# Simple start script for MVG Departures
# Works from any directory, automatically handles venv and dependencies

set -e

# Find project root (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "$PROJECT_ROOT"

# Find virtual environment
VENV_PATH=""
for venv_name in .venv venv env .env; do
    if [ -d "${PROJECT_ROOT}/${venv_name}" ]; then
        if [ -f "${PROJECT_ROOT}/${venv_name}/bin/python" ] || [ -f "${PROJECT_ROOT}/${venv_name}/Scripts/python.exe" ]; then
            VENV_PATH="${PROJECT_ROOT}/${venv_name}"
            break
        fi
    fi
done

# Determine Python executable
if [ -n "$VENV_PATH" ]; then
    if [ -f "${VENV_PATH}/bin/python" ]; then
        PYTHON="${VENV_PATH}/bin/python"
        PIP="${VENV_PATH}/bin/pip"
        UV="${VENV_PATH}/bin/uv"
    else
        PYTHON="${VENV_PATH}/Scripts/python.exe"
        PIP="${VENV_PATH}/Scripts/pip.exe"
        UV="${VENV_PATH}/Scripts/uv.exe"
    fi
    echo "Using virtual environment: ${VENV_PATH}" >&2
else
    PYTHON="python3"
    PIP="pip3"
    UV="uv"
    echo "No virtual environment found, using system Python" >&2
fi

# Check if package is installed by trying to import it
if ! "$PYTHON" -c "import mvg_departures" 2>/dev/null; then
    echo "Package not installed. Installing..." >&2
    echo "" >&2
    
    # Try uv first, then pip
    if command -v "$UV" >/dev/null 2>&1 && "$UV" --version >/dev/null 2>&1; then
        echo "Installing with uv..." >&2
        "$UV" pip install -e . || {
            echo "uv failed, trying pip..." >&2
            "$PIP" install -e . || {
                echo "Error: Failed to install package" >&2
                exit 1
            }
        }
    else
        echo "Installing with pip..." >&2
        "$PIP" install -e . || {
            echo "Error: Failed to install package" >&2
            exit 1
        }
    fi
    echo "Package installed successfully!" >&2
    echo "" >&2
fi

# Run the application
echo "Starting MVG Departures..." >&2
echo "Press Ctrl+C to stop" >&2
echo "" >&2

"$PYTHON" -m mvg_departures.main
