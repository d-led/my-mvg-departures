# Development Guide

This document covers development-related topics for the MVG Departures project.

## Running Tests

```bash
# Using pytest directly
pytest

# With coverage
pytest --cov=mvg_departures --cov-report=html

# Using uv
uv run pytest

# Using the test script (recommended)
./scripts/test.sh
```

The test script runs all tests, linting, and type checking. Keep it green.

## Code Quality

```bash
# Format code
black src tests

# Lint code
ruff check src tests

# Type checking
mypy src
```

## Extending the Application

### Adding a New Output Device

To add support for a new output device (e.g., e-ink display, LED matrix):

1. Create a new adapter in `src/mvg_departures/adapters/` implementing `DisplayAdapter`
2. Use the `DepartureGroupingService` to get grouped departures
3. Update `main.py` to instantiate your adapter instead of `PyViewWebAdapter`

Example structure:

```python
from mvg_departures.domain.ports import DisplayAdapter

class MyDeviceAdapter(DisplayAdapter):
    async def display_departures(self, direction_groups):
        # Render to your device
        pass

    async def start(self):
        # Initialize device
        pass

    async def stop(self):
        # Cleanup
        pass
```

## Poller Architecture

The application uses a two-tier polling system:

1. **Shared Departure Fetcher**: Single background task that fetches raw departures for all unique stations across all routes. Populates `SharedDepartureCache`. Runs on global `refresh_interval_seconds`.
   - See: `src/mvg_departures/adapters/web/pyview_app.py::_start_departure_fetcher()`
   - Implementation: `src/mvg_departures/adapters/web/fetchers/departure_fetcher.py`

2. **Route-Specific ApiPollers**: Each route has its own `ApiPoller` instance in a separate async task. Reads from shared cache, processes per route's `StopConfiguration`, updates route state, broadcasts to WebSocket clients. Can have route-specific `refresh_interval_seconds`.
   - See: `src/mvg_departures/adapters/web/pollers/api_poller.py`
   - Started per route: `src/mvg_departures/adapters/web/pyview_app.py::start()` (lines ~2270-2281)
   - Route config: `src/mvg_departures/domain/models/route_configuration.py` (field: `refresh_interval_seconds`)

All tasks run concurrently in the same asyncio event loop.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and development practices.
