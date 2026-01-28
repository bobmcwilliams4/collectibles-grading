# Collectibles Grading System - Production Dockerfile
# Multi-stage build for optimized image size

# =============================================================================
# Stage 1: Python dependencies
# =============================================================================
FROM python:3.11-slim as python-deps

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# =============================================================================
# Stage 2: Production image
# =============================================================================
FROM python:3.11-slim as production

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libmagic1 \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from deps stage
COPY --from=python-deps /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Create non-root user for security
RUN groupadd -r grading && useradd -r -g grading grading

# Create necessary directories
RUN mkdir -p /app/data/database \
             /app/data/images \
             /app/data/cache \
             /app/logs \
    && chown -R grading:grading /app

# Copy application code
COPY --chown=grading:grading backend/ ./backend/
# Removed - ai_providers is inside backend/
# Removed - pricing_sources is inside backend/
COPY --chown=grading:grading requirements.txt ./

# Switch to non-root user
USER grading

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    APP_ENV=production

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Start command
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# =============================================================================
# Stage 3: Development image
# =============================================================================
FROM production as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    mypy \
    httpx

# Install additional dev tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    vim \
    && rm -rf /var/lib/apt/lists/*

USER grading

ENV APP_ENV=development

# Override command for development
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
