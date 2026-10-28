#!/usr/bin/env bash
set -e

echo "🛑 Stopping any process running on port 3000..."
fuser -k 3000/tcp 2>/dev/null || true

echo "🐍 Starting Python FastAPI StoreStock Server on port 3000..."
cd "$(dirname "$0")"
python3 server.py 3000
