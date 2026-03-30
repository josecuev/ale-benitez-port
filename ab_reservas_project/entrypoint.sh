#!/bin/sh
set -e
echo "==> collectstatic..."
poetry run python manage.py collectstatic --noinput
echo "==> migrate..."
poetry run python manage.py migrate --noinput
echo "==> Uvicorn..."
if [ "${DEBUG}" = "1" ]; then
  exec poetry run uvicorn ab_reservas_project.asgi:application \
    --host 0.0.0.0 --port 8000 \
    --reload \
    --proxy-headers --forwarded-allow-ips='*'
else
  exec poetry run uvicorn ab_reservas_project.asgi:application \
    --host 0.0.0.0 --port 8000 --workers 2 \
    --proxy-headers --forwarded-allow-ips='*'
fi
