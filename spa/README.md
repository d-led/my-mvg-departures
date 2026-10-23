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

The SPA includes an interactive configuration wizard accessible by clicking the config icon (⚙️) in the status bar at the bottom of the page.

**Two ways to configure:**

1. **Use the wizard**: Add stops, configure direction mappings, and customize display settings through the UI
2. **Paste TOML**: If you already have a TOML config (from the server-side version), paste it directly into the modal

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

To get rid of them, open the config dialog and press **Clean up**: it rewrites the
stored text into the shape above in one step, keeps your comments, and says what it
removed. Nothing is saved until you press **Save**.

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
