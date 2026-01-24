# MVG Departures SPA

Client-side Single Page Application for displaying MVG departures.

## Features

- **Client-side only**: No server required - runs entirely in the browser
- **MVG API integration**: Fetches departures directly from MVG API
- **LocalStorage caching**: Caches departures for offline viewing
- **Configuration via UI**: Paste TOML config directly in the browser
- **Route switching**: Switch between different route configurations via URL paths
- **Same view as server version**: Maintains the exact same UI/UX

## Setup

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

## Configuration

Users can paste their TOML configuration directly into the configuration modal (click the config icon in the status bar). The configuration is stored in browser localStorage.

## Deployment

The `dist/` directory can be deployed to any static hosting service (GitHub Pages, Netlify, Vercel, etc.).

For GitHub Pages, configure the build output directory as `spa/dist` in your repository settings.
