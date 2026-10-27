#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install fastapi uvicorn httpx beautifulsoup4 pydantic curl_cffi
fi

echo "Starting StoreStock Core Engine on http://localhost:3000..."
./venv/bin/python server.py
