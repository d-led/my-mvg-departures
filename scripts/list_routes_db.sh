#!/bin/bash
# List routes for DB stations
# Usage: ./scripts/list_routes_db.sh "Augsburg Hbf" or ./scripts/list_routes_db.sh 8000013

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if venv exists
if [ -d "$PROJECT_ROOT/.venv" ]; then
    DB_CONFIG="$PROJECT_ROOT/.venv/bin/db-config"
else
    # Try to find db-config in PATH
    if command -v db-config >/dev/null 2>&1; then
        DB_CONFIG="db-config"
    else
        echo "Error: Virtual environment not found and db-config not in PATH" >&2
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
    echo "  $0 8000013" >&2
    exit 1
fi

# Run the command
exec "$DB_CONFIG" routes "$@"

