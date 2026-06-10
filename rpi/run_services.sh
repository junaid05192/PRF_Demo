#!/bin/bash
cd "$(dirname "$0")"
mkdir -p logs
set -a
source .env
set +a

pkill -f mmwave_service.py 2>/dev/null
pkill -f camera_service.py 2>/dev/null
pkill -f ruuvi_service.py 2>/dev/null
sleep 1

nohup .venv/bin/python mmwave_service.py >> logs/mmwave.log 2>&1 &
disown
nohup .venv/bin/python camera_service.py >> logs/camera.log 2>&1 &
disown
nohup .venv/bin/python ruuvi_service.py >> logs/ruuvi.log 2>&1 &
disown

echo "started"
