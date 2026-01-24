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

# Svelte check (includes a11y diagnostics)
echo "Running Svelte check..."
npm run check || {
  echo "✗ Svelte check failed"
  exit 1
}

# Linting
echo "Running ESLint..."
npm run lint || {
  echo "✗ Linting failed"
  exit 1
}

# Prettier formatting
echo "Reformatting with Prettier..."
npm run prettier
echo "✓ Prettier formatting complete"

# Unit tests
echo "Running unit tests..."
npm test || {
  echo "✗ Tests failed"
  exit 1
}

echo "✓ All checks passed!"
