#!/bin/bash
# KTEL Chania (Crete) CLI: list stations or fetch departures.
# Usage: ./scripts/chania-config.sh [command] [options]
#        ./scripts/chania-config.sh              # show help
#        ./scripts/chania-config.sh stations     # list all stations with IDs
#        ./scripts/chania-config.sh departures 11 [--date YYYY-MM-DD] [--limit N]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

if [ -d "$PROJECT_ROOT/.venv" ]; then
    CHANIA_CONFIG="$PROJECT_ROOT/.venv/bin/chania-config"
else
    CHANIA_CONFIG=""
fi

if [ -z "$CHANIA_CONFIG" ] || [ ! -f "$CHANIA_CONFIG" ]; then
    PYTHON="${PYTHON:-python3}"
    if [ -d "$PROJECT_ROOT/.venv" ]; then
        PYTHON="$PROJECT_ROOT/.venv/bin/python"
    fi
    if [ -z "$PYTHONPATH" ] && [ -d "$PROJECT_ROOT/src" ]; then
        export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"
    fi
    exec "$PYTHON" -m mvg_departures.cli_chania "$@"
else
    exec "$CHANIA_CONFIG" "$@"
fi
