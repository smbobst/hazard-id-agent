@echo off
cd /d "%~dp0"
if not exist .venv (
  echo First run: setting up, this takes a minute...
  py -3 -m venv .venv || python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  pip install -r requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
if not exist .env (
  echo.
  echo  No .env file found. Copy .env.example to .env and add your API keys first.
  pause
  exit /b
)
start "" http://localhost:8000
python app.py
pause
