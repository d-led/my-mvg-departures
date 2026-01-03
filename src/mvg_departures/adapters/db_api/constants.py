"""Constants for DB API adapter.

Uses the v6.db.transport.rest public API.
API Documentation: https://v6.db.transport.rest/api.html

Rate limit: 100 requests/minute (burst 200 requests/minute)
No authentication required.
"""

# API endpoints - using v6.db.transport.rest (public API)
# See: https://v6.db.transport.rest/api.html
DB_BASE_URL = "https://v6.db.transport.rest"
DB_LOCATIONS_URL = f"{DB_BASE_URL}/locations"  # GET /locations?query=...
DB_STOPS_URL = f"{DB_BASE_URL}/stops"  # GET /stops/:id, GET /stops/:id/departures

# HTTP headers
DEFAULT_HEADERS = {
    "Accept": "application/json",
}

# Icon mapping: transport type -> icon name
ICON_MAP = {
    "ICE": "mdi:train",
    "IC/EC": "mdi:train",
    "RE": "mdi:train",
    "RB": "mdi:train",
    "S-Bahn": "mdi:subway-variant",
    "Bus": "mdi:bus",
    "Tram": "mdi:tram",
    "U-Bahn": "mdi:subway",
    "Train": "mdi:train",
}

# Station encoding constants
STATION_ENCODING_VERSION = "A=1"
STATION_ENCODING_COUNTRY = "U=81"
