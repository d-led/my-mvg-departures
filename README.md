# MVG Departures

[![CI](https://github.com/YOUR_USERNAME/my_mvg_departures/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/my_mvg_departures/actions/workflows/ci.yml)

A well-architected, server-side rendered live display application for Munich public transport (MVG) departures. Built with Python 3.12, following ports-and-adapters architecture principles, and featuring a responsive web UI using PyView and DaisyUI.

## Features

- **Live Departure Updates**: Real-time departure information from MVG API
- **Configurable Stops**: Monitor multiple stops with custom direction groupings
- **Responsive Design**: Clean, modern UI that works on all screen sizes
- **Dark/Light Mode**: Automatic theme switching based on system preferences
- **Flexible Time Display**: Show departures "in minutes" or "at" specific times
- **Direction Grouping**: Group routes by configurable direction names (e.g., "->Giesing")
- **12-Factor App**: Configuration via environment variables
- **Multiple Deployment Options**: Docker container or init.d service

## Architecture

This application follows the **ports-and-adapters** (hexagonal) architecture pattern:

- **Domain Layer**: Core business models and interfaces (ports)
- **Application Layer**: Use cases and business logic
- **Adapters Layer**: External system integrations (MVG API, Web UI, Config)

This design allows for easy extension with new output devices (e.g., e-ink displays, LED matrices) without changing core logic.

## Requirements

- Python 3.12+
- Virtual environment tool: `uv`, `poetry`, `pipenv`, or `pyenv`

## Installation

### Quick Setup (Recommended)

The easiest way to set up the project is using the setup script:

```bash
# Clone the repository
git clone <repository-url>
cd my_mvg_departures

# Run the setup script (creates venv and installs dependencies)
./scripts/setup.sh
```

This will:
- Create a virtual environment (`.venv`)
- Install all dependencies
- Install the package in editable mode
- Make `mvg-config` and `mvg-departures` commands available

### Manual Setup

#### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone <repository-url>
cd my_mvg_departures
uv sync
```

#### Using Poetry

```bash
poetry install
poetry shell
```

#### Using pip

```bash
python3.12 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

## Configuration

Configuration follows the [12-factor app](https://12factor.net/config) methodology using environment variables, with TOML files for complex configurations.

**By default, the application uses `config.example.toml`** which includes a pre-configured Giesing stop. You can customize this file or create your own `config.toml`.

### Quick Start

The application works out of the box with the example configuration:

```bash
# Just start it - uses config.example.toml by default
./scripts/start.sh
```

### Configuration Methods

#### Method 1: TOML File (Recommended)

Copy and customize the example configuration:

```bash
cp config.example.toml config.toml
# Edit config.toml with your stops
```

Or set a custom path via environment variable:

```bash
export CONFIG_FILE=/path/to/your/config.toml
```

#### Method 2: Environment Variables

Copy `env.example` to `.env` and configure:

```bash
cp env.example .env
```

### Environment Variables

- `HOST`: Server host (default: `0.0.0.0`)
- `PORT`: Server port (default: `8000`)
- `RELOAD`: Enable auto-reload for development (default: `false`)
- `TIME_FORMAT`: Display format - `minutes` or `at` (default: `minutes`)
- `REFRESH_INTERVAL_SECONDS`: Update interval in seconds (default: `30`)
- `CONFIG_FILE`: Path to TOML configuration file (default: `config.example.toml`)
- `STOPS_CONFIG`: JSON array of stop configurations (fallback if TOML not available)

### Stop Configuration

Stops can be configured either via TOML file (recommended) or JSON environment variable. The TOML file provides a cleaner structure for complex configurations with multiple stops and direction mappings.

**Example TOML Configuration (config.toml):**

```toml
[display]
departures_per_page = 5
page_rotation_seconds = 8
pagination_enabled = true

[[stops]]
station_id = "de:09162:100"
station_name = "Giesing"
max_departures_per_stop = 30

[stops.direction_mappings]
"->Balanstr." = ["Messestadt", "Messestadt West"]
"->Klinikum" = ["Klinikum", "Klinikum Großhadern"]
"->Tegernseer" = ["Ackermannbogen", "Tegernseer"]
"->Stadt" = ["Gondrellplatz", "Marienplatz"]
```

**Example JSON Configuration (for STOPS_CONFIG env var):**

```json
[
  {
    "station_id": "de:09162:100",
    "station_name": "Giesing",
    "direction_mappings": {
      "->Balanstr.": ["Messestadt", "Messestadt West"],
      "->Klinikum": ["Klinikum", "Klinikum Großhadern"],
      "->Tegernseer": ["Ackermannbogen", "Tegernseer"],
      "->Stadt": ["Gondrellplatz", "Marienplatz"]
    },
    "max_departures_per_stop": 30
  }
]
```

**How Direction Mappings Work:**

- **Keys** (e.g., "->Giesing") are user-defined direction names that appear as headers in the UI
- **Values** are lists of destination patterns that match route destinations
- Patterns match destinations using substring matching (case-insensitive)
- Routes whose destinations don't match any pattern appear in an "Other" group
- You can group multiple different destinations under one direction name (e.g., all routes going toward Giesing area)

**Finding Station IDs and Configuring Stops:**

📖 **See [docs/FINDING_STOP_IDS.md](docs/FINDING_STOP_IDS.md) for a complete guide on finding stop IDs.**

Quick start - use the `mvg-config` CLI tool to search for stations, view details, and generate configuration:

```bash
# Search for stations by name
mvg-config search "Giesing"

# Show detailed information about a station
mvg-config info de:09162:100

# List all available routes and destinations for a station (by ID)
mvg-config routes de:09162:100

# Search for stations by name and show routes for each match
mvg-config routes "Giesing"

# Generate a TOML config snippet (ready to paste into config.toml)
mvg-config generate de:09162:100 "Giesing"
```

The `generate` command creates a starter configuration with suggested direction mappings based on available destinations. You can then customize the direction names and groupings in your TOML file.

**Alternative: Using the helper scripts:**

```bash
# Find station ID
python scripts/find_station.py "Giesing" München

# List routes for a station (by name or ID)
./scripts/list_routes.sh "Giesing"
./scripts/list_routes.sh de:09162:100
```

**Or using the MVG API directly:**

```python
from mvg import MvgApi

station = MvgApi.station("Giesing, München")
print(station["id"])  # e.g., "de:09162:100"
```

## Usage

### Development

```bash
# Set environment variables
export STOPS_CONFIG='[{"station_id": "de:09162:100", "station_name": "Giesing", "direction_mappings": {"->Balanstr.": ["Messestadt"]}}]'

# Run the application
python -m mvg_departures.main

# Or using the entry point
mvg-departures
```

Access the web UI at `http://localhost:8000`

### Production

#### Docker

```bash
# Build the image
docker build -t mvg-departures .

# Run with docker-compose
docker-compose up -d

# Or run directly
docker run -d \
  -p 8000:8000 \
  -e STOPS_CONFIG='[{"station_id": "de:09162:100", "station_name": "Giesing", "direction_mappings": {"->Balanstr.": ["Messestadt"]}}]' \
  mvg-departures
```

#### Init.d Service

```bash
# Install as a system service (requires root)
sudo ./scripts/install-service.sh

# Configure stops - copy and edit the TOML config file
sudo cp /opt/mvg-departures/config.example.toml /opt/mvg-departures/config.toml
sudo nano /opt/mvg-departures/config.toml

# Or configure via environment variables in .env
sudo nano /opt/mvg-departures/.env

# Start the service
sudo service mvg-departures start

# Check status
sudo service mvg-departures status

# View logs
sudo tail -f /var/log/mvg-departures.log
```

## Development

### Running Tests

```bash
# Using pytest directly
pytest

# With coverage
pytest --cov=mvg_departures --cov-report=html

# Using uv
uv run pytest
```

### Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

## UI Features

### Responsive Layout

- **Route Number**: Fixed position on the left (3-4rem width)
- **Destination**: Flexible middle section with text overflow handling
- **Time**: Fixed position on the right (4-5rem width)
- **Small Screens**: Automatically adjusts font sizes and spacing

### Time Display

- **Minutes Format** (default): Shows "5m", "<1m", or "now"
- **At Format**: Shows "14:30" style times

### Visual Indicators

- **Real-time Data**: Green color for real-time departures
- **Delays**: Warning color for significant delays (>1 minute)
- **Cancelled**: Strikethrough and reduced opacity

## Extending the Application

### Adding a New Output Device

To add support for a new output device (e.g., e-ink display, LED matrix):

1. Create a new adapter in `src/mvg_departures/adapters/` implementing `DisplayAdapter`
2. Use the `DepartureGroupingService` to get grouped departures
3. Update `main.py` to instantiate your adapter instead of `PyViewWebAdapter`

Example structure:

```python
from mvg_departures.domain.ports import DisplayAdapter

class MyDeviceAdapter(DisplayAdapter):
    async def display_departures(self, direction_groups):
        # Render to your device
        pass
    
    async def start(self):
        # Initialize device
        pass
    
    async def stop(self):
        # Cleanup
        pass
```

## License

This project is licensed under the Mozilla Public License 2.0 (MPL-2.0). See `LICENSE` file for details.

## Disclaimer

This project is **not an official project from the Münchner Verkehrsgesellschaft (MVG)**. It uses the unofficial MVG API and is intended for **private, non-commercial, moderate use** only. Please refer to the [MVG imprint](https://www.mvg.de/impressum.html) for usage restrictions.

## Contributing

Contributions are welcome! This project follows **trunk-based development**:

- All development happens in short-lived feature branches
- Feature branches merge directly to `main`
- `main` is always in a deployable state

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for detailed contribution guidelines, including:
- Development workflow
- Branch naming conventions
- Code quality standards
- Testing requirements
- Architecture principles

## Acknowledgments

- [mvg](https://github.com/mondbaron/mvg) - MVG API library
- [pyview](https://github.com/ogrodnek/pyview) - Python LiveView implementation
- [DaisyUI](https://daisyui.com/) - Component library

