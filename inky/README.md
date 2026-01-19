# MVG Departures - Inky Display

This is the Inky e-ink display version of the MVG departures application, designed for Pimoroni Inky Impression displays (targeting 7.5" displays in portrait mode - 480x800 pixels).

## Features

- Static e-ink display (no animations)
- Vertical fill layout - automatically fits all departures
- Dynamic font sizing to fit all destinations
- Route icons and numbers on the left
- Destination names in the middle
- Platform information on the right
- Support for alternating absolute/relative time display (configurable)

## Installation

### Quick Setup with Scripts

**For Raspberry Pi (with hardware support):**
```bash
cd inky
./scripts/setup.sh
```

**For macOS/Windows (development mode, mock only):**
```bash
cd inky
./scripts/setup_dev.sh
```

**Note for macOS:** The setup script will automatically install the Cairo library via Homebrew (if Homebrew is installed). If you don't have Homebrew, install it from https://brew.sh, or manually install Cairo:
```bash
brew install cairo librsvg pkg-config
```

### Manual Installation

1. First, install the parent project:
```bash
cd ..
pip install -e .
```

2. Then install the Inky version:

**For development/testing (mock mode, works on macOS/Windows):**
```bash
cd inky
pip install -e .
```

**For Raspberry Pi with hardware (Linux only):**
```bash
cd inky
pip install -e ".[hardware]"
```

The hardware dependencies (`inky` library and its Linux-specific dependencies) are optional and only needed when using real Inky hardware. On macOS/Windows, the project will automatically use mock mode.

## Configuration

Use the same `config.toml` file as the main project. The Inky adapter will use the first route configuration.

You can specify a custom config file using the `CONFIG_FILE` environment variable:

```bash
CONFIG_FILE=my.config.toml ./scripts/start.sh
```

Or set it in your environment:

```bash
export CONFIG_FILE=my.config.toml
./scripts/start.sh
```

## Usage

### Quick Start with Scripts

1. **Setup** (first time only):
   ```bash
   cd inky
   ./scripts/setup.sh
   ```

2. **Run with real hardware**:
   ```bash
   ./scripts/start.sh
   ```

3. **Run in mock mode** (saves PNGs, no hardware needed):
   ```bash
   ./scripts/run_mock.sh
   ```

### Configuration

The scripts support the `CONFIG_FILE` environment variable to specify a custom config file:

```bash
CONFIG_FILE=my.config.toml ./scripts/start.sh
```

Or for mock mode:

```bash
CONFIG_FILE=my.config.toml ./scripts/run_mock.sh
```

### Manual Usage

#### With Real Hardware

```bash
mvg-departures-inky
```

Or:

```bash
python -m mvg_departures_inky.main
```

#### Testing Without Hardware (Mock Mode)

You can test the rendering without having the Inky display connected by using mock mode:

```bash
INKY_MOCK_MODE=true mvg-departures-inky
```

Or set the output directory:

```bash
INKY_MOCK_MODE=true INKY_MOCK_OUTPUT_DIR=./output mvg-departures-inky
```

In mock mode, the adapter will:
- Use a software mock of the Inky display
- Save rendered images as PNG files instead of displaying on hardware
- Allow you to visually inspect the layout, fonts, and content
- Work on any system (not just Raspberry Pi)

This is useful for:
- Development and testing without hardware
- CI/CD pipelines
- Layout validation
- Font size testing
- Visual debugging

## Requirements

- Raspberry Pi with Inky Impression display connected (for hardware mode)
- Python 3.12+
- Inky library installed (via pip or system package, Linux only)
- **macOS development:** Cairo library (installed automatically by setup script if Homebrew is available)
  - If Homebrew is not available, install manually: `brew install cairo librsvg pkg-config`
