#!/bin/bash
# Start script for MVG Departures Inky Display (real hardware)
# Assumes dependencies are already installed via ./scripts/setup.sh
# Works from any directory

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
    else
        PYTHON="${VENV_PATH}/Scripts/python.exe"
    fi
    echo "Using virtual environment: ${VENV_PATH}" >&2
else
    echo "Error: No virtual environment found." >&2
    echo "Please run setup first:" >&2
    echo "  ./scripts/setup.sh        (for Raspberry Pi with hardware support)" >&2
    exit 1
fi

# Verify packages are installed
if ! "$PYTHON" -c "import mvg_departures" 2>/dev/null; then
    echo "Error: Parent package 'mvg_departures' not installed." >&2
    echo "Please run setup first:" >&2
    echo "  ./scripts/setup.sh        (for Raspberry Pi with hardware support)" >&2
    exit 1
fi

if ! "$PYTHON" -c "import mvg_departures_inky" 2>/dev/null; then
    echo "Error: Package 'mvg_departures_inky' not installed." >&2
    echo "Please run setup first:" >&2
    echo "  ./scripts/setup.sh        (for Raspberry Pi with hardware support)" >&2
    exit 1
fi

if ! "$PYTHON" -c "import inky" 2>/dev/null; then
    echo "Error: Hardware package 'inky' not installed." >&2
    echo "Please run setup first:" >&2
    echo "  ./scripts/setup.sh        (for Raspberry Pi with hardware support)" >&2
    exit 1
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
