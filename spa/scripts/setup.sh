#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SPA_DIR"

echo "Setting up SPA dependencies..."

if ! command -v node &> /dev/null; then
  echo "Error: Node.js is not installed. Please install Node.js 18 or later."
  exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
  echo "Error: Node.js 18 or later is required. Current version: $(node -v)"
  exit 1
fi

if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
else
  echo "Dependencies already installed. Run 'npm install' to update."
fi

echo "✓ Setup complete!"
