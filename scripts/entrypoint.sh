#!/bin/bash
# When starting the django container, we need to wait until the postgres Db is ready to receive connections
# docker-compose "depends_on: -db" checks the container started, but is not enough to check that the database is ready to receive connections
# This scripts also accepts a command to be executed after the DB is ready (i.e migrate, runserver or a script..)

function postgres_ready(){
python << END
import sys
import psycopg2
try:
    print("Trying to connect to database '$POSTGRES_DB' on host '$POSTGRES_HOST'..")
    conn = psycopg2.connect(dbname="$POSTGRES_DB", user="$POSTGRES_USER", password="$POSTGRES_PASSWORD", host="$POSTGRES_HOST")
except psycopg2.OperationalError as e:
    print(e)
    sys.exit(-1)
sys.exit(0)
END
}

until postgres_ready; do
    >&2 echo "Postgres is unavailable - sleeping"
    sleep 1
done

>&2 echo "Postgres is up - continuing..."

# Received command is executed here
exec "$@"
