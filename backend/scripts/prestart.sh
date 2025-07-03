#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python src/backend_pre_start.py

# Run migrations
alembic upgrade head

# Create initial data in DB
python src/initial_data.py
