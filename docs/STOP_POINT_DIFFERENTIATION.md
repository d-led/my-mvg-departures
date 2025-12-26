# Stop Point Differentiation

## Problem

At stations like "Chiemgaustraße (München)", multiple physical stops exist with the same name but different locations (e.g., buses making a loop in Giesing). For example, Bus 139 to "Klinikum Harlaching" may stop at different physical locations at the same named station.

## Solution: `stopPointGlobalId`

The MVG API provides a `stopPointGlobalId` field in the departure response that uniquely identifies each physical stop point, even when they share the same `stationGlobalId`.

### API Response Structure

The raw MVG API response includes:

- **`stationGlobalId`**: The station identifier (e.g., `"de:09162:1108"` for Chiemgaustraße)
- **`stopPointGlobalId`**: The physical stop point identifier (e.g., `"de:09162:1108:4:4"`)

### Example from Chiemgaustraße

For station `de:09162:1108` (Chiemgaustraße), the following `stopPointGlobalId` values are observed:

- `de:09162:1108:1:1` - Tram 18 (Schwanseestraße direction)
- `de:09162:1108:2:2` - Tram 18 (Gondrellplatz/Ostfriedhof direction)
- `de:09162:1108:3:3` - Bus 59 (Ackermannbogen/Einsteinstraße direction)
- `de:09162:1108:4:4` - Bus 139 to Klinikum Harlaching (some departures)
- `de:09162:1108:5:5` - Bus 139 to Klinikum Harlaching (other departures), Bus 59 to Giesing Bahnhof, Bus 139 to Neuperlach Zentrum
- `de:09162:1108:6:6` - Regional Bus 220

**Key Finding**: Bus 139 to "Klinikum Harlaching" uses **both** `4:4` and `5:5`, indicating it stops at two different physical locations at the same named station.

### Format

The `stopPointGlobalId` format appears to be:
```
{stationGlobalId}:{stopNumber}:{stopNumber}
```

Where `{stopNumber}` is repeated (e.g., `de:09162:1108:4:4`).

## Current Implementation Status

The codebase **now extracts and uses** `stopPointGlobalId`:

- ✅ `stop_point_global_id` field added to `Departure` domain model
- ✅ `MvgDepartureRepository` extracts `stopPointGlobalId` from API response
- ✅ `StopConfiguration` supports `stop_point_global_id` filter option
- ✅ `DepartureGroupingService` filters departures by stop point when configured
- ✅ CLI tool (`mvg-config routes`) displays stop point differentiation hints

## Potential Use Cases

1. **Filtering by Physical Stop**: Allow users to configure which physical stop point(s) to display
2. **Display Differentiation**: Show stop point numbers in the UI (e.g., "Bus 139 → Klinikum Harlaching (Stop 4)")
3. **Route Configuration**: Configure direction mappings per physical stop point
4. **Accurate Departure Display**: Ensure users see departures from the correct physical location

## Usage

### Configuration

When a station has multiple physical stops, use the `stop_point_global_id` directly as the `station_id` in separate `[[stops]]` entries:

```toml
# First physical stop (e.g., stop 5:5)
[[stops]]
station_id = "de:09162:1108:5:5"
station_name = "Chiemgaustraße (Stop 5)"

[stops.direction_mappings]
"->Klinikum" = ["139 Klinikum Harlaching"]
"->Neuperlach" = ["139 Neuperlach Zentrum"]

# Second physical stop (e.g., stop 4:4)
[[stops]]
station_id = "de:09162:1108:4:4"
station_name = "Chiemgaustraße (Stop 4)"

[stops.direction_mappings]
"->Klinikum" = ["139 Klinikum Harlaching"]
```

### Finding Stop Points

Use the CLI tool to discover available stop points:

```bash
mvg-config routes "Chiemgaustraße"
```

The output includes a "Stop Point Differentiation Hints" section showing:
- Which routes/destinations use each physical stop
- The exact `station_id` value to copy/paste into your config (using the stop_point_global_id format)

### Example Use Case

At Chiemgaustraße, Bus 139 to "Klinikum Harlaching" uses both stop `4:4` and `5:5`. To monitor both physical stops separately:

```toml
# Monitor stop 5:5 (used by most routes)
[[stops]]
station_id = "de:09162:1108:5:5"
station_name = "Chiemgaustraße (Stop 5)"

[stops.direction_mappings]
"->Klinikum" = ["139 Klinikum Harlaching"]
"->Neuperlach" = ["139 Neuperlach Zentrum"]

# Monitor stop 4:4 (alternative stop for Klinikum)
[[stops]]
station_id = "de:09162:1108:4:4"
station_name = "Chiemgaustraße (Stop 4)"

[stops.direction_mappings]
"->Klinikum" = ["139 Klinikum Harlaching"]
```

**Note**: If you use the base `station_id` (e.g., `"de:09162:1108"`), the stop will show departures from all physical stops at that station (default behavior). Use the `stop_point_global_id` format (e.g., `"de:09162:1108:5:5"`) to filter to a specific physical stop.

## API Endpoints

### Routes Endpoint

The MVG API provides a dedicated routes endpoint that returns all routes and destinations for a station:

```
GET https://www.mvg.de/api/bgw-pt/v3/lines/{stationGlobalId}
```

**Benefits over departures sampling:**
- More reliable: Returns all routes, not just those with upcoming departures
- Complete: Shows all destinations, not just those in the current sample
- Faster: Single API call instead of sampling many departures

**Implementation:** The `mvg-config routes` command now uses this endpoint first, falling back to departures sampling if the endpoint is unavailable.

### Departures Endpoint

The MVG API endpoint for departures:
```
GET https://www.mvg.de/api/bgw-pt/v3/departures?globalId={stationGlobalId}&limit=100&transportTypes=...
```

The response includes `stopPointGlobalId` in each departure object.

### Stop PDFs Endpoint

MVG also provides an endpoint that returns information about stop PDFs (departure boards) for different physical stops:

```
GET https://www.mvg.de/.rest/aushang/stations?id={stationCode}
```

Where `{stationCode}` is a short station identifier (e.g., `"CHI"` for Chiemgaustraße).

This endpoint likely returns:
- Different PDF URLs or identifiers for each physical stop point
- Mapping between physical stops and their departure board information
- Additional metadata about the physical stop locations

**Note**: This endpoint uses a different identifier format (short code like "CHI") compared to the `stationGlobalId` format (`de:09162:1108`). The relationship between these identifiers and the `stopPointGlobalId` values needs to be investigated.

### Potential Use Case

The stop PDFs endpoint could be used to:
1. Discover all physical stop points at a station
2. Get human-readable information about each physical stop
3. Map `stopPointGlobalId` values to actual stop locations/names
4. Display stop-specific information in the UI

