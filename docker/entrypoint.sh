#!/bin/sh
set -e

# =============================================================
# Database and Redis Connectivity Polling
# =============================================================

# Extract host and port from DATABASE_URL or defaults
DB_HOST=${DB_HOST:-db}
DB_PORT=${DB_PORT:-5432}
REDIS_HOST=${REDIS_HOST:-redis}
REDIS_PORT=${REDIS_PORT:-6379}

echo "Waiting for PostgreSQL ($DB_HOST:$DB_PORT)..."
while ! nc -z "$DB_HOST" "$DB_PORT"; do
  sleep 0.5
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis ($REDIS_HOST:$REDIS_PORT)..."
while ! nc -z "$REDIS_HOST" "$REDIS_PORT"; do
  sleep 0.5
done
echo "Redis is ready!"

# =============================================================
# Run Migrations (Only executed if starting web service)
# =============================================================
if [ "$1" = "gunicorn" ]; then
    echo "Applying database migrations..."
    python manage.py migrate --noinput
fi

# =============================================================
# Execute Target Process with PID 1 Signal Forwarding
# =============================================================
exec "$@"
