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
python3 -m uvicorn server:app --host 127.0.0.1 --port 8001 &
PY_PID=$!

# Wait for Python worker to fully initialize before starting Rust gateway
echo "⏳ Waiting for Python Scraper Worker to initialize..."
for i in {1..30}; do
  if curl -s http://127.0.0.1:8001/api/countries > /dev/null 2>&1; then
    echo "✅ Python Scraper Worker is live and ready on port 8001!"
    break
  fi
  sleep 0.5
done

echo "🦀 Launching Rust Axum Gateway on port ${PORT}..."
./storestock_server
