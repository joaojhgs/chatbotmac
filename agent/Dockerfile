# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy pyproject.toml first for better dependency caching
COPY pyproject.toml .

# Install build tools
RUN pip install --upgrade pip setuptools wheel

# Copy application code (needed for package installation)
COPY app/ ./app/

# Install package and dependencies from pyproject.toml
# This will install all dependencies listed in [project.dependencies]
RUN pip install --no-build-isolation -e .

# Copy remaining files
COPY scripts/ ./scripts/
COPY *.md *.sql ./

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


