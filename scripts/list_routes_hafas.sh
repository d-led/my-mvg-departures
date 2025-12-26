#!/bin/bash
# List routes for HAFAS stations
# Usage: ./scripts/list_routes_hafas.sh "Augsburg Hbf" or ./scripts/list_routes_hafas.sh 9000589

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if venv exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    HAFAS_CONFIG="$PROJECT_ROOT/.venv/bin/hafas-config"
else
    # Try to find hafas-config in PATH
    if command -v hafas-config >/dev/null 2>&1; then
        HAFAS_CONFIG="hafas-config"
    else
        echo "Error: Virtual environment not found and hafas-config not in PATH" >&2
        echo "Please run: ./scripts/setup.sh" >&2
        exit 1
    fi
fi

# Check if query is provided
if [ $# -eq 0 ]; then
    echo "Usage: $0 <station_name_or_id>" >&2
    echo "" >&2
    echo "Examples:" >&2
    echo "  $0 \"Augsburg Hbf\"" >&2
    echo "  $0 9000589" >&2
    echo "" >&2
    echo "Note: If you provide a station ID, it will detect the profile." >&2
    echo "      If you provide a station name, it will search across all profiles." >&2
    exit 1
fi

QUERY="$1"

# Check if query looks like a station ID (numeric or alphanumeric without spaces)
if [[ "$QUERY" =~ ^[0-9A-Za-z]+$ ]] && [[ ! "$QUERY" =~ [[:space:]] ]]; then
    # Treat as station ID - use detect command
    exec "$HAFAS_CONFIG" detect "$QUERY"
else
    # Treat as station name - use search command
    exec "$HAFAS_CONFIG" search "$QUERY"
fi

