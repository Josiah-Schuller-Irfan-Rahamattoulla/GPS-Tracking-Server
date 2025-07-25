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

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy source files
COPY db/ ./db/
COPY endpoints/ ./endpoints/
COPY main.py .

# Set environment variables (optional)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Start the app using Gunicorn with Uvicorn workers
CMD ["gunicorn", "main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "4", "--log-level", "info"]

# Build command:
# docker build -t gps-tracker-server .
# Run command:
# docker run --rm -p 80:8000 -e DATABASE_URI="REDACTED" gps-tracker-server
