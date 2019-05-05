#!/bin/sh
set -e
# Create tables once, before any worker starts.
flask --app trip_planner.wsgi init-db
exec "$@"
