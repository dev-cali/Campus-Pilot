#!/usr/bin/env bash
set -euo pipefail

echo "Initializing CampusPilot fictional AI demo..."

# Seed the isolated fictional database.
python -m ai.demo_store --reference-date "$(date -u +%Y-%m-%d)"

echo "Starting CampusPilot AI backend..."

# Start FastAPI on Render's assigned port.
exec python -m uvicorn ai.demo_api:app \
  --host 0.0.0.0 \
  --port "${PORT:?PORT must be set}"
