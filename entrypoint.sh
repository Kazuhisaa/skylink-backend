#!/bin/sh

# Wait for database to be ready
if [ "$DATABASE_URL" ]; then
    # Extract host and port from DATABASE_URL
    # URL format: postgresql+asyncpg://user:password@host:port/dbname
    DB_HOST=$(echo $DATABASE_URL | sed -e 's|.*@||' -e 's|:.*||' -e 's|/.*||')
    DB_PORT=$(echo $DATABASE_URL | sed -e 's|.*:||' -e 's|/.*||')
    
    # If DB_PORT is not a number, default to 5432
    if ! echo "$DB_PORT" | grep -q '^[0-9]\+$'; then
        DB_PORT=5432
    fi

    echo "Waiting for database at $DB_HOST:$DB_PORT..."
    while ! nc -z $DB_HOST $DB_PORT; do
      sleep 0.1
    done
    echo "Database is ready!"
fi

# Run migrations
echo "Running database migrations..."
alembic upgrade head

# Start application
echo "Starting FastAPI application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
