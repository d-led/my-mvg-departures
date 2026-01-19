#!/bin/bash
# Fix virtual environment architecture mismatch
# Use this if you get "Illegal instruction" errors after transferring the project
# from a different architecture (e.g., macOS x86_64 to Raspberry Pi ARM)
# or between different Raspberry Pi models (e.g., Pi 2 to Pi Zero)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INKY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PARENT_ROOT="$(cd "${INKY_ROOT}/.." && pwd)"

echo "=========================================="
echo "Fixing Virtual Environment Architecture"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Remove the existing virtual environment"
echo "  2. Create a new one for this architecture/CPU"
echo "  3. Reinstall all dependencies"
echo ""
echo "Use this when:"
echo "  - Moving from macOS/Windows to Raspberry Pi"
echo "  - Moving between different Raspberry Pi models (Pi 2, Pi Zero, etc.)"
echo "  - Getting 'Illegal instruction' errors"
echo ""
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 1
fi

echo ""
echo "Step 1: Removing old virtual environment..."
if [ -d "${PARENT_ROOT}/.venv" ]; then
    rm -rf "${PARENT_ROOT}/.venv"
    echo "✓ Removed ${PARENT_ROOT}/.venv"
else
    echo "  No existing venv found"
fi
echo ""

echo "Step 2: Recreating virtual environment for this architecture..."
cd "$PARENT_ROOT"
python3 -m venv .venv
echo "✓ Created new virtual environment"
echo ""

echo "Step 3: Reinstalling dependencies..."
echo "  (This may take a while, especially on Raspberry Pi)"
echo ""

# Source common setup functions
source "${PARENT_ROOT}/scripts/setup-common.sh"

# Setup venv (will detect the newly created one)
setup_venv "$PARENT_ROOT"

# Install parent project
echo "Installing parent project..."
if ! install_with_available_manager "$PARENT_ROOT" ".[dev]"; then
    echo "Error: Failed to install parent project" >&2
    exit 1
fi
echo ""

# Install inky project with hardware support
echo "Installing inky project with hardware support..."
cd "$INKY_ROOT"

# Install numpy via apt first (on Linux)
if [ "$(uname)" = "Linux" ]; then
    install_numpy_for_pi
fi

if ! install_with_available_manager "$INKY_ROOT" ".[dev,hardware]"; then
    echo "Warning: Failed to install with hardware support, trying without..." >&2
    if ! install_with_available_manager "$INKY_ROOT" ".[dev]"; then
        echo "Error: Failed to install inky project" >&2
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "✓ Virtual environment fixed!"
echo "=========================================="
echo ""
echo "You can now run:"
echo "  cd inky && ./scripts/start.sh"
echo ""
