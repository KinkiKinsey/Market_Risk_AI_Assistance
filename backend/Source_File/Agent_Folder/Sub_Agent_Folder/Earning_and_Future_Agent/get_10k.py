#!/usr/bin/env python3
"""
Simple 10-K Data Fetcher
Test script to see what 10-K information we can get from Financial Modeling Prep API
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

def get_form_10k_data(ticker: str, year: int = None, period: str = "FY", api_key: str = None) -> Dict[str, Any]:
    # Use centralized config if api_key not provided
    if api_key is None:
        import sys
        import os
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from config import FMP_API_KEY
        api_key = FMP_API_KEY
        if not api_key:
            raise ValueError("FMP_API_KEY is required in config.env")
    """
    Get Form 10-K data from Financial Modeling Prep API
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        year (int): Year of the report (if None, uses current year)
        period (str): Period - 'Q1', 'Q2', 'Q3', 'Q4', or 'FY' (annual)
        api_key (str): FMP API key
    
    Returns:
        Dict: Form 10-K data or error information
    """
    try:
        # Use current year if not specified
        if year is None:
            year = datetime.now().year
        
        print(f"🔍 Fetching Form 10-K data for {ticker} ({year} {period})...")
        
        # API endpoint
        # Import centralized config
        import sys
        import os
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from config import FMP_STABLE_URL
        
        url = f"{FMP_STABLE_URL}/financial-reports-json"
        
        # Parameters
        params = {
            "symbol": ticker.upper(),
            "year": year,
            "period": period,
            "apikey": api_key
        }
        
        print(f"📡 Making API request to: {url}")
        print(f"📋 Parameters: {params}")
        
        # Make the request
        response = requests.get(url, params=params, timeout=30)
        
        print(f"📊 Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            if data and len(data) > 0:
                print(f"✅ Successfully retrieved Form 10-K data for {ticker}")
                print(f"📄 Data structure preview:")
                
                # Show the structure of what we got
                first_item = data[0] if isinstance(data, list) else data
                print(f"   - Keys available: {list(first_item.keys())}")
                
                # Show some key sections
                key_sections = [
                    "Cover Page", 
                    "CONSOLIDATED STATEMENTS OF OPER", 
                    "CONSOLIDATED BALANCE SHEETS",
                    "CONSOLIDATED STATEMENTS OF CASH",
                    "Segment Information and Geograp"
                ]
                
                print(f"\n🔍 Key sections found:")
                for section in key_sections:
                    if section in first_item:
                        print(f"   ✅ {section}")
                        # Show a preview of the data
                        section_data = first_item[section]
                        if isinstance(section_data, list) and len(section_data) > 0:
                            print(f"      Preview: {str(section_data[0])[:100]}...")
                    else:
                        print(f"   ❌ {section} - Not found")
                
                return {
                    "status": "success",
                    "ticker": ticker.upper(),
                    "year": year,
                    "period": period,
                    "data": data,
                    "retrieved_at": datetime.now().isoformat(),
                    "data_source": "FMP_API"
                }
            else:
                print(f"⚠️ No data returned from API")
                return {
                    "status": "no_data",
                    "ticker": ticker.upper(),
                    "year": year,
                    "period": period,
                    "error": "No data returned from API",
                    "retrieved_at": datetime.now().isoformat()
                }
        else:
            print(f"❌ API request failed with status {response.status_code}")
            return {
                "status": "error",
                "ticker": ticker.upper(),
                "year": year,
                "period": period,
                "error": f"API request failed: {response.status_code} - {response.text}",
                "retrieved_at": datetime.now().isoformat()
            }
            
    except requests.exceptions.Timeout:
        print(f"⏰ Request timed out")
        return {
            "status": "error",
            "ticker": ticker.upper(),
            "year": year,
            "period": period,
            "error": "Request timed out",
            "retrieved_at": datetime.now().isoformat()
        }
    except requests.exceptions.RequestException as e:
        print(f"🌐 Network error: {e}")
        return {
            "status": "error",
            "ticker": ticker.upper(),
            "year": year,
            "period": period,
            "error": f"Network error: {str(e)}",
            "retrieved_at": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return {
            "status": "error",
            "ticker": ticker.upper(),
            "year": year,
            "period": period,
            "error": f"Unexpected error: {str(e)}",
            "retrieved_at": datetime.now().isoformat()
        }

def analyze_form_10k_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze the structure of Form 10-K data to understand what we have
    
    Args:
        data (Dict): Form 10-K data from API
    
    Returns:
        Dict: Analysis of the data structure
    """
    try:
        if data.get("status") != "success":
            return {"error": "No valid data to analyze"}
        
        form_data = data["data"]
        first_item = form_data[0] if isinstance(form_data, list) else form_data
        
        analysis = {
            "total_sections": len(first_item.keys()),
            "sections": list(first_item.keys()),
            "key_financial_sections": [],
            "data_types": {},
            "sample_data": {}
        }
        
        # Identify key financial sections
        financial_keywords = [
            "BALANCE SHEET", "INCOME", "CASH FLOW", "OPERATIONS", 
            "REVENUE", "ASSETS", "LIABILITIES", "EQUITY", "SEGMENT"
        ]
        
        for section_name in first_item.keys():
            for keyword in financial_keywords:
                if keyword in section_name.upper():
                    analysis["key_financial_sections"].append(section_name)
                    break
        
        # Analyze data types in each section
        for section_name, section_data in first_item.items():
            if isinstance(section_data, list):
                analysis["data_types"][section_name] = "list"
                if len(section_data) > 0:
                    analysis["sample_data"][section_name] = str(section_data[0])[:200]
            elif isinstance(section_data, dict):
                analysis["data_types"][section_name] = "dict"
                analysis["sample_data"][section_name] = str(section_data)[:200]
            else:
                analysis["data_types"][section_name] = type(section_data).__name__
        
        return analysis
        
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

def main():
    """
    Test function to try getting 10-K data for different tickers
    """
    print("🚀 Testing Form 10-K Data Fetcher")
    print("=" * 50)
    
    # Test tickers
    test_tickers = ["AAPL", "TSLA", "MSFT"]
    
    for ticker in test_tickers:
        print(f"\n📊 Testing {ticker}:")
        print("-" * 30)
        
        # Get 10-K data for current year
        result = get_form_10k_data(ticker, year=2023, period="FY")
        
        if result["status"] == "success":
            print(f"✅ Successfully got data for {ticker}")
            
            # Analyze the structure
            analysis = analyze_form_10k_structure(result)
            if "error" not in analysis:
                print(f"📋 Analysis Results:")
                print(f"   - Total sections: {analysis['total_sections']}")
                print(f"   - Key financial sections: {len(analysis['key_financial_sections'])}")
                print(f"   - Sections: {analysis['key_financial_sections']}")
            
            # Save sample data to file
            filename = f"sample_10k_{ticker.lower()}_2023.json"
            with open(filename, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"💾 Sample data saved to: {filename}")
            
        else:
            print(f"❌ Failed to get data for {ticker}: {result.get('error', 'Unknown error')}")
    
    print(f"\n🎯 Test completed!")

if __name__ == "__main__":
    main()
