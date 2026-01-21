#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SPA_DIR"

echo "Building SPA for production..."

npm run build

echo "✓ Build complete! Output in dist/"
