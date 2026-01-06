# Test E2E workflow locally using Docker
#
# Note: This script starts the app service manually and runs Cypress tests directly against localhost:8000
#
# Usage:
#   .\scripts\test_ci_e2e.ps1

$ErrorActionPreference = "Stop"

$IMAGE_NAME = "my-mvg-departures:test"
$CONTAINER_NAME = "mvg-departures-test"
$PORT = 8000

# Cleanup function
function cleanup {
    Write-Host "Cleaning up..."
    docker stop $CONTAINER_NAME 2>$null | Out-Null
    docker rm $CONTAINER_NAME 2>$null | Out-Null
}

# Register cleanup on script exit
try {
    # PowerShell cleanup handler
    $null = Register-EngineEvent PowerShell.Exiting -Action { cleanup }
} catch {
    # Fallback: manual cleanup will be called at end
}

Write-Host "Building Docker image: $IMAGE_NAME"
docker build -f docker/Dockerfile.optimized --platform linux/arm64 -t $IMAGE_NAME .

Write-Host "Verifying image exists..."
$imageExists = docker images $IMAGE_NAME | Select-String -Pattern $IMAGE_NAME
if (-not $imageExists) {
    Write-Host "Error: Image $IMAGE_NAME not found after build" -ForegroundColor Red
    exit 1
}

Write-Host "Starting app service container..."
docker stop $CONTAINER_NAME 2>$null | Out-Null
docker rm $CONTAINER_NAME 2>$null | Out-Null
docker run -d `
    --name $CONTAINER_NAME `
    -p "${PORT}:8000" `
    -e HOST=0.0.0.0 `
    -e PORT=8000 `
    -e CONFIG_FILE=/app/config.example.toml `
    $IMAGE_NAME

Write-Host "Waiting for service to be ready..."
$maxAttempts = 60
$attempt = 0
$ready = $false

while ($attempt -lt $maxAttempts) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:$PORT/healthz" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Service is ready!"
            $ready = $true
            break
        }
    } catch {
        # Service not ready yet
    }
    
    $attempt++
    Write-Host "Waiting for service... ($attempt/$maxAttempts)"
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Host "Error: Service did not become ready in time" -ForegroundColor Red
    docker logs $CONTAINER_NAME
    cleanup
    exit 1
}

Write-Host "Running E2E tests..."
try {
    npm run e2e -- --config "baseUrl=http://localhost:$PORT"
} finally {
    cleanup
}

