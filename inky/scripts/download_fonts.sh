#!/bin/bash
# Script to download HK Grotesk fonts for Inky display
# Fonts are downloaded from Font Library (fontlibrary.org)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INKY_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
FONTS_DIR="${INKY_ROOT}/fonts"

echo "Downloading HK Grotesk fonts..." >&2
echo "" >&2

# Create fonts directory if it doesn't exist
mkdir -p "$FONTS_DIR"

# Font Library URLs for HK Grotesk
# Note: These are direct download links from Font Library
# If these URLs don't work, users should download manually from:
# https://fontlibrary.org/en/font/hk-grotesk

FONT_BASE_URL="https://fontlibrary.org/assets/fonts/hk-grotesk"

# Try to download using curl or wget
DOWNLOAD_CMD=""
if command -v curl >/dev/null 2>&1; then
    DOWNLOAD_CMD="curl -L -o"
elif command -v wget >/dev/null 2>&1; then
    DOWNLOAD_CMD="wget -O"
else
    echo "Error: Neither curl nor wget found. Please install one of them." >&2
    echo "" >&2
    echo "Alternatively, download fonts manually:" >&2
    echo "  1. Visit: https://fontlibrary.org/en/font/hk-grotesk" >&2
    echo "  2. Download HKGrotesk-Bold.ttf and HKGrotesk-Regular.ttf" >&2
    echo "  3. Place them in: $FONTS_DIR" >&2
    exit 1
fi

# Note: Font Library doesn't provide direct download links for individual font files
# Users need to download from the website manually
echo "Font Library doesn't provide direct download links for individual files." >&2
echo "" >&2
echo "Please download HK Grotesk fonts manually:" >&2
echo "  1. Visit: https://fontlibrary.org/en/font/hk-grotesk" >&2
echo "  2. Click on 'HK Grotesk Bold' and download the font file" >&2
echo "  3. Click on 'HK Grotesk Regular' and download the font file" >&2
echo "  4. Rename the files to:" >&2
echo "     - HKGrotesk-Bold.ttf" >&2
echo "     - HKGrotesk-Regular.ttf" >&2
echo "  5. Place them in: $FONTS_DIR" >&2
echo "" >&2
echo "After downloading, verify the files exist:" >&2
echo "  ls -la $FONTS_DIR" >&2
