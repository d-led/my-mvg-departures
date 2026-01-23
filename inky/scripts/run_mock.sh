#!/bin/bash
# Run script for MVG Departures Inky Display (mock mode - saves PNGs)
# Assumes dependencies are already installed via ./scripts/setup.sh or ./scripts/setup_dev.sh
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
    echo "  ./scripts/setup_dev.sh    (for development/macOS)" >&2
    echo "  ./scripts/setup.sh        (for Raspberry Pi)" >&2
    exit 1
fi

# Verify packages are installed
if ! "$PYTHON" -c "import mvg_departures" 2>/dev/null; then
    echo "Error: Parent package 'mvg_departures' not installed." >&2
    echo "Please run setup first:" >&2
    echo "  ./scripts/setup_dev.sh    (for development/macOS)" >&2
    echo "  ./scripts/setup.sh        (for Raspberry Pi)" >&2
    exit 1
fi

if ! "$PYTHON" -c "import mvg_departures_inky" 2>/dev/null; then
    echo "Error: Package 'mvg_departures_inky' not installed." >&2
    echo "Please run setup first:" >&2
    echo "  ./scripts/setup_dev.sh    (for development/macOS)" >&2
    echo "  ./scripts/setup.sh        (for Raspberry Pi)" >&2
    exit 1
fi

# Create output directory for mock images
MOCK_OUTPUT_DIR="${INKY_ROOT}/mock_output"
mkdir -p "$MOCK_OUTPUT_DIR"

# Run the application (mock mode)
echo "Starting MVG Departures Inky Display (MOCK MODE)..." >&2
if [ -n "${CONFIG_FILE:-}" ]; then
    echo "Using config file: $CONFIG_FILE" >&2
fi
echo "Mock images will be saved to: $MOCK_OUTPUT_DIR" >&2
echo "Press Ctrl+C to stop" >&2
echo "" >&2

# Set mock mode environment variables
export INKY_MOCK_MODE=true
export INKY_MOCK_OUTPUT_DIR="$MOCK_OUTPUT_DIR"

"$PYTHON" -m mvg_departures_inky.main
