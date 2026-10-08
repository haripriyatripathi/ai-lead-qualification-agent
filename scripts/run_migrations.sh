#!/usr/bin/env bash
# Run Alembic migrations (use inside container or with .env loaded)
set -e
cd "$(dirname "$0")/.."
alembic upgrade head
