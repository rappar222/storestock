#!/usr/bin/env bash
# StoreStock Quick Scraper Runner
# Executes the internet scourer inside the running Docker container

set -e

CONTAINER_NAME=$(sudo docker compose ps -q storestock 2>/dev/null || true)

if [ -z "$CONTAINER_NAME" ]; then
    echo "⚠️ StoreStock container is not running."
    echo "Starting container first..."
    sudo docker compose up -d
fi

echo "🚀 Launching StoreStock Crawler inside container..."
sudo docker compose exec storestock python crawler.py "$@"
