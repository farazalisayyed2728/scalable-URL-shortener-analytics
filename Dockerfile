# =============================================================
# Stage 1: Build & Dependency Compilation Stage
# =============================================================
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies required for compiling C-extensions (psycopg2, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY requirements/ /app/requirements/

# Compile Python wheels into a local cache directory
RUN pip install --upgrade pip \
    && pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements/prod.txt


# =============================================================
# Stage 2: Lean Production Runtime Stage
# =============================================================
FROM python:3.12-slim AS runner

WORKDIR /app

# Install ONLY runtime shared libraries (libpq for PostgreSQL driver)
# netcat-openbsd is used by entrypoint.sh to poll database sockets
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Copy pre-compiled wheels from builder stage and install
COPY --from=builder /app/wheels /wheels
COPY requirements/ /app/requirements/
RUN pip install --no-cache /wheels/* \
    && rm -rf /wheels

# Create an unprivileged non-root user and group
RUN groupadd -r appgroup && useradd -r -g appgroup -d /app -s /sbin/nologin appuser

# Copy application source code
COPY . /app/

# Copy and set execution permissions for the entrypoint script
COPY docker/entrypoint.sh /app/docker/entrypoint.sh
RUN chmod +x /app/docker/entrypoint.sh

# Change ownership of application directory to non-root user
RUN chown -R appuser:appgroup /app

# Switch execution context to non-root user
USER appuser

EXPOSE 8000

# Set entrypoint to run service checks and migration steps
ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Default command: Launch Gunicorn with 4 workers listening on port 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "30", "--access-logfile", "-", "--error-logfile", "-"]