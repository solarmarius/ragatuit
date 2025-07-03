#! /usr/bin/env bash
set -e
set -x

python scripts/setup/wait_for_db.py

bash scripts/test.sh "$@"
