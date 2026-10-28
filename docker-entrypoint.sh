#!/usr/bin/env bash
set -e

PORT=${PORT:-3000}
export PYTHON_WORKER_URL="http://127.0.0.1:8001"

cleanup() {
  echo "🛑 Terminating StoreStock services..."
  kill $(jobs -p) 2>/dev/null || true
  exit 0
}
trap cleanup SIGINT SIGTERM EXIT

echo "🐍 Starting Python Scraper Engine on internal port 8001..."
uvicorn server:app --host 127.0.0.1 --port 8001 &

sleep 1

echo "🦀 Launching Rust Axum Gateway on port ${PORT}..."
./storestock_server
