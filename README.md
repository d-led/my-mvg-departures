# MVG Departures

[![CI](https://github.com/YOUR_USERNAME/my_mvg_departures/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/my_mvg_departures/actions/workflows/ci.yml)

A server-side rendered live dashboard for Munich public transport (MVG) departures. Featuring a responsive and live web UI. Usable on various screen sizes.

![Giesing departures screenshot](./docs/img/giesing-screenshot.png)

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

#### iPad Deployment with Guided Access (Kiosk Mode)

This dashboard is perfect for deployment on an iPad as a permanent departure display. Apple's Guided Access feature allows you to lock the iPad to a single app, creating a kiosk-like experience.

**Prerequisites:**

- iPad (any model with iOS support)
- The server running and accessible on your network
- Safari browser (or any modern browser)

**Setup Steps:**

1. **Start the Server:**

   ```bash
   # On your server/computer, start the application
   ./scripts/start.sh
   # Or if running as a service:
   sudo service mvg-departures start
   ```

2. **Configure iPad Network:**

   - Connect iPad to the same network as your server
   - Note the server's IP address (e.g., `192.168.1.100:8000`)

3. **Open Dashboard in Safari:**

   - Open Safari on the iPad
   - Navigate to `http://YOUR_SERVER_IP:8000` (replace with your server's IP)
   - Wait for the page to load completely
   - Tap the Share button (square with arrow)
   - Select "Add to Home Screen"
   - Give it a name like "MVG Departures"
   - Tap "Add"

4. **Enable Guided Access:**

   - Open iPad Settings → Accessibility → Guided Access
   - Toggle "Guided Access" to ON
   - Tap "Passcode Settings" → "Set Guided Access Passcode"
   - Enter a passcode (you'll need this to exit Guided Access)
   - Optionally enable "Accessibility Shortcut" for quick access

5. **Activate Guided Access:**

   - Open the "MVG Departures" app from the home screen
   - Triple-click the Home button (or Side button on newer iPads)
   - If prompted, enter your passcode
   - Tap "Start" in the top-right corner
   - The iPad is now locked to this app

6. **Configure Guided Access Options (Optional):**

   - While in Guided Access setup, you can:
     - Disable touch in certain areas (tap areas to disable)
     - Disable motion (prevent screen rotation)
     - Disable buttons (Home button, volume buttons, etc.)
     - Set time limits (auto-exit after a period)

7. **Exit Guided Access:**
   - Triple-click the Home/Side button
   - Enter your Guided Access passcode
   - Tap "End" in the top-left corner

**Tips for Best Experience:**

- **Keep iPad Charged:** Use a wall charger or dock to keep the iPad powered
- **Auto-Lock Settings:** Set iPad to never auto-lock (Settings → Display & Brightness → Auto-Lock → Never or another setting if you have physical access to the ipad to wake the screen up)
- **Screen Brightness:** Adjust to your preference, or enable Auto-Brightness
- **Network Stability:** Ensure stable Wi-Fi connection for reliable updates
- **Wall Mount:** Consider a wall mount or stand for permanent installation
- **Full Screen:** The dashboard is designed to work in full-screen mode

**Troubleshooting:**

- **Dashboard not updating:** Check that the server is running and accessible
- **Connection issues:** Verify iPad and server are on the same network
- **Page refresh needed:** Exit and re-enter Guided Access to reload the page
- **WebSocket errors:** Check server logs for connection issues

**Alternative: Using Shortcuts App for Auto-Launch**

For even more automation, you can use the Shortcuts app to automatically open the dashboard when the iPad wakes:

1. Open Shortcuts app
2. Create a new automation: "When iPad wakes"
3. Add action: "Open URLs" → Enter your dashboard URL
4. Disable "Ask Before Running"
5. The dashboard will automatically open when the iPad wakes

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

## Why This Dashboard?

### The Problem with Plain Departure Displays

Traditional departure displays show a simple list of upcoming departures from a single stop. While this works for basic information, it falls short when you need to make strategic decisions about your journey.

**Real-world scenario:** You're at home and need to get to work. You check multiple stops:

- Your local stop (e.g., "Giesing")
- A transfer stop (e.g., "Marienplatz")
- Your destination stop

A plain display shows you raw departure times from each stop, but your brain has to:

1. **Remember** departure times from multiple stops
2. **Calculate** transfer windows and connection possibilities
3. **Compare** different route options
4. **Decide** which combination minimizes waiting time

This mental calculation becomes overwhelming when you're dealing with:

- Multiple routes per stop
- Different directions (some going your way, some not)
- Transfer connections with tight windows
- Real-time delays that affect your strategy

### How This Dashboard Helps

**Direction Grouping for Quick Comprehension:**
Instead of scrolling through a long list of mixed destinations, departures are grouped by direction (e.g., "->Balanstr.", "->Klinikum"). This lets you instantly see:

- Which routes are going your way
- How many options you have in each direction
- The timing spread across your preferred routes

**Strategic Limiting:**
By limiting departures per route and per group, the dashboard shows you the **most relevant information** without cognitive overload:

- **`max_departures_per_route`**: Shows 1-2 departures per route, so you see the next immediate options without being overwhelmed by future departures of the same route
- **`max_departures_per_stop`**: Limits total departures per direction, focusing on the near-term decisions you need to make

This design philosophy recognizes that **you don't need to see every departure**—you need to see the departures that matter for your immediate decision-making. The limits ensure the information density matches your cognitive capacity for quick strategic planning.

**Result:** Instead of mental arithmetic across multiple stops, you can quickly scan grouped departures, identify your best options, and make confident decisions about when to leave and which route to take.

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
