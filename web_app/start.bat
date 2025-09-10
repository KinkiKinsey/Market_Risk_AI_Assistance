@echo off
REM Investment Analysis Pipeline Web App Startup Script for Windows

echo 🚀 Investment Analysis Pipeline Web App
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8+ and try again
    pause
    exit /b 1
)

REM Check if we're in the right directory
if not exist "app.py" (
    echo ❌ Please run this script from the web_app directory
    echo cd web_app ^&^& start.bat
    pause
    exit /b 1
)

REM Install dependencies if needed
echo 📦 Checking dependencies...
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call venv\Scripts\activate.bat

REM Install requirements
echo 📥 Installing requirements...
pip install -r requirements.txt

REM Test the setup
echo 🧪 Testing setup...
python test_app.py

if %errorlevel% equ 0 (
    echo.
    echo 🎉 Setup complete! Starting the web app...
    echo 🌐 The app will open in your browser at http://localhost:8501
    echo 🛑 Press Ctrl+C to stop the server
    echo.
    
    REM Start Streamlit
    streamlit run app.py
) else (
    echo ❌ Setup test failed. Please check the errors above.
    pause
    exit /b 1
)

pause
