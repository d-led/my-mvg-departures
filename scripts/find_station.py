#!/usr/bin/env python3
"""Helper script to find MVG station IDs."""

import asyncio
import sys

from mvg import MvgApi


def _print_station_info(result: dict) -> None:
    """Print station information."""
    print(f"\nFound station:")
    print(f"  ID: {result['id']}")
    print(f"  Name: {result['name']}")
    print(f"  Place: {result['place']}")
    print(f"  Coordinates: {result['latitude']}, {result['longitude']}")


def _print_sample_destinations(departures: list) -> None:
    """Print sample destinations from departures."""
    print(f"\nSample destinations:")
    seen = set()
    for dep in departures:
        key = (dep['line'], dep['destination'])
        if key not in seen:
            print(f"  {dep['line']} → {dep['destination']}")
            seen.add(key)


async def find_station(name: str, place: str = "München") -> None:
    """Find a station by name."""
    query = f"{name}, {place}"
    print(f"Searching for: {query}")
    
    result = await MvgApi.station_async(query)
    if not result:
        print(f"Station not found: {query}")
        sys.exit(1)
    
    _print_station_info(result)
    
    print(f"\nFetching sample departures...")
    departures = await MvgApi.departures_async(result['id'], limit=10)
    if departures:
        _print_sample_destinations(departures)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_station.py <station_name> [place]")
        print('Example: python find_station.py "Chiemgaustraße" München')
        sys.exit(1)
    
    station_name = sys.argv[1]
    place = sys.argv[2] if len(sys.argv) > 2 else "München"
    
    asyncio.run(find_station(station_name, place))


