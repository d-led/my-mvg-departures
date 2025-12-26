#!/usr/bin/env python3
"""Check if mvg_departures package is installed."""

import sys

try:
    import mvg_departures  # noqa: F401
    sys.exit(0)
except ImportError:
    sys.exit(1)

