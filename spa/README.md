# MVG Departures SPA

Client-side Single Page Application for displaying MVG departures. Runs entirely in the browser without requiring a server apart from hosting the static assets.

**Try it online**: **[https://d-led.github.io/my-mvg-departures/](https://d-led.github.io/my-mvg-departures/)**

## Features

- **Client-side only**: No server required - runs entirely in the browser
- **Configuration wizard**: Interactive UI to generate TOML config (click the config icon ⚙️)
- **MVG API integration**: Fetches departures directly from MVG API
- **LocalStorage caching**: Caches departures for offline viewing
- **Route switching**: Switch between different route configurations via URL paths
- **Same view as server version**: Maintains the exact same UI/UX as the server-side version
- **Pinch zoom support**: Zoom in/out without breaking the layout

## Configuration

The SPA includes an interactive configuration UI, opened by clicking the config icon (⚙️) in the status bar at the bottom of the page.

The dialog has two views:

- **Pages** - a card for the settings every page inherits (`[display]`: refresh
  interval, theme, fonts and the rest) and one card per screen: its title, its path
  and its stops. Drag a card (or use the arrows) to change the order the pages
  appear in, **Edit** opens the page's form - title, path, this page's own display
  settings, and per stop its direction headings (the name and the one-per-line
  matches) plus the heading for departures that match none and whether they are
  shown at all - and the page or a single stop can be deleted, each asking first.
  **New page** adds an empty one and **Add stops…** brings up the wizard for it.
  Everything is an edit of the file: nothing
  is stored until **Save**, and **Cancel** leaves the stored config untouched,
  while applying an unchanged form changes nothing at all.
- **TOML** - the raw configuration, for pasting an existing config or fixing
  something by hand. The toolbar copies, pastes, tweaks single values, opens a
  full-screen editor on a phone, and offers **Clean up** for configs written for
  the server version.

**Where stops come from:** the wizard searches stops by name, lets you pick the
direction headings you want, and writes them into the chosen page.

Configuration is stored in browser localStorage and persists across sessions.

### The SPA's TOML shape

Everything is per user, so the file holds only what a browser renders:

```toml
# Settings every route inherits; a route's own [routes.display] wins
[display]
title = "Giesing Departures"
refresh_interval_seconds = 20

# One screen per route; `path` is the URL fragment (/#/work)
[[routes]]
path = "/"

# Every stop is its own config; what it leaves out comes from [display]
[[routes.stops]]
station_id = "de:09162:1110"
station_name = "Giesing"
max_departures_per_stop = 6
show_ungrouped = true

[routes.stops.direction_mappings]
"->Stadtmitte" = ["U2 Messestadt", "U2 Feldmoching"]

# The "Next to me" screen, driven by the browser's location
[[on_the_run]]
radius_meters = 100
```

There is no default stop list beside the routes, and no `[api]`, `[inky]` or `[server]`
table: those belong to the server versions and are ignored here. See
[`config.example.toml`](config.example.toml) for a complete example.

### Older configs

A config written for the server keeps loading:

- top-level `[[stops]]` are read as the route at `/`,
- `[api]`, `[inky]`, `[server]` and other server-only tables are ignored,
- `departures_per_page`, `page_rotation_seconds`, `pagination_enabled` and
  `banner_color` are not rendered by the SPA.

To get rid of them, open the config dialog and press **Clean up**: it prepares the
rewrite, keeps your comments, and says what it would remove. Nothing changes until
you press **Apply clean-up** — **Cancel clean-up** leaves the text as it was, and
nothing is saved either way until you press **Save**.

The "Next to me" page is one optional `[[on_the_run]]` table, so it is easy to lose
by accident. The dialog says whether the page is part of the config and offers
**Restore**, with working defaults; it never removes the page.

### Examples: two Munich, two Berlin

| Example                                                                                | Provider    | What it shows                 |
| -------------------------------------------------------------------------------------- | ----------- | ----------------------------- |
| [`config.example.toml`](config.example.toml)                                           | MVG München | the default: Giesing          |
| [`configs/muenchen-muenchner-freiheit.toml`](configs/muenchen-muenchner-freiheit.toml) | MVG München | U3/U6, buses and tram grouped |
| [`configs/berlin-alexanderplatz.toml`](configs/berlin-alexanderplatz.toml)             | VBB Berlin  | S+U Alexanderplatz, all lines |
| [`configs/berlin-zoologischer-garten.toml`](configs/berlin-zoologischer-garten.toml)   | VBB Berlin  | one platform, 249 grouped     |

Berlin stops read the VBB API, so they say `api_provider = "vbb"`; Munich stops use
the default MVG API and need no line. The dialog's **Example** button loads the
default one, and each example is preconfigured on GitHub Pages:

- **Giesing**:
  <https://d-led.github.io/my-mvg-departures/?config=https://d-led.github.io/my-mvg-departures/config.example.toml>
- **Münchner Freiheit**:
  <https://d-led.github.io/my-mvg-departures/?config=https://d-led.github.io/my-mvg-departures/configs/muenchen-muenchner-freiheit.toml>
- **Berlin Alexanderplatz**:
  <https://d-led.github.io/my-mvg-departures/?config=https://d-led.github.io/my-mvg-departures/configs/berlin-alexanderplatz.toml>
- **Berlin Zoologischer Garten**:
  <https://d-led.github.io/my-mvg-departures/?config=https://d-led.github.io/my-mvg-departures/configs/berlin-zoologischer-garten.toml>

### Why there is no Wuppertal example (yet)

Wuppertal would read the DB API (`v6.db.transport.rest`, `api_provider = "db"`), but
that instance answers `503` on `/locations` and `/departures` today, and its own docs
say it must not be used for automated requests ("the underlying APIs seem to have a
much lower rate limit than before"). The SPA therefore reports DB as an unsupported
provider rather than showing an empty screen. When a source for NRW answers, the
sample is a stop with `api_provider = "db"` plus groupings: buses and regional
trains by their destination in the city, local trains by their next stop.

### Sharing a config by link

`?config=<url>` loads a config from any absolute http(s) link, stores it and shows
it immediately:

```
https://d-led.github.io/my-mvg-departures/?config=https://raw.githubusercontent.com/d-led/my-mvg-departures/main/spa/configs/berlin-alexanderplatz.toml
```

Raw links are the useful ones - `raw.githubusercontent.com` serves plain text and
allows cross-origin reads. GitHub's file pages
(`github.com/<owner>/<repo>/blob/<ref>/<path>`) and gist pages also work: they are
translated to their raw URLs. Pasting a link into the config dialog does the same.

> **💡 Tip**: Use this SPA version to generate and test your TOML configuration, then copy the route and stop tables to the server-side or Inky versions for deployment!

For configuration details and patterns, see the main [README.md](../README.md#configuration).

## Development Setup

```bash
./scripts/setup.sh
```

This will install all Node.js dependencies.

## Development

```bash
./scripts/dev.sh
```

Starts a development server with hot reload at `http://localhost:8000`.

## Building

```bash
./scripts/build.sh
```

Builds the production bundle to `dist/` directory.

## Testing

```bash
./scripts/test.sh
```

Runs:

- Svelte check (a11y + diagnostics)
- TypeScript type checking
- ESLint
- Prettier formatting check
- Unit tests

### End-to-end

The SPA is covered by Cypress specs that stub the MVG API, so they run without network access:

```bash
cd spa && npm run dev      # serve the SPA on http://localhost:8000
npm run e2e:spa            # from the project root, runs cypress/e2e/spa/**
```

## Partial failures

Every refresh cycle retries a stop that fails, up to three attempts with a short pause between
them, so a hiccup does not blank a stop until the next interval. The budget is part of the route's
configuration:

```toml
[display]
fetch_retry_attempts = 3   # total tries per stop and cycle (1 = no retry)
fetch_retry_delay_ms = 500 # pause between those tries
```

Only when a cycle leaves nothing to show at all does the app announce the failing stops on top of
the departures area. While departures are on screen the failure stays out of the way: the affected
stop reads "No data (refresh failed)" and the status indicator turns degraded, with the stop names
and reasons in its tooltip.

## Architecture

Follows the same ports and adapters pattern as the Python version:

- **Domain Models**: `src/domain/models/` - Core data structures
- **Ports**: `src/domain/ports/` - Interfaces (DepartureRepository, DepartureCache, ConfigStorage)
- **Adapters**: `src/adapters/` - Implementations (MvgDepartureRepository, LocalStorageCache, etc.)
- **Services**: `src/application/services/` - Business logic (DepartureGroupingService, ApiPoller)

## Deployment

The `dist/` directory can be deployed to any static hosting service (GitHub Pages, Netlify, Vercel, etc.).

**GitHub Pages Example:**

This repository deploys the SPA to GitHub Pages automatically. The live version is available at:
**[https://d-led.github.io/my-mvg-departures/](https://d-led.github.io/my-mvg-departures/)**

To deploy your own:

1. Build the SPA: `cd spa && npm run build`
2. Configure GitHub Pages to serve from `spa/dist` directory
3. The SPA will be available at `https://YOUR_USERNAME.github.io/YOUR_REPO/`

For other static hosting services, simply upload the contents of `spa/dist/` to your hosting provider.
