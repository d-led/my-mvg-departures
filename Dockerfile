FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml ./

# Create minimal README.md for build (hatchling requires it, but .dockerignore excludes *.md)
RUN echo "# my-mvg-departures" > README.md

# Install uv for faster dependency management
RUN pip install --no-cache-dir uv && \
    uv pip install --system -e .

# Copy application code
COPY src/ ./src/

COPY config.example.toml ./config.example.toml

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/')" || exit 1

# Run the application
CMD ["python", "-m", "mvg_departures.main"]


