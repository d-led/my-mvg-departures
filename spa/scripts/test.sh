#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPA_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$SPA_DIR"

echo "Running quality checks and tests..."

# Type checking
echo "Running TypeScript type check..."
npm run typecheck || {
  echo "✗ Type check failed"
  exit 1
}

# Linting
echo "Running ESLint..."
npm run lint || {
  echo "✗ Linting failed"
  exit 1
}

# Prettier check
echo "Running Prettier check..."
npm run prettier:check || {
  echo "✗ Prettier check failed"
  exit 1
}

# Unit tests
echo "Running unit tests..."
npm test || {
  echo "✗ Tests failed"
  exit 1
}

echo "✓ All checks passed!"
