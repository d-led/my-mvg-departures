# MVG Departures - Inky Display

E-ink display version of the MVG departures application, designed for Pimoroni Inky Impression displays (targeting 7.5" displays in portrait mode - 480x800 pixels).

This version is part of the MVG Departures family. See the [main README](../README.md) for the server-side version and [SPA version](https://d-led.github.io/my-mvg-departures/) for a browser-based alternative.

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

Use the same TOML configuration format as the server-side and SPA versions. The Inky adapter will use the first route configuration from your config file.

> **🎯 Easy Configuration**: Use the **[SPA Configuration Wizard](https://d-led.github.io/my-mvg-departures/)** to generate your TOML config interactively in your browser, then save it for use with the Inky version!

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

### Deployment on Raspberry Pi

For production deployment on Raspberry Pi, use the deployment script:

```bash
cd inky
sudo ./scripts/deploy-rpi.sh
```

This script will:

1. Set up the project and install all dependencies (including numpy via apt to avoid build issues)
2. Install and start the systemd service
3. Configure the service to start automatically on boot

**Manual deployment steps** (if you prefer to do it step by step):

1. **Setup the project:**

   ```bash
   cd inky
   ./scripts/setup.sh
   ```

   This installs all dependencies including hardware support.

2. **Install as systemd service:**
   ```bash
   sudo ./scripts/install-service.sh
   ```

The service will:

- Start automatically on boot
- Restart automatically if it crashes
- Log to systemd journal (view with `journalctl -u mvg-departures-inky -f`)

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
- Python 3.13
- Inky library installed (via pip or system package, Linux only)
- **macOS development:** Cairo library (installed automatically by setup script if Homebrew is available)
  - If Homebrew is not available, install manually: `brew install cairo librsvg pkg-config`

## Troubleshooting

### "No space left on device" error during installation

If you encounter `OSError: [Errno 28] No space left on device` when installing on a Raspberry Pi (especially Pi Zero), this is because pip is trying to build numpy from source, which requires significant temporary space.

**Root cause:** Building numpy from source needs ~500MB+ of temporary space. On Raspberry Pi, `/tmp` is often a tmpfs (RAM-based filesystem) with limited size (typically 214MB), which is insufficient for building numpy and its build dependencies (cmake, patchelf, etc.).

**Solution:** The setup script automatically:

1. Installs numpy via apt first (pre-built binaries, no compilation needed)
2. If apt fails, uses `~/.tmp` instead of `/tmp` for build files (which has more space on the main filesystem)

If installing manually:

1. **Preferred:** Install numpy via apt first:

   ```bash
   sudo apt-get update
   sudo apt-get install -y python3-numpy
   ```

2. **Alternative:** If you must build from source, use a larger temp directory:
   ```bash
   export TMPDIR="${HOME}/.tmp"
   mkdir -p "$TMPDIR"
   pip install -e ".[hardware]"
   ```

This avoids the `/tmp` space limitation.

### "Illegal instruction" error when running

If you get an `Illegal instruction` error when trying to run the application, this means the virtual environment or packages were created on a different architecture or CPU variant and are being run on a different one.

**Common causes:**

- Moving from macOS/Windows (x86_64) to Raspberry Pi (ARM)
- Moving between different Raspberry Pi models (e.g., Pi 2 to Pi Zero - different ARM variants)
- Binary packages compiled for a different CPU architecture

**Solution:** Recreate the virtual environment on the target device:

```bash
cd inky
./scripts/fix-venv-architecture.sh
```

This script will:

1. Remove the existing virtual environment
2. Create a new one for the current architecture/CPU
3. Reinstall all dependencies (including numpy via apt)

**Prevention:** Always create the virtual environment on the target device. If you transfer the project from another machine or different Pi model, don't transfer the `.venv` directory - let it be created fresh on the target device.
