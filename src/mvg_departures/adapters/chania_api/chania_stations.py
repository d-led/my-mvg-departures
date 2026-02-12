"""Known KTEL Chania (Crete) stations: ID and name.

Station list matches the departure-station dropdown on:
https://www.e-ktel.com/en/services/live-departures
(parsed from the page select options; use for config and CLI list.)
"""

# (station_id, station_name) in display order from the website dropdown
CHANIA_STATIONS: list[tuple[str, str]] = [
    ("11", "CHANIA"),
    ("20", "CHANIA AIRPORT"),
    ("12", "RETHIMNO"),
    ("13", "KASTELI"),
    ("30", "ELAFONISI"),
    ("31", "CHORA SFAKION"),
    ("32", "SOUGIA"),
    ("33", "FALASARNA"),
    ("35", "ALMIRIDA"),
    ("60", "PERIVOLIA RETHIMNOY"),
    ("61", "THESSALONIKI"),
    ("19", "OMALOS"),
    ("71", "CROSS KALIVES"),
    ("70", "CROSS MEGALA XORAFIA"),
    ("72", "AGIOI PANTES"),
    ("73", "VRISSES APOKORONOU"),
    ("74", "GEORGIOUPOLI"),
    ("75", "KAVROS"),
    ("76", "CROSS EPISKOPIS"),
    ("80", "STAVROMENOS"),
    ("84", "PANORMO"),
    ("85", "SKEPASTI"),
    ("88", "BALI"),
    ("89", "SISES"),
    ("69", "SOUDA"),
    ("83", "CRETA PANORAMA"),
    ("77", "PETRES"),
    ("100", "STALOS"),
    ("101", "AGIA MARINA"),
    ("102", "PLATANIAS"),
    ("103", "GERANI"),
    ("104", "PIRGOS PSILONEROU"),
    ("105", "MALEME"),
    ("106", "MALEME AIRPORT"),
    ("187", "TAVRONITIS"),
    ("188", "KAMISIANA"),
    ("189", "RAPANIANA"),
    ("190", "SKOUTELONAS"),
    ("25", "KOLYMPARI"),
    ("14", "PALAIOCHORA"),
    ("16", "PLAKIAS"),
    ("18", "HERAKLION"),
    ("81", "SKALETA"),
    ("201", "MINOTHIANA"),
]


def list_chania_stations() -> list[tuple[str, str]]:
    """Return all known KTEL Chania stations as (station_id, station_name)."""
    return list(CHANIA_STATIONS)
