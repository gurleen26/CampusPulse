#!/usr/bin/env bash
# CampusPulse setup for Linux / macOS
cd "$(dirname "$0")"
python3 -m venv venv && source venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "Setup finished. Make sure MongoDB is running (or set MONGO_URI in .env), then run: ./run.sh"
