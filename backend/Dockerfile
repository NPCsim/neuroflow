# ==============================================================================
# NeuroFlow Backend Dockerfile (Optimized for Render & Cloud PostgreSQL)
# Python 3.11 Slim Image
# ==============================================================================

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

# Install system dependencies (curl for container healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root application user for container security
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Install Python dependencies first (optimizing Docker layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application source code and migrations
COPY alembic.ini .
COPY alembic/ alembic/
COPY app/ app/
COPY feasibility.py .
COPY scheduler.py .
COPY start.sh .

# Normalize line endings (CRLF -> LF), make executable, and transfer ownership
RUN sed -i 's/\r$//' start.sh && \
    chmod +x start.sh && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose container port (Render maps dynamic $PORT at runtime)
EXPOSE 8000

# Health check using FastAPI /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Start container: runs Alembic migrations then starts Uvicorn
CMD ["./start.sh"]
