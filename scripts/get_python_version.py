#!/usr/bin/env python3
"""Get Python version as major.minor string."""

import sys

if __name__ == "__main__":
    print(f"{sys.version_info.major}.{sys.version_info.minor}")

