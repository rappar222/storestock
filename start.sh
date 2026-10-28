#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

echo "🛑 Cleaning up ports 3000 and 8001..."
fuser -k 3000/tcp 2>/dev/null || true
fuser -k 8001/tcp 2>/dev/null || true

# Cleanup background processes on exit
cleanup() {
  echo ""
  echo "🛑 Shutting down StoreStock services..."
  kill $(jobs -p) 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 1. Start Python Scraper Engine on internal port 8001
echo "🐍 Starting Python Scraper Engine (curl_cffi / 21 Countries) on internal port 8001..."
python3 server.py 8001 &
PY_PID=$!

# Wait briefly for Python worker to bind
sleep 1.5

# 2. Start Rust Gateway on port 3000
echo "🦀 Starting Rust Axum Gateway on http://localhost:3000 ..."
export PORT=3000
export PYTHON_WORKER_URL="http://127.0.0.1:8001"
cd "$DIR/rust_server"
cargo run --release
