# ---- Stage 1: Install dependencies ----
FROM python:3.13-slim-bookworm AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install pip tools
RUN pip install --upgrade pip

# Copy requirements and install to a target dir
COPY requirements.txt .

# Install packages into /install so we can copy them later
RUN pip install --prefix=/install -r requirements.txt


# ---- Stage 2: Final image ----
FROM python:3.13-slim-bookworm

WORKDIR /app

# Install curl for health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source files (as an installed-style package)
COPY db/ ./api/db/
COPY endpoints/ ./api/endpoints/
COPY services/ ./api/services/
COPY agnss/ ./api/agnss/
COPY notifications/ ./api/notifications/
COPY main.py ./api/main.py

# Ensure /app is on PYTHONPATH so 'api' is importable
ENV PYTHONPATH=/app

# Set environment variables (optional)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Start the app using Gunicorn with Uvicorn workers
CMD ["gunicorn", "api.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "1", "--log-level", "info"]

# Build command:
# docker build -t gps-tracking .
# Run command:
# docker run --rm -p 8000:8000 -e DATABASE_URI="REDACTED" gps-tracking
