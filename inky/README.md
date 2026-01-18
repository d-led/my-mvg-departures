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

1. First, install the parent project:
```bash
cd ..
pip install -e .
```

2. Then install the Inky version:
```bash
cd inky
pip install -e .
```

Alternatively, you can install both at once:
```bash
# From project root
pip install -e .
pip install -e ./inky
```

## Configuration

Use the same `config.toml` file as the main project. The Inky adapter will use the first route configuration.

## Usage

```bash
mvg-departures-inky
```

Or:

```bash
python -m mvg_departures_inky.main
```

## Requirements

- Raspberry Pi with Inky Impression display connected
- Python 3.12+
- Inky library installed (via pip or system package)
