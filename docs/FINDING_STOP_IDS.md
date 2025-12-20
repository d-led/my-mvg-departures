# Finding Stop IDs

This guide explains how to find the station/stop ID needed to configure MVG Departures. Station IDs are unique identifiers in the format `de:09162:XXX` where `XXX` is a numeric identifier.

## Quick Start

The easiest way to find a stop ID is using the `mvg-config` CLI tool:

```bash
# Search for a station by name
mvg-config search "Giesing"

# This will show you the station ID along with other details
```

## Methods to Find Stop IDs

### Method 1: Using mvg-config CLI (Recommended)

The `mvg-config` tool is the most convenient way to find and explore stations.

#### Search for Stations

```bash
mvg-config search "Station Name"
```

**Example:**
```bash
$ mvg-config search "Giesing"

Found 1 station(s):

  Giesing (München)
    ID: de:09162:100
```

#### Get Detailed Information

Once you have a station ID, get detailed information including all available routes:

```bash
mvg-config info de:09162:100
```

**Example output:**
```
Station Information:
  ID: de:09162:100
  Name: Giesing
  Place: München

Routes: 4
  U-Bahn U2: Messestadt, Feldmoching
  Bus 59: Giesing Bahnhof, Ackermannbogen
  Bus 139: Messestadt West, Klinikum
  Tram 18: Gondrellplatz, Marienplatz
```

#### List All Routes

See all routes and destinations for a station:

```bash
mvg-config routes de:09162:100
```

**Example output:**
```
Station: Giesing (de:09162:100)
Place: München

Available Routes (4):
======================================================================

U-Bahn U2:
  → Messestadt
  → Feldmoching

Bus 59:
  → Giesing Bahnhof
  → Ackermannbogen

Bus 139:
  → Messestadt West
  → Klinikum

Tram 18:
  → Gondrellplatz
  → Marienplatz

Total departures found: 15
```

#### Generate Configuration Snippet

Automatically generate a TOML configuration snippet:

```bash
mvg-config generate de:09162:100 "Chiemgaustraße"
```

**Example output:**
```toml
[[stops]]
station_id = "de:09162:100"
station_name = "Giesing"
max_departures_per_stop = 30

[stops.direction_mappings]
# Configure your direction mappings here
# Example based on available destinations:
"->Balanstr." = ["Messestadt", "Messestadt West"]
"->Klinikum" = ["Klinikum", "Klinikum Großhadern"]
"->Tegernseer" = ["Ackermannbogen", "Tegernseer"]
"->Stadt" = ["Gondrellplatz", "Marienplatz"]
```

You can redirect this to a file:
```bash
mvg-config generate de:09162:100 "Giesing" >> config.toml
```

### Method 2: Using the Helper Script

A simple Python script is also available:

```bash
python scripts/find_station.py "Station Name" München
```

**Example:**
```bash
$ python scripts/find_station.py "Giesing" München

Searching for: Giesing, München

Found station:
  ID: de:09162:100
  Name: Giesing
  Place: München
  Coordinates: 48.1234, 11.5678

Fetching sample departures...

Sample destinations:
  U2 → Messestadt
  BUS 59 → Giesing Bahnhof
  BUS 139 → Messestadt West
```

### Method 3: Using Python API Directly

You can also use the MVG API library directly in Python:

```python
from mvg import MvgApi

# Search for a station
station = MvgApi.station("Giesing, München")
if station:
    print(f"Station ID: {station['id']}")
    print(f"Name: {station['name']}")
    print(f"Place: {station['place']}")
```

**Async version:**
```python
import asyncio
from mvg import MvgApi

async def find_station():
    station = await MvgApi.station_async("Giesing, München")
    if station:
        print(f"Station ID: {station['id']}")

asyncio.run(find_station())
```

### Method 4: Using Nearby Search

If you know the coordinates, you can find the nearest station:

```python
from mvg import MvgApi

# Find nearest station to coordinates
station = MvgApi.nearby(48.1234, 11.5678)
if station:
    print(f"Nearest station: {station['name']} ({station['id']})")
```

**Async version:**
```python
import asyncio
from mvg import MvgApi

async def find_nearby():
    station = await MvgApi.nearby_async(48.1234, 11.5678)
    if station:
        print(f"Nearest station: {station['name']} ({station['id']})")

asyncio.run(find_nearby())
```

## Understanding Station IDs

Station IDs follow the format: `de:09162:XXX`

- `de`: Country code (Germany)
- `09162`: Region code (Munich area)
- `XXX`: Unique station identifier (numeric)

**Examples:**
- `de:09162:70` - Universität station
- `de:09162:100` - Giesing station
- `de:09162:123` - Another station

## Tips for Finding Stations

### 1. Use Partial Names
The search is flexible and matches partial station names:
```bash
mvg-config search "Gies"
# Will find "Giesing"
```

### 2. Include Place Name
For better results, include "München" or "Munich":
```bash
mvg-config search "Universität München"
```

### 3. Check Multiple Results
If you get multiple results, use `mvg-config info` or `mvg-config routes` to verify:
```bash
# Search might return multiple matches
mvg-config search "Giesing"

# Check each one to find the right station
mvg-config routes de:09162:XXX
```

### 4. Verify with Routes
After finding a station ID, verify it's correct by checking its routes:
```bash
mvg-config routes de:09162:100
```

This helps ensure you have the right station, especially if there are multiple stations with similar names.

## Common Issues

### Station Not Found

If a station is not found:

1. **Check spelling**: Station names are case-sensitive and may include special characters (ä, ö, ü, ß)
2. **Try different variations**: 
   - "Giesing" vs "Giesing Bahnhof"
   - "Universität" vs "Universitaet"
3. **Use partial search**: Try just part of the name
4. **Check place name**: Make sure you're searching in "München"

### Multiple Stations with Same Name

Some station names appear multiple times (different locations):

```bash
# Search returns multiple results
mvg-config search "Giesing"

# Check routes for each to identify the right one
mvg-config routes de:09162:XXX
mvg-config routes de:09162:YYY
```

### No Routes Found

If `mvg-config routes` shows no routes:

1. **Check if station is active**: The station might be temporarily closed
2. **Try different time**: Some stations have limited service hours
3. **Verify station ID**: Double-check the ID is correct

## Next Steps

Once you have the station ID:

1. **Get route information**: Use `mvg-config routes` to see all available destinations
2. **Generate config**: Use `mvg-config generate` to create a starter configuration
3. **Customize directions**: Edit the generated config to group destinations by your preferred directions
4. **Add to configuration**: Add the stop configuration to your `config.toml` or `STOPS_CONFIG` environment variable

## Example Workflow

Here's a complete example workflow:

```bash
# 1. Search for the station
$ mvg-config search "Giesing"
Found 1 station(s):
  Giesing (München)
    ID: de:09162:100

# 2. Check available routes
$ mvg-config routes de:09162:100
# ... shows all routes and destinations ...

# 3. Generate configuration
$ mvg-config generate de:09162:100 "Giesing" > my_stop.toml

# 4. Edit the configuration to customize direction names
$ nano my_stop.toml
# Change "->Direction1" to "->Balanstr.", etc.

# 5. Add to your main config.toml or set STOPS_CONFIG
```

## Additional Resources

- **MVG Website**: https://www.mvg.de - Official MVG website with station maps
- **MVG API Library**: https://github.com/mondbaron/mvg - Python library documentation
- **Project README**: See main README.md for configuration examples

