#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SPA_DIR"

echo "Starting development server..."

npm run dev
