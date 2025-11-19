#!/bin/bash
set -e

echo "Starting Story Generator..."

# Generate a secret key if not provided
if [ -z "$SECRET_KEY" ]; then
    export SECRET_KEY=$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')
    echo "Generated new SECRET_KEY"
fi

# Move database and media to persistent volume if not already there
if [ ! -f /app/data/db.sqlite3 ] && [ -f /app/db.sqlite3 ]; then
    echo "Moving database to persistent volume..."
    mv /app/db.sqlite3 /app/data/db.sqlite3
fi

# Create symbolic links for persistent data
if [ ! -L /app/db.sqlite3 ]; then
    ln -sf /app/data/db.sqlite3 /app/db.sqlite3
fi

if [ ! -L /app/media ]; then
    rm -rf /app/media
    ln -sf /app/data/media /app/media
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --settings=settings_docker

# Run migrations
echo "Running database migrations..."
python manage.py migrate --noinput --settings=settings_docker

# Create superuser if environment variables are set
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ]; then
    echo "Creating superuser..."
    python manage.py shell --settings=settings_docker << END
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='$DJANGO_SUPERUSER_USERNAME').exists():
    User.objects.create_superuser('$DJANGO_SUPERUSER_USERNAME', '$DJANGO_SUPERUSER_EMAIL', '$DJANGO_SUPERUSER_PASSWORD')
    print('Superuser created.')
else:
    print('Superuser already exists.')
END
fi

echo "Story Generator is ready!"
echo "Access the application at http://localhost:8000"
if [ -n "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "Admin interface available at http://localhost:8000/admin"
    echo "Username: $DJANGO_SUPERUSER_USERNAME"
fi

# Execute the main command
exec "$@"