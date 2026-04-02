@echo off
REM Script to run Solar System Sales Quote Tool locally
REM Activates virtual environment, navigates to solar_app, and starts Django development server

echo ============================================
echo Solar App - Local Development Server
echo ============================================
echo.

echo [1/3] Activating virtual environment...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    pause
    exit /b 1
)

echo [2/3] Navigating to solar_app directory...
cd solar_app
if errorlevel 1 (
    echo ERROR: Failed to change to solar_app directory
    pause
    exit /b 1
)

echo [3/3] Starting Django development server...
echo.
echo Server will be available at: http://127.0.0.1:8000/
echo Press Ctrl+C to stop the server
echo.

python manage.py runserver

pause
