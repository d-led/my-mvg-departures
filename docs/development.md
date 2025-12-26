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

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines and development practices.

