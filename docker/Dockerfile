# Multi-stage build for secure, minimal Python Docker image
# Stage 1: Build stage - contains build tools and compilers
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv

# Copy dependency files
COPY pyproject.toml README.md ./

# Copy application code (needed for editable install)
COPY src/ ./src/

# Install dependencies and build wheels
# Use --system to install to system Python, not venv
# Use --no-cache to avoid caching pip downloads
RUN uv pip install --system --no-cache -e .

# Stage 2: Runtime stage - minimal image with only runtime dependencies
FROM python:3.12-slim AS runtime

# Install only runtime system dependencies (if any are needed)
# Most Python packages should be pre-compiled wheels, but some may need libc
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# Copy Python environment from builder
# Copy the entire Python site-packages and installed packages
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY src/ ./src/
COPY README.md ./
COPY config.example.toml ./config.example.toml

# Copy static assets
COPY static/ ./static/

# Create non-root user with specific UID/GID for better security
# Use numeric IDs to avoid dependency on /etc/passwd
RUN groupadd -r -g 1000 appuser && \
    useradd -r -u 1000 -g appuser -d /app -s /bin/false appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser:appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run the application
CMD ["python", "-m", "mvg_departures.main"]
