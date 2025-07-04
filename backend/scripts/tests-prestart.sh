#!/usr/bin/env bash

set -e
set -x

# Let the DB start
python scripts/setup/wait_for_db.py

# Create test database if it doesn't exist
python scripts/setup/create_test_db.py

# Note: We don't run migrations here as tests handle their own database setup
echo "Test database setup completed"
