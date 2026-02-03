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

> **💡 Tip**: Use this SPA version to generate and test your TOML configuration, then copy it to the server-side or Inky versions for deployment!

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
