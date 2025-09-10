#!/bin/bash

# Investment Analysis Pipeline Web App Startup Script

echo "🚀 Investment Analysis Pipeline Web App"
echo "========================================"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is not installed or not in PATH"
    echo "Please install Python 3.8+ and try again"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "app.py" ]; then
    echo "❌ Please run this script from the web_app directory"
    echo "cd web_app && ./start.sh"
    exit 1
fi

# Install dependencies if needed
echo "📦 Checking dependencies..."
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Test the setup
echo "🧪 Testing setup..."
python test_app.py

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup complete! Starting the web app..."
    echo "🌐 The app will open in your browser at http://localhost:8501"
    echo "🛑 Press Ctrl+C to stop the server"
    echo ""
    
    # Start Streamlit
    streamlit run app.py
else
    echo "❌ Setup test failed. Please check the errors above."
    exit 1
fi
