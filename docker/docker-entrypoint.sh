#!/usr/bin/env sh
set -e

# Run DB migrations
alembic upgrade head || {
  echo "Alembic migration failed" >&2
  exit 1
}

# Start the app
HOST="0.0.0.0"
PORT_ENV=${PORT:-8000}

exec fastapi run api/app.py --host ${HOST} --port ${PORT_ENV} --proxy-headers --forwarded-allow-ips='*'