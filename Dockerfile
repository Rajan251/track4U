# Stage 1: Build stage
FROM python:3.12-slim as builder

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Final runtime stage
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

# Install runtime dependencies for WHOIS/SSL if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    whois \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtualenv from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create app directory for SQLite database storage
RUN mkdir -p /app/data && chmod 777 /app/data

# Copy application code
COPY . .

# Set execution permissions and create non-root user
RUN chmod +x /app/docker-entrypoint.sh && \
    useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Health check hitting /health endpoint
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["gunicorn", "app.main:app", "-w", "2", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
