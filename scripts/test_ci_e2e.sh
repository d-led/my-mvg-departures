#!/bin/bash
# Test E2E workflow locally using act
#
# Note: act doesn't fully support service containers, so we start the app service
# manually and run Cypress tests directly against localhost:8000
#
# Usage:
#   ./scripts/test_ci_e2e.sh

set -e

IMAGE_NAME="my-mvg-departures:test"
CONTAINER_NAME="mvg-departures-test"
PORT=8000

# Cleanup function
cleanup() {
  echo "Cleaning up..."
  docker stop "$CONTAINER_NAME" 2>/dev/null || true
  docker rm "$CONTAINER_NAME" 2>/dev/null || true
}
trap cleanup EXIT

echo "Building Docker image: $IMAGE_NAME"
docker build -f docker/Dockerfile.optimized --platform linux/arm64 -t "$IMAGE_NAME" .

echo "Verifying image exists..."
docker images "$IMAGE_NAME" | grep -q "$IMAGE_NAME" || { echo "Error: Image $IMAGE_NAME not found after build"; exit 1; }

echo "Starting app service container..."
docker stop "$CONTAINER_NAME" 2>/dev/null || true
docker rm "$CONTAINER_NAME" 2>/dev/null || true
docker run -d \
  --name "$CONTAINER_NAME" \
  -p "$PORT:8000" \
  -e HOST=0.0.0.0 \
  -e PORT=8000 \
  -e CONFIG_FILE=/app/config.example.toml \
  "$IMAGE_NAME"

echo "Waiting for service to be ready..."
for i in {1..60}; do
  if curl -f "http://localhost:$PORT/healthz" > /dev/null 2>&1; then
    echo "Service is ready!"
    break
  fi
  if [ $i -eq 60 ]; then
    echo "Error: Service did not become ready in time"
    docker logs "$CONTAINER_NAME"
    exit 1
  fi
  echo "Waiting for service... ($i/60)"
  sleep 1
done

echo "Running E2E tests..."
npm run e2e -- --config baseUrl="http://localhost:$PORT"

