#!/bin/sh
set -e
# docker-compose 기본 SQLITE_PATH=/app/data/db.sqlite3 용
mkdir -p /app/data
python manage.py migrate --noinput
exec "$@"
