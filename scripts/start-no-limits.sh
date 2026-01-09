#!/bin/bash
# Start script for MVG Departures with rate limiting disabled (for scalability/load testing)
# Sets environment variables and calls the original start script

# Set environment variable to disable rate limiting
export MVG_DEPARTURES_DISABLE_RATE_LIMIT=1
export RATE_LIMIT_PER_MINUTE=0

# Call the original start script
exec ./scripts/start.sh
