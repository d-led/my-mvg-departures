#!/bin/bash
# Start script for MVG Departures Inky Display (real hardware)
# Works from any directory, automatically handles venv and dependencies

set -e

# Find project root (where this script is located)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INKY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARENT_ROOT="$(cd "${INKY_ROOT}/.." && pwd)"

cd "$INKY_ROOT"

# Find virtual environment (use parent's venv)
VENV_PATH=""
for venv_name in .venv venv env .env; do
    if [ -d "${PARENT_ROOT}/${venv_name}" ]; then
        if [ -f "${PARENT_ROOT}/${venv_name}/bin/python" ] || [ -f "${PARENT_ROOT}/${venv_name}/Scripts/python.exe" ]; then
            VENV_PATH="${PARENT_ROOT}/${venv_name}"
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

# Check if parent package is installed
if ! "$PYTHON" -c "import mvg_departures" 2>/dev/null; then
    echo "Parent package not installed. Installing..." >&2
    echo "" >&2
    
    cd "$PARENT_ROOT"
    # Try uv first, then pip
    if command -v "$UV" >/dev/null 2>&1 && "$UV" --version >/dev/null 2>&1; then
        echo "Installing parent with uv..." >&2
        "$UV" pip install -e . || {
            echo "uv failed, trying pip..." >&2
            "$PIP" install --prefer-binary -e . || {
                echo "Error: Failed to install parent package" >&2
                exit 1
            }
        }
    else
        echo "Installing parent with pip..." >&2
        "$PIP" install --prefer-binary -e . || {
            echo "Error: Failed to install parent package" >&2
            exit 1
        }
    fi
    cd "$INKY_ROOT"
    echo "Parent package installed successfully!" >&2
    echo "" >&2
fi

# Check if inky package is installed (with hardware dependencies)
if ! "$PYTHON" -c "import mvg_departures_inky" 2>/dev/null || ! "$PYTHON" -c "import inky" 2>/dev/null; then
    echo "Inky package not installed. Installing..." >&2
    echo "" >&2
    
    # Try uv first, then pip
    if command -v "$UV" >/dev/null 2>&1 && "$UV" --version >/dev/null 2>&1; then
        echo "Installing with uv (including hardware support)..." >&2
        "$UV" pip install -e '.[hardware]' || {
            echo "uv failed, trying pip..." >&2
            "$PIP" install --prefer-binary -e '.[hardware]' || {
                echo "Error: Failed to install inky package with hardware support" >&2
                exit 1
            }
        }
    else
        echo "Installing with pip (including hardware support)..." >&2
        "$PIP" install --prefer-binary -e '.[hardware]' || {
            echo "Error: Failed to install inky package with hardware support" >&2
            exit 1
        }
    fi
    echo "Inky package installed successfully!" >&2
    echo "" >&2
fi

# Run the application (real hardware mode)
echo "Starting MVG Departures Inky Display (real hardware)..." >&2
if [ -n "${CONFIG_FILE:-}" ]; then
    echo "Using config file: $CONFIG_FILE" >&2
fi
echo "Press Ctrl+C to stop" >&2
echo "" >&2

# Ensure we're not in mock mode
export INKY_MOCK_MODE=false

"$PYTHON" -m mvg_departures_inky.main
