#!/bin/sh
set -e

echo "Waiting for DB to be ready..."
./wait-for-it.sh db:5432 -t 60

echo "Making migrations..."
python manage.py makemigrations

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Starting Daphne server..."
exec daphne -b 0.0.0.0 -p 8000 hotel_admin.asgi:application
