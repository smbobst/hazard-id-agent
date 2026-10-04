#!/bin/bash
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "First run: setting up, this takes a minute..."
  python3 -m venv .venv
  source .venv/bin/activate
  python -m pip install --upgrade pip
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi
if [ ! -f .env ]; then
  echo ""
  echo " No .env file found. Copy .env.example to .env and add your API keys first."
  read -p "Press Enter to close."
  exit 1
fi
(sleep 2 && open http://localhost:8000) &
python app.py
