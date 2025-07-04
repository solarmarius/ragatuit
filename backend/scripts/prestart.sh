#! /usr/bin/env bash

set -e
set -x

# Let the DB start
python scripts/setup/wait_for_db.py

# Run migrations
alembic upgrade head

# Create initial data in DB
python scripts/setup/init_data.py
