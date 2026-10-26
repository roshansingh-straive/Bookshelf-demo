#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "=========================================================="
echo "  Shelf Check: In-Store AI Shelf Scanning Demo            "
echo "  Straive Innovation · Retail Operations Platform         "
echo "=========================================================="
echo ""

# Ensure data is generated
if [ ! -f "app/public/data/store.json" ]; then
    echo ">> Generating simulated store data..."
    ./.venv/bin/python3 pipeline/build_store.py
fi

if [ ! -d "app/public/data/scans" ] || [ -z "$(ls -A app/public/data/scans 2>/dev/null)" ]; then
    echo ">> Generating replay scan results from Claude Opus 5.5..."
    ./.venv/bin/python3 pipeline/run_replay_scans.py
fi

# Ensure production bundle exists
if [ ! -d "app/dist" ]; then
    echo ">> Building web app bundle..."
    (cd app && npm run build)
fi

PORT="${PORT:-8000}"
HOST="${HOST:-127.0.0.1}"

echo ">> Starting Shelf Check local server at http://${HOST}:${PORT}"
echo ">> Replay mode active: 100% offline & reliable."
echo ">> Press Ctrl+C to stop."
echo ""

exec ./.venv/bin/uvicorn server.main:app --host "$HOST" --port "$PORT"
