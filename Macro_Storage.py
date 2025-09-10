#!/usr/bin/env python3
"""
Macro Storage Agent
Handles macro-economic data storage and analysis.
"""

import sys
import os
from pathlib import Path

# Fix import paths for multiprocessing in Streamlit
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import yfinance as yf
import numpy as np
import pandas as pd
from scipy.signal import argrelextrema
from sklearn.linear_model import LinearRegression

import matplotlib.pyplot as plt
import requests
from datetime import datetime, timedelta
import copy
from typing import Dict, List, Any
from openai import OpenAI
import json
import re
import time
import logging
from multiprocessing import Pool, current_process
from functools import partial

# Configuration
API_KEY = "9dfbbfa29d93f4793f246e8fb5ca5e74"
FMP_API_KEY = '9dfbbfa29d93f4793f246e8fb5ca5e74'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('macro_storage.log')
    ]
)

def deepseek_api_call(prompt, base_url="https://api.deepseek.com", model="deepseek-chat"):
    """DeepSeek API call function - Using Shared Clients"""
    try:
        # Use shared clients for LLM operations
        try:
            from shared_clients import shared_clients
            llm_agent = shared_clients.get_llm_agent()
        except ImportError:
            # Fallback to direct LLM agent if shared clients not available
            from LLM_Call_Agent import LLMCallAgent
            llm_agent = LLMCallAgent(default_provider="deepseek", default_model=model)
        
        response = llm_agent.call_llm(
            prompt=prompt,
            provider="deepseek",
            model=model,
            system_message="You are an financial report analyst as API agent"
        )
        return response
    except Exception as e:
        print(f"❌ Error in deepseek_api_call: {e}")
        return f"Error: {str(e)}"

def download_indicator_with_dates(indicator_name, api_key, from_date, to_date):
    """
    Download economic indicator with correct FMP API parameters
    """
    url = "https://financialmodelingprep.com/stable/economic-indicators"
    
    params = {
        "name": indicator_name,
        "apikey": api_key,
        "from": from_date,
        "to": to_date
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            print(f"❌ No data for {indicator_name}")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        if 'date' in df.columns and 'value' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.sort_values('date').drop_duplicates(subset=['date'], keep='last')
            df = df.reset_index(drop=True)
            df = df[['date', 'value']]
            
            print(f"✅ {indicator_name}: {len(df)} records")
            return df
        else:
            print(f"❌ Bad format for {indicator_name}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"❌ Error downloading {indicator_name}: {e}")
        logging.error(f"Error downloading {indicator_name}: {e}")
        return pd.DataFrame()

async def download_all_indicators(start_date=None, end_date=None):
    """
    Download all indicators with custom date range
    """
    # Set default dates if not provided - CHANGED TO 1 YEAR
    if start_date is None:
        today = datetime.now()
        one_year_ago = today - timedelta(days=365)  # Changed from 10 years to 1 year
        start_date = one_year_ago.strftime("%Y-%m-%d")
    
    if end_date is None:
        end_date = datetime.now().strftime("%Y-%m-%d")
    
    # Business cycle indicators
    indicators = [
        "realGDP",
        "retailSales", 
        "CPI",
        "unemploymentRate",
        "federalFunds",
        "30YearFixedRateMortgageAverage",
        "15YearFixedRateMortgageAverage"
    ]
    
    print("🚀 Downloading Economic Indicators...")
    print(f"📅 Date Range: {start_date} to {end_date}")
    print(f"📊 Total Indicators: {len(indicators)}")
    print("=" * 80)
    
    # Download all indicators
    dataframes = {}
    for i, indicator in enumerate(indicators, 1):
        print(f"[{i:2d}/{len(indicators)}] Downloading {indicator}...")
        df = download_indicator_with_dates(indicator, API_KEY, start_date, end_date)
        
        if not df.empty:
            dataframes[indicator] = df
            print(f"   📊 Shape: {df.shape}")
            print(f"   📅 Date range: {df['date'].min().strftime('%Y-%m-%d')} to {df['date'].max().strftime('%Y-%m-%d')}")
        
        time.sleep(0.5)
    
    print(f"\n✅ Download Complete! Total indicators: {len(dataframes)}")
    return dataframes, start_date, end_date

def prepare_economic_summary(all_dfs):
    """
    Prepare economic summary for LLM analysis
    """
    print("📊 Preparing Economic Summary...")
    
    summary = {}
    
    for indicator, df in all_dfs.items():
        if not df.empty:
            # Get latest values and trends
            latest_date = df['date'].max()
            latest_value = df[df['date'] == latest_date]['value'].iloc[0]
            
            # Calculate trends (3-month and 12-month if available)
            three_months_ago = latest_date - timedelta(days=90)
            twelve_months_ago = latest_date - timedelta(days=365)
            
            three_month_value = df[df['date'] <= three_months_ago]['value'].iloc[-1] if len(df[df['date'] <= three_months_ago]) > 0 else None
            twelve_month_value = df[df['date'] <= twelve_months_ago]['value'].iloc[-1] if len(df[df['date'] <= twelve_months_ago]) > 0 else None
            
            # Convert numpy types to native Python types for JSON serialization
            def convert_numpy_types(obj):
                if hasattr(obj, 'item'):  # numpy scalar
                    return obj.item()
                elif isinstance(obj, (list, tuple)):
                    return [convert_numpy_types(x) for x in obj]
                elif isinstance(obj, dict):
                    return {k: convert_numpy_types(v) for k, v in obj.items()}
                return obj
            
            # Calculate percentage changes with proper type conversion
            three_month_change = None
            twelve_month_change = None
            
            if three_month_value is not None:
                three_month_change = ((latest_value - three_month_value) / three_month_value * 100)
                three_month_change = convert_numpy_types(three_month_change)
            
            if twelve_month_value is not None:
                twelve_month_change = ((latest_value - twelve_month_value) / twelve_month_value * 100)
                twelve_month_change = convert_numpy_types(twelve_month_change)
            
            summary[indicator] = {
                'latest_value': convert_numpy_types(latest_value),
                'latest_date': latest_date.strftime('%Y-%m-%d'),
                'start_date': df['date'].min().strftime('%Y-%m-%d'),
                'end_date': df['date'].max().strftime('%Y-%m-%d'),
                'three_month_change': three_month_change,
                'twelve_month_change': twelve_month_change
            }
    
    print("✅ Economic summary prepared!")
    return summary

def generate_llm_prompt(economic_summary):
    """
    Generate LLM prompt for business cycle analysis
    """
    prompt = f"""
# ECONOMIC BUSINESS CYCLE ANALYSIS REQUEST

Please analyze the following economic indicators and provide a comprehensive business cycle assessment:

## ECONOMIC INDICATORS DATA:
{json.dumps(economic_summary, indent=2)}

## ANALYSIS REQUIREMENTS:

### 1. Summary of Dynamic Movement
Analyze the dynamic movement of the top 5 most significant economic indicators over the timeline.

### 2. Current Business Cycle Phase
Determine the current phase of the business cycle (Expansion, Peak, Contraction, Trough, or Transition).

### 3. Risk & Opportunity Assessment
Identify key risks and opportunities in the current economic environment.

### 4. Favorable Sectors
List sectors that are likely to perform well in the current economic conditions.

### 5. Non-Favorable Sectors
List sectors that may face challenges in the current economic conditions.

## OUTPUT FORMAT:
Provide a structured analysis with clear sections for each requirement above. Use data-driven insights and explain your reasoning.
"""
    return prompt

def process_macro_data(start_date=None, end_date=None):
    """
    Main function to process macro data (NO DATABASE OPERATIONS)
    Returns processed data for DB Agent to store
    
    Args:
        start_date: Start date for data range (optional)
        end_date: End date for data range (optional)
        
    Returns:
        tuple: (all_dfs, from_date, to_date, analysis_result) or (None, None, None, None) if failed
    """
    print("🚀 MACRO STORAGE AGENT STARTING DATA PROCESSING...")
    print("=" * 60)
    
    try:
        # Step 1: Download economic indicators
        all_dfs, from_date, to_date = download_all_indicators(start_date, end_date)
        
        if not all_dfs:
            print("❌ No data was downloaded. Exiting.")
            return None, None, None, None
        
        # Step 2: Prepare economic summary
        economic_summary = prepare_economic_summary(all_dfs)
        
        # Step 3: Generate LLM prompt
        prompt = generate_llm_prompt(economic_summary)
        print("📝 LLM prompt generated!")
        
        # Step 4: Call LLM API
        print("🤖 Calling LLM API...")
        analysis_result = deepseek_api_call(prompt)
        
        if not analysis_result:
            print("❌ LLM analysis failed. Exiting.")
            return None, None, None, None
        
        print("✅ LLM analysis completed!")
        print(f"📊 Data range: {from_date} to {to_date}")
        print(f"📈 Analysis length: {len(analysis_result)} characters")
        
        return all_dfs, from_date, to_date, analysis_result
        
    except Exception as e:
        print(f"❌ Error in data processing: {e}")
        logging.error(f"Data processing error: {e}")
        return None, None, None, None

# ============================================================================
# UTILITY FUNCTIONS FOR TESTING (NO DATABASE OPERATIONS)
# ============================================================================

def test_data_download():
    """
    Test function to verify data download works
    """
    print("🧪 TESTING MACRO DATA DOWNLOAD...")
    print("=" * 50)
    
    all_dfs, from_date, to_date = download_all_indicators()
    
    if all_dfs:
        print(f"✅ Test successful!")
        print(f"📊 Downloaded {len(all_dfs)} indicators")
        print(f"📅 Date range: {from_date} to {to_date}")
        
        for indicator, df in all_dfs.items():
            print(f"   📈 {indicator}: {len(df)} records")
    else:
        print("❌ Test failed!")

def test_llm_analysis():
    """
    Test function to verify LLM analysis works
    """
    print("🧪 TESTING LLM ANALYSIS...")
    print("=" * 50)
    
    # Download sample data
    all_dfs, from_date, to_date = download_all_indicators()
    
    if not all_dfs:
        print("❌ No data to analyze!")
        return
    
    # Prepare summary
    economic_summary = prepare_economic_summary(all_dfs)
    
    # Generate prompt
    prompt = generate_llm_prompt(economic_summary)
    
    # Test LLM call
    analysis_result = deepseek_api_call(prompt)
    
    if analysis_result:
        print(f"✅ LLM test successful!")
        print(f"📝 Analysis length: {len(analysis_result)} characters")
        print(f"📊 Sample: {analysis_result[:200]}...")
    else:
        print("❌ LLM test failed!")

if __name__ == "__main__":
    print("🚀 MACRO STORAGE AGENT - TEST MODE")
    print("=" * 50)
    print("This agent only processes data. Use Macro_DB_Agent.py for database operations.")
    print()
    
    # Run other tests
    test_data_download()
    print()
    test_llm_analysis()