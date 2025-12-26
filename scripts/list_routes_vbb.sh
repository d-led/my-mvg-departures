#!/bin/bash
# List routes for a VBB (Berlin) station
# Usage: ./scripts/list_routes_vbb.sh <station_name_or_id>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Determine Python and vbb-config command
if [ -d "$PROJECT_ROOT/.venv" ]; then
    PYTHON="$PROJECT_ROOT/.venv/bin/python"
    VBB_CONFIG="$PROJECT_ROOT/.venv/bin/vbb-config"
else
    PYTHON="python3"
    # Try to find vbb-config in PATH
    if command -v vbb-config >/dev/null 2>&1; then
        VBB_CONFIG="vbb-config"
    else
        VBB_CONFIG=""
    fi
fi

# Check if query is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <station_name>" >&2
    echo "Example: $0 \"Zoologischer Garten\"" >&2
    exit 1
fi

QUERY="$*"

# If vbb-config doesn't exist, use Python module directly
if [ -z "$VBB_CONFIG" ] || [ ! -f "$VBB_CONFIG" ]; then
    # Use Python module directly (requires package to be installed or PYTHONPATH set)
    # Set PYTHONPATH to include the src directory if it's not already set
    if [ -z "$PYTHONPATH" ] && [ -d "$PROJECT_ROOT/src" ]; then
        export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    fi
    exec "$PYTHON" -m mvg_departures.cli_vbb search "$QUERY"
else
    exec "$VBB_CONFIG" search "$QUERY"
fi

