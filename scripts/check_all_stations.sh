#!/bin/bash
# Check if all stations in a TOML config file can be queried

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <config.toml>"
    echo "Example: $0 config.toml"
    exit 1
fi

CONFIG_FILE="$1"

if [ ! -f "$CONFIG_FILE" ]; then
    echo "Error: Config file '$CONFIG_FILE' not found"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# Check for --raw flag
RAW_FLAG=""
if [ "$2" = "--raw" ]; then
    RAW_FLAG="--raw"
fi

# Run Python script
python3 "$SCRIPT_DIR/check_all_stations.py" "$CONFIG_FILE" $RAW_FLAG

