#!/usr/bin/env python3
"""
Simple launcher script for the Investment Analysis Pipeline Web App
"""

import subprocess
import sys
import os
import webbrowser
import time

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = ['streamlit', 'pandas', 'numpy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Installing missing packages...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install'] + missing_packages)
            print("✅ Dependencies installed successfully!")
        except subprocess.CalledProcessError:
            print("❌ Failed to install dependencies. Please install manually:")
            print(f"pip install {' '.join(missing_packages)}")
            return False
    
    return True

def check_agent_files():
    """Check if required agent files exist in parent directory"""
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    required_files = [
        'News_Verification.py',
        'Manager_Agent.py',
        'Chain_of_Thought_Agent.py'
    ]
    
    missing_files = []
    for file in required_files:
        file_path = os.path.join(parent_dir, file)
        if not os.path.exists(file_path):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required agent files: {', '.join(missing_files)}")
        print(f"Please ensure these files exist in: {parent_dir}")
        return False
    
    print("✅ All required agent files found!")
    return True

def launch_app():
    """Launch the Streamlit app"""
    print("🚀 Launching Investment Analysis Pipeline Web App...")
    print("=" * 60)
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Change to the script directory
    os.chdir(script_dir)
    
    # Launch Streamlit
    try:
        print("Starting Streamlit server...")
        print("The app will open in your default browser automatically.")
        print("If it doesn't open, navigate to: http://localhost:8501")
        print("\nPress Ctrl+C to stop the server")
        print("=" * 60)
        
        # Wait a moment for the server to start
        time.sleep(2)
        
        # Try to open browser automatically
        try:
            webbrowser.open('http://localhost:8501')
        except:
            pass
        
        # Start Streamlit
        subprocess.run([sys.executable, '-m', 'streamlit', 'run', 'app.py'])
        
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
    except Exception as e:
        print(f"❌ Error launching app: {e}")
        return False
    
    return True

def main():
    """Main function"""
    print("🔍 Investment Analysis Pipeline Web App Launcher")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        return False
    
    # Check agent files
    if not check_agent_files():
        return False
    
    # Launch the app
    return launch_app()

if __name__ == "__main__":
    success = main()
    if not success:
        print("\n❌ Failed to launch the web app. Please check the errors above.")
        sys.exit(1)
