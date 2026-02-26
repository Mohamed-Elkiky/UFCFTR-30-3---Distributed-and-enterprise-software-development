#!/bin/bash
set -e

echo "==> Waiting for PostgreSQL to be ready..."
while ! python -c "
import socket, sys, os
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect((os.environ.get('DJANGO_DB_HOST','db'), int(os.environ.get('DJANGO_DB_PORT','5432'))))
    s.close()
    sys.exit(0)
except Exception:
    sys.exit(1)
" 2>/dev/null; do
  echo "   Postgres not ready yet – retrying in 2s..."
  sleep 2
done
echo "==> PostgreSQL is up!"

echo "==> Running migrations..."
python manage.py migrate --noinput

# Load seed data only if the DB is empty (no users yet)
USER_COUNT=$(python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'brfn.settings.docker')
django.setup()
from django.contrib.auth import get_user_model
print(get_user_model().objects.count())
")

if [ "$USER_COUNT" = "0" ]; then
  echo "==> Empty database detected – loading seed data..."
  if [ -f fixtures/seed.json ]; then
    python manage.py loaddata fixtures/seed.json
    echo "==> Seed data loaded."
  else
    echo "==> No fixtures/seed.json found – skipping seed."
  fi
else
  echo "==> Database already has data ($USER_COUNT users) – skipping seed."
fi

echo "==> Starting server..."
exec "$@"
