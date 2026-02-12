# Greece Buses & Transport APIs – Research Note

This document summarizes what exists for **buses and public transport across Greece and Greek islands**, so we can keep the Chania connector as-is and decide whether a generic “Greece” connector is feasible.

## What we use today: KTEL Chania (Crete)

- **Connector**: `api_provider = "chania"` (server only; see [ktel-chania.md](samples/ktel-chania.md)).
- **Source**: KTEL Chania–Rethymno website (e-ktel.com) – undocumented JSON endpoint for scheduled departures by station and date.
- **Scope**: Chania region (Crete) only. We keep this connector unchanged.

## Is there a single “Greece bus API”?

**No.** There is no nationwide, public REST/API that returns live or scheduled bus departures for all of Greece.

- **KTEL** is a network of many **independent regional companies** (50+). There is no central KTEL API; each region has its own site (and sometimes its own backend).
- Some regions may expose JSON or HTML that could be scraped or called (like Chania); others do not. There is no standard or list of “KTEL API endpoints.”

So a true “generic Greece bus API” does **not** exist. We keep Chania and can add more **regional** connectors (e.g. “chania”, “patras”, “lesvos”) if we find similar endpoints elsewhere.

## What does exist?

### 1. Greece National Access Point (NAP) – data.nap.gov.gr

- **Role**: Government open-data portal (CKAN).
- **Content**: Static datasets (XLSX, CSV, XML, etc.), including:
  - [Information about transport by long-distance buses in Greece](https://data.nap.gov.gr/dataset/information-about-transport-by-long-distance-buses-in-greece) – routes and timetables from KTEL companies.
  - Maritime, rail, air, traffic, etc.
- **Access**: Download files or use the [CKAN API](https://data.nap.gov.gr/api/3) for **registry/dataset metadata**, not for live departures.
- **Use for us**: Good for reference or static schedule data only. **Not** a drop-in replacement for Chania (no per-stop, per-day departure API).

### 2. GTFS and community projects

- **gtfs-greece (GitHub)**: Converts various KTEL/regional sites into **GTFS** (static schedules). Covers many regions (e.g. Kastoria, Patras, Xanthi, Achaia, Fokida, Kerkyra, Lakonia, Lesvos, Messinia, Zakynthos, etc.). Output is **static GTFS**, not a live-departure API.
- **Official GTFS in Greece**: Only a few feeds are registered (e.g. Athens urban, TRAINOSE). No single KTEL-wide GTFS API.
- **Use for us**: If we ever add GTFS-based schedule display (no real-time), we could consume such feeds. Does **not** replace the Chania connector, which uses e-ktel.com’s JSON.

### 3. Ferries (Greek islands)

- **FerriesinGreece** and similar services offer **ferry** timetables/booking; some have APIs (e.g. apisnodejs.ferriesingreece.com). These are **ferries**, not buses.
- **Use for us**: Separate domain (maritime). Out of scope for a “Greece bus” connector.

### 4. Transit apps (Moovit, etc.)

- Apps aggregate KTEL and other operators; they do **not** expose a public API we can use for a generic Greece connector.

## Recommendation

- **Keep** the Chania connector as-is (`api_provider = "chania"`).
- **Do not** replace it with a “generic Greece” API, because no such API exists.
- **Optional later**: Add more **regional** connectors (e.g. one per KTEL region that exposes a similar JSON or scrapeable endpoint), each with its own `api_provider` (e.g. `chania`, `patras`, …). That would grow “Greece” coverage without a single generic API.
- **Optional later**: If we add **static schedule** support (e.g. GTFS-based), we could use NAP long-distance bus datasets or gtfs-greece outputs for reference; that would complement, not replace, live/scheduled connectors like Chania.

## References (quick links)

- [Greece NAP – long-distance buses dataset](https://data.nap.gov.gr/dataset/information-about-transport-by-long-distance-buses-in-greece)
- [Greece NAP – datasets list](https://data.nap.gov.gr/dataset)
- [gtfs-greece (GitHub)](https://github.com/angelou/gtfs-greece)
- [KTEL Chania sample config](samples/ktel-chania.md)
