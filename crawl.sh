#!/usr/bin/env bash
# StoreStock Catalog Sync Runner
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"
python3 crawler.py sync "$@"
