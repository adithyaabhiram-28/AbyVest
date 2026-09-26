#!/bin/sh
set -e

echo "Running database migrations..."
flask --app wsgi db upgrade

echo "Starting Gunicorn..."
exec gunicorn -b 0.0.0.0:2005 --workers 2 --timeout 120 wsgi:app
