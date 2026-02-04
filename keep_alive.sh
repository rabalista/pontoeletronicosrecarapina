#!/bin/bash
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH"
BASE_DIR="/Users/ridan/PontoEletronico"
PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
cd "$BASE_DIR"

while true; do
    echo "[$(date)] Starting run_cloudflare.py..." >> keep_alive.log
    kill -9 $(lsof -ti:5005) 2>/dev/null
    "$PYTHON_BIN" -u run_cloudflare.py >> keep_alive.log 2>&1
    echo "[$(date)] run_cloudflare.py exited with code $?. Restarting in 2s..." >> keep_alive.log
    sleep 2
done
