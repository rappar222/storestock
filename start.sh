#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🛑 Cleaning up port 3000..."
fuser -k 3000/tcp 2>/dev/null || true

if [ -f "./venv/bin/python" ]; then
  PYTHON="./venv/bin/python"
else
  PYTHON="python3"
fi

echo "🐍 Starting StoreStock Real Scraper Engine on http://localhost:3000 ..."
export PORT=3000
exec $PYTHON server.py 3000
