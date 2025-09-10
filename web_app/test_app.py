#!/usr/bin/env python3
"""
Test script for the Investment Analysis Pipeline Web App
"""

import sys
import os
import importlib

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing module imports...")
    
    # Add parent directory to path
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.append(parent_dir)
    
    required_modules = [
        'News_Verification',
        'Manager_Agent', 
        'Chain_of_Thought_Agent',
        'LLM_Call_Agent'
    ]
    
    failed_imports = []
    
    for module in required_modules:
        try:
            importlib.import_module(module)
            print(f"✅ {module} - OK")
        except ImportError as e:
            print(f"❌ {module} - FAILED: {e}")
            failed_imports.append(module)
    
    if failed_imports:
        print(f"\n❌ Failed to import: {', '.join(failed_imports)}")
        return False
    
    print("✅ All required modules imported successfully!")
    return True

def test_agent_classes():
    """Test if agent classes can be instantiated"""
    print("\n🔍 Testing agent class instantiation...")
    
    try:
        from Manager_Agent import ManagerAgent
        from Chain_of_Thought_Agent import ChainOfThoughtAgent
        
        # Test ManagerAgent
        try:
            manager = ManagerAgent("test_user")
            print("✅ ManagerAgent - OK")
        except Exception as e:
            print(f"❌ ManagerAgent - FAILED: {e}")
            return False
        
        # Test ChainOfThoughtAgent
        try:
            chain_agent = ChainOfThoughtAgent()
            print("✅ ChainOfThoughtAgent - OK")
        except Exception as e:
            print(f"❌ ChainOfThoughtAgent - FAILED: {e}")
            return False
        
        # Test News_Verification functions (not class-based)
        try:
            from News_Verification import verify_statement_with_user
            print("✅ News_Verification functions - OK")
        except Exception as e:
            print(f"❌ News_Verification functions - FAILED: {e}")
            return False
        
        print("✅ All agent classes and functions instantiated successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing agent classes: {e}")
        return False

def test_config():
    """Test configuration loading"""
    print("\n🔍 Testing configuration...")
    
    try:
        from config import Config, get_config
        
        # Test basic config
        config = Config()
        print(f"✅ Config loaded - App: {config.APP_NAME}")
        
        # Test config factory
        dev_config = get_config("development")
        prod_config = get_config("production")
        print("✅ Configuration factory - OK")
        
        # Test pipeline steps
        steps = config.PIPELINE_STEPS
        print(f"✅ Pipeline steps: {len(steps)} steps configured")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def test_dependencies():
    """Test if required Python packages are available"""
    print("\n🔍 Testing Python dependencies...")
    
    required_packages = [
        'streamlit',
        'pandas',
        'numpy',
        'requests',
        'redis',
        'langchain',
        'openai',
        'pydantic'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            importlib.import_module(package)
            print(f"✅ {package} - OK")
        except ImportError:
            print(f"❌ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️ Missing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All required packages available!")
    return True

def main():
    """Run all tests"""
    print("🚀 Investment Analysis Pipeline Web App - Test Suite")
    print("=" * 60)
    
    tests = [
        ("Dependencies", test_dependencies),
        ("Module Imports", test_imports),
        ("Agent Classes", test_agent_classes),
        ("Configuration", test_config)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n📋 Running: {test_name}")
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ {test_name} - ERROR: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
        if success:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The web app is ready to run.")
        print("\nTo launch the app:")
        print("1. cd web_app")
        print("2. python run_app.py")
        print("3. Or: streamlit run app.py")
    else:
        print("⚠️ Some tests failed. Please fix the issues before running the web app.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
