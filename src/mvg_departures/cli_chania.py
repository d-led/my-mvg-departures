"""CLI for KTEL Chania (Crete) one-time schedule fetch and config help.

Use this for a one-time fetch of departures from the Chania API (e.g. to verify
station_id or print a schedule). For finding stops by location (GPS/address), use
the website: https://www.e-ktel.com/en/services/find-closest-stop
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import TYPE_CHECKING

from mvg_departures.adapters.chania_api import ChaniaDepartureRepository, list_chania_stations

if TYPE_CHECKING:
    from mvg_departures.domain.models.departure import Departure


def _departure_to_dict(dep: Departure) -> dict:
    """Convert domain Departure to a JSON-friendly dict for CLI output."""
    return {
        "line": dep.line,
        "destination": dep.destination,
        "planned_time": dep.planned_time.isoformat(),
        "time": dep.time.isoformat(),
        "platform": dep.platform,
        "transport_type": dep.transport_type,
        "is_cancelled": dep.is_cancelled,
        "stop_point_global_id": dep.stop_point_global_id,
    }


def _format_departure(dep: Departure, index: int) -> str:
    """Format a single departure for human-readable output."""
    time_str = dep.planned_time.strftime("%H:%M")
    platform_str = f" [Platform {dep.platform}]" if dep.platform is not None else ""
    cancelled_str = " [CANCELLED]" if dep.is_cancelled else ""
    return (
        f"  {index:3}. {time_str:6}  {dep.line:20} → {dep.destination}{platform_str}{cancelled_str}"
    )


async def fetch_departures_chania(
    station_id: str,
    date: str | None = None,
    limit: int = 20,
) -> list[Departure]:
    """Fetch scheduled departures from KTEL Chania API for a station.

    Args:
        station_id: Station ID (e.g. "11" for Chania, "59" for Paleochora).
        date: Departure date YYYY-MM-DD; if None, uses today (server date).
        limit: Maximum number of departures to return.

    Returns:
        List of Departure domain objects.
    """
    repo = ChaniaDepartureRepository()
    return await repo.get_departures(
        station_id=station_id,
        limit=limit,
        offset_minutes=0,
        transport_types=None,
        duration_minutes=60,
        departure_date=date,
    )


async def run_departures_command(
    station_id: str,
    date: str | None = None,
    limit: int = 20,
    output_json: bool = False,
) -> None:
    """Run the departures command: fetch once and print (or JSON)."""
    if date is None:
        date = datetime.now().astimezone().strftime("%Y-%m-%d")

    departures = await fetch_departures_chania(station_id=station_id, date=date, limit=limit)

    if output_json:
        out = [_departure_to_dict(d) for d in departures]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    print(f"\nKTEL Chania - Departures from station {station_id} on {date}\n")
    if not departures:
        print("  No departures found.")
        return
    for i, dep in enumerate(departures, 1):
        print(_format_departure(dep, i))
    print(f"\n  ({len(departures)} departure(s))\n")


def run_stations_command(*, output_json: bool = False) -> None:
    """List all known KTEL Chania stations (id, name)."""
    stations = list_chania_stations()
    if output_json:
        out = [{"station_id": sid, "station_name": name} for sid, name in stations]
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return
    print("\nKTEL Chania - Stations (use station_id in config)\n")
    for sid, name in stations:
        print(f"  {sid:>4}  {name}")
    print(f"\n  ({len(stations)} station(s))\n")


def cli_main() -> None:
    """CLI entry point for chania-config (setuptools script)."""
    import argparse

    logging.basicConfig(
        level=logging.WARNING,
        format="%(message)s",
        stream=sys.stderr,
    )
    # Reduce noise from aiohttp and our adapters
    logging.getLogger("mvg_departures").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        description="KTEL Chania (Crete) - one-time schedule fetch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all stations with IDs (for config)
  chania-config stations

  # Today's departures from Chania main station (ID 11)
  chania-config departures 11

  # Specific date, limit 10
  chania-config departures 11 --date 2025-06-15 --limit 10

  # Paleochora (ID 14), JSON output
  chania-config departures 14 --json

Finding station IDs:
  chania-config stations   # list all known stations
  Or: https://www.e-ktel.com/en/services/live-departures (dropdown)
  Or: https://www.e-ktel.com/en/services/find-closest-stop (map/GPS)
        """,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command")

    dep_parser = subparsers.add_parser(
        "departures", help="Fetch scheduled departures for a station (one-time)"
    )
    dep_parser.add_argument(
        "station_id",
        help="Station ID (e.g. 11=Chania, 14=Paleochora). Run 'chania-config stations' to list all.",
    )
    dep_parser.add_argument(
        "--date",
        default=None,
        metavar="YYYY-MM-DD",
        help="Departure date (default: today)",
    )
    dep_parser.add_argument(
        "--limit", type=int, default=20, help="Max departures to show (default: 20)"
    )
    dep_parser.add_argument("--json", action="store_true", help="Output as JSON")

    subparsers.add_parser(
        "stations",
        help="List KTEL Chania stations with IDs (for config station_id)",
    ).add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    if args.command == "stations":
        run_stations_command(output_json=getattr(args, "json", False))
    elif args.command == "departures":
        asyncio.run(
            run_departures_command(
                station_id=args.station_id,
                date=args.date,
                limit=args.limit,
                output_json=args.json,
            )
        )
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
