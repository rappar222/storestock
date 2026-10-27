#!/usr/bin/env bash
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$DIR"

if [ ! -x "venv/bin/python" ]; then
    echo "Virtual environment missing or broken, recreating..."
    rm -rf venv
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

PORT="${PORT:-3000}"
echo "Starting StoreStock Core Engine on http://localhost:$PORT..."
./venv/bin/python server.py "$PORT"
