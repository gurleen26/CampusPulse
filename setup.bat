@echo off
REM ---- CampusPulse setup for Windows: creates a virtual environment and installs requirements ----
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (set PY=py) else (set PY=python)
%PY% --version || (echo Python is not installed. Download it from https://www.python.org/downloads/ and tick "Add Python to PATH". & pause & exit /b 1)
if not exist venv (%PY% -m venv venv)
call venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt || (echo Installation failed. & pause & exit /b 1)
if not exist .env copy .env.example .env
echo.
echo Setup finished. Next: make sure MongoDB is running (or put your Atlas URI in .env), then double-click run.bat
pause
