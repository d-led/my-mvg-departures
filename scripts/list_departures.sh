#!/bin/bash
# List live departures for MVG stations
# Usage: ./scripts/list_departures.sh "Giesing" or ./scripts/list_departures.sh de:09162:100
#        ./scripts/list_departures.sh de:09162:1108:4:4  # Filter by specific stop point

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if venv exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    MVG_CONFIG="$PROJECT_ROOT/.venv/bin/mvg-config"
else
    # Try to find mvg-config in PATH
    if command -v mvg-config >/dev/null 2>&1; then
        MVG_CONFIG="mvg-config"
    else
        echo "Error: Virtual environment not found and mvg-config not in PATH" >&2
        echo "Please run: ./scripts/setup.sh" >&2
        exit 1
    fi
fi

# Check if query is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <station_name_or_id> [--limit N] [--json]" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 \"Donnersbergerstr.\"          # Search by name" >&2
    echo "  $0 de:09162:100                  # By station ID" >&2
    echo "  $0 de:09162:100:2:2              # By specific stop point" >&2
    echo "  $0 de:09162:100 --limit 50       # Limit results" >&2
    echo "  $0 de:09162:100 --json           # Output as JSON" >&2
    exit 1
fi

# Run the command
exec "$MVG_CONFIG" departures "$@"

