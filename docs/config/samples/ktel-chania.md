# KTEL Chania (Greece) Sample Config

For an overview of Greece bus/transport APIs and why we use a regional Chania connector (no generic Greece API), see [greece-transport-apis.md](../greece-transport-apis.md).

```toml
# KTEL Chania (Greece) sample config for my-mvg-departures

title = "Chania ↔ Paleochora Departures"
theme = "auto"
refresh_interval_seconds = 30
random_header_colors = true

# Show "Find your stop on map (GPS)" link in the Check schedule overlay (off by default in other configs)
[display]
find_closest_stop_url = "https://www.e-ktel.com/en/services/find-closest-stop"

[[stops]]
station_id = "11" # CHANIA main station (see website for IDs)
station_name = "Chania"
api_provider = "chania"
max_departures_per_stop = 10
max_departures_per_route = 3

[[stops]]
station_id = "14" # PALAIOCHORA (use chania-config stations to list all)
station_name = "Paleochora"
api_provider = "chania"
max_departures_per_stop = 5
max_departures_per_route = 2

[[routes]]
path = "/chania-paleochora"
title = "Chania ↔ Paleochora"

[[routes.stops]]
station_id = "11"
station_name = "Chania"
max_departures_per_stop = 10
max_departures_per_route = 3

[[routes.stops]]
station_id = "14"
station_name = "Paleochora"
max_departures_per_stop = 5
max_departures_per_route = 2
```

- **List all stations with IDs:** `chania-config stations` (or `--json`). Same list as the [Live Departures](https://www.e-ktel.com/en/services/live-departures) station dropdown. From the repo you can run `./scripts/chania-config.sh` (no args for help) or `./scripts/chania-config.sh stations`.
- `station_id` values correspond to that dropdown (e.g. `11` = Chania, `14` = Paleochora).
- **Example: fetch tomorrow's departures in Chania** (station ID `11`):

  ```bash
  # From project root (with venv activated)
  chania-config departures 11 --date 2026-02-13 --limit 20
  ```

  Or with Python (e.g. in a script or notebook):

  ```python
  import asyncio
  from mvg_departures.adapters.chania_api import ChaniaDepartureRepository

  async def main():
      repo = ChaniaDepartureRepository()
      departures = await repo.get_departures(
          station_id="11",
          limit=20,
          departure_date="2026-02-13",
      )
      for d in departures:
          print(f"{d.planned_time.strftime('%H:%M')}  {d.line} → {d.destination}")

  asyncio.run(main())
  ```

  The same data is shown on the [Live Departures](https://www.e-ktel.com/en/services/live-departures) page when you select station "CHANIA" and date 2026-02-13.

- **Finding station IDs**: Run `chania-config stations` to list all IDs and names. Or use the [Live Departures](https://www.e-ktel.com/en/services/live-departures) dropdown or [Find closest stop](https://www.e-ktel.com/en/services/find-closest-stop) (map/GPS).
- **Find closest stop:** Set `[display] find_closest_stop_url` (e.g. to the e-ktel URL above) to show the "Find your stop on map (GPS)" link in the one-time schedule overlay. Leave unset in non-Chania configs so the link is hidden by default.
- `api_provider = "chania"` enables the new connector.
- The `routes` section defines a dashboard tab with the listed stops.
- You can add more stops or routes by copying the blocks and changing the IDs/names.

## API response field mapping

The Chania connector uses the same JSON endpoint as the [Departures](https://www.e-ktel.com/en/services/live-departures) page. The response `data` array contains one row per departure; each row is an array in the same order as the table columns:

| Index | Website column | Description                                                                           |
| ----- | -------------- | ------------------------------------------------------------------------------------- |
| 0     | **Route ID**   | Trip/route identifier (stored as departure id in the app).                            |
| 1     | **To**         | Destination name in Greek (e.g. ΠΑΛΑΙΟΧΩΡΑ).                                          |
| 2     | **To**         | Destination name in English (e.g. Paleochora); used for line and destination display. |
| 3     | **Bus number** | Route code (e.g. A1, 54).                                                             |
| 4     | **Date**       | Departure date (`YYYY-MM-DD`).                                                        |
| 5     | **Time**       | Departure time (`HH:MM`).                                                             |
| 6     | _(no header)_  | Platform or gate number.                                                              |
