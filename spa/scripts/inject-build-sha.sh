#!/bin/bash
# Injects current git short SHA into built SPA and reveals the build-sha element.
# Run from repo root after building the SPA (same as CI does).
# Usage: from repo root: spa/scripts/inject-build-sha.sh
#        or from spa/:   ./scripts/inject-build-sha.sh (DIST_DIR=dist)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DIST_DIR="${DIST_DIR:-$REPO_ROOT/spa/dist}"

if [ ! -f "$DIST_DIR/bundle.js" ]; then
  echo "ERROR: $DIST_DIR/bundle.js not found. Build the SPA first (e.g. from spa/: npm run build)." >&2
  exit 1
fi

SHA="$(git -C "$REPO_ROOT" rev-parse --short HEAD)"
echo "Injecting build SHA: $SHA"

# Portable sed -i (macOS vs GNU)
replace_in_file() {
  local file="$1"
  local pattern="$2"
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i "s/__BUILD_SHA__/$SHA/g" "$file"
  else
    sed -i '' "s/__BUILD_SHA__/$SHA/g" "$file"
  fi
}

remove_hide_block() {
  local file="$1"
  if sed --version 2>/dev/null | grep -q GNU; then
    sed -i '/__BUILD_SHA_HIDE_START__/,/__BUILD_SHA_HIDE_END__/d' "$file"
  else
    sed -i '' '/__BUILD_SHA_HIDE_START__/,/__BUILD_SHA_HIDE_END__/d' "$file"
  fi
}

replace_in_file "$DIST_DIR/bundle.js"
CSS_FILE="$DIST_DIR/css/departures.css"
if [ -f "$CSS_FILE" ]; then
  remove_hide_block "$CSS_FILE"
fi

echo "✓ Build SHA injected. Open the app and check the config dialog footer."
