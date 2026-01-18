# Fonts Directory

This directory contains font files for the Inky display renderer.

## Required Fonts

### HK Grotesk (Default)

HK Grotesk is the default font family used for rendering:
- **Bold** variant for headers
- **Regular** variant for body text

**Download Instructions:**

1. Visit [Font Library - HK Grotesk](https://fontlibrary.org/en/font/hk-grotesk)
2. Download the following font files:
   - `HKGrotesk-Bold.ttf` (for headers)
   - `HKGrotesk-Regular.ttf` (for body text)
3. Place both files in this directory (`inky/fonts/`)

**License:** SIL Open Font License (OFL) - free for personal and commercial use.

## Alternative Font

### Fredoka One

Fredoka One can be used as an alternative font by setting `font_family = "fredoka_one"` in the configuration.

This font is installed via the `font-fredoka-one` Python package (already in dependencies), so no manual download is needed.

## Font Priority

The renderer tries fonts in this order:

1. **HK Grotesk** (if `font_family = "hk_grotesk"` and font files exist)
2. **Fredoka One** (if `font_family = "fredoka_one"` and package is installed)
3. **System fonts** (DejaVu Sans, Liberation Sans)
4. **Default PIL font** (last resort)
