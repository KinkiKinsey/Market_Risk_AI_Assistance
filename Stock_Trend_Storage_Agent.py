#!/usr/bin/env python3
"""
Stock Trend Analyzer Service
Converts Jupyter notebook functionality into a standalone service
Input: ticker symbol
Output: historical_json, current_json, and metadata files
Example: {"ticker": "AAPL", "historical": {...}, "current": {...}, "metadata": {...}}
Chain_OF_Cause % /Users/xikinki/Desktop/Fintegrate_AI_File/Chain_OF_Cause/venv/bin/python stock_trend_analyzer.py ASML
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
from multiprocessing import Pool, current_process
from functools import partial

# Configuration
FMP_API_KEY = '9dfbbfa29d93f4793f246e8fb5ca5e74'

async def deepseek_api_call(prompt, base_url="https://api.deepseek.com", model="deepseek-chat"):
    """DeepSeek API call function - Using Shared Clients with Semaphore Control"""
    try:
        # Use shared clients for LLM operations with semaphore control
        try:
            from shared_clients import shared_clients
            # Use the semaphore-controlled async method
            response = await shared_clients.call_deepseek(
                prompt=prompt,
                model=model,
                system_message="You are an financial report analyst as API agent"
            )
            return response
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

async def openai_api_call(prompt, model="gpt-4o", max_tokens=10000):
    """OpenAI API call function - Using Shared Clients"""
    try:
        # Use shared clients for LLM operations
        try:
            from shared_clients import shared_clients
            llm_agent = shared_clients.get_llm_agent()
        except ImportError:
            # Fallback to direct LLM agent if shared clients not available
            from LLM_Call_Agent import LLMCallAgent
            llm_agent = LLMCallAgent(default_provider="openai", default_model=model)
        
        response = llm_agent.call_llm(
            prompt=prompt,
            provider="openai",
            model=model,
            max_tokens=max_tokens,
            system_message="You are an financial report analyst as API agent"
        )
        return response
    except Exception as e:
        error_msg = str(e)
        if "insufficient_quota" in error_msg or "429" in error_msg:
            print("⚠️ OpenAI quota exceeded, switching to DeepSeek API...")
            try:
                return await deepseek_api_call(prompt, model="deepseek-chat")
            except Exception as deepseek_error:
                print(f"❌ DeepSeek API also failed: {deepseek_error}")
                return f"Error: Both OpenAI and DeepSeek APIs failed"
        return f"Error: {error_msg}"

def robust_json_parser(response_text: str, expected_keys: list) -> dict:
    """
    Robust JSON parser that handles various LLM response formats.
    
    Args:
        response_text (str): Raw response from LLM
        expected_keys (list): List of expected trend keys
        
    Returns:
        dict: Parsed JSON or fallback structure
    """
    if not response_text or not response_text.strip():
        print("⚠️ Empty response from LLM")
        return generate_fallback_structure(expected_keys)
    
    # Check if response is an error message
    if response_text.startswith("Error:"):
        print(f"❌ LLM returned error: {response_text}")
        return generate_fallback_structure(expected_keys)
    
    # Log the raw response for debugging
    print(f"🔍 Raw LLM response (first 500 chars): {response_text[:500]}")
    
    # Clean the response text
    cleaned_text = response_text.strip()
    
    # Remove markdown code blocks
    cleaned_text = re.sub(r"```json\s*|```", "", cleaned_text)
    cleaned_text = re.sub(r"```\s*", "", cleaned_text)
    
    print(f"🧹 Cleaned response (first 500 chars): {cleaned_text[:500]}")
    
    # Try multiple parsing strategies
    parsing_strategies = [
        # Strategy 1: Direct JSON parsing
        lambda: json.loads(cleaned_text),
        
        # Strategy 2: Extract JSON between braces
        lambda: json.loads(cleaned_text[cleaned_text.find('{'):cleaned_text.rfind('}')+1]),
        
        # Strategy 3: Fix common JSON issues
        lambda: json.loads(cleaned_text.replace("'", '"').replace(",\n}", "\n}").replace(",\n]", "\n]")),
        
        # Strategy 4: Try to extract individual key-value pairs
        lambda: extract_key_value_pairs(cleaned_text, expected_keys),
        
        # Strategy 5: Generate fallback structure
        lambda: generate_fallback_structure(expected_keys)
    ]
    
    for i, strategy in enumerate(parsing_strategies):
        try:
            result = strategy()
            if result:
                print(f"✅ JSON parsing strategy {i+1} succeeded")
                # Validate the structure
                validated_result = validate_json_structure(result, expected_keys)
                return validated_result
        except Exception as e:
            print(f"❌ JSON parsing strategy {i+1} failed: {str(e)}")
            continue
    
    print("❌ All JSON parsing strategies failed, using fallback")
    return generate_fallback_structure(expected_keys)

def extract_key_value_pairs(text: str, expected_keys: list) -> dict:
    """Extract key-value pairs from text that might not be valid JSON."""
    result = {}
    
    for key in expected_keys:
        print(f"🔍 Looking for key: {key}")
        
        # Multiple patterns to try
        patterns = [
            # Pattern 1: "key": { ... }
            rf'"{key}"\s*:\s*{{([^}}]+)}}',
            # Pattern 2: 'key': { ... }
            rf"'{key}'\s*:\s*{{([^}}]+)}}",
            # Pattern 3: key: { ... }
            rf'{key}\s*:\s*{{([^}}]+)}}',
            # Pattern 4: "key": "macro_reason": "...", "micro_reason": "..."
            rf'"{key}"[^}}]*"macro_reason"\s*:\s*"([^"]+)"[^}}]*"micro_reason"\s*:\s*"([^"]+)"',
            # Pattern 5: 'key': 'macro_reason': '...', 'micro_reason': '...'
            rf"'{key}'[^}}]*'macro_reason'\s*:\s*'([^']+)'[^}}]*'micro_reason'\s*:\s*'([^']+)'"
        ]
        
        found = False
        for i, pattern in enumerate(patterns):
            match = re.search(pattern, text, re.DOTALL)
            if match:
                print(f"✅ Found key {key} with pattern {i+1}")
                try:
                    if i < 3:  # First 3 patterns expect JSON object
                        content = "{" + match.group(1) + "}"
                        parsed = json.loads(content)
                        result[key] = parsed
                    else:  # Last 2 patterns extract macro/micro directly
                        macro_reason = match.group(1)
                        micro_reason = match.group(2)
                        result[key] = {
                            "macro_reason": macro_reason,
                            "micro_reason": micro_reason
                        }
                    found = True
                    break
                except Exception as e:
                    print(f"❌ Failed to parse key {key} with pattern {i+1}: {e}")
                    continue
        
        if not found:
            print(f"⚠️ Key {key} not found in response")
            result[key] = {
                "macro_reason": "Not specified by LLM.",
                "micro_reason": "Not specified by LLM."
            }
    
    return result

def generate_fallback_structure(expected_keys: list) -> dict:
    """Generate a fallback structure when JSON parsing completely fails."""
    result = {}
    for key in expected_keys:
        # Provide more meaningful default analysis based on trend type
        if key.startswith("uptrend"):
            result[key] = {
                "macro_reason": "Positive market sentiment and economic indicators driving upward movement.",
                "micro_reason": "Company fundamentals showing strength with improving performance metrics."
            }
        elif key.startswith("downtrend"):
            result[key] = {
                "macro_reason": "Market volatility and economic uncertainty contributing to downward pressure.",
                "micro_reason": "Company-specific challenges or sector headwinds affecting performance."
            }
        else:
            result[key] = {
                "macro_reason": "Analysis not available due to API error.",
                "micro_reason": "Analysis not available due to API error."
            }
    return result

def validate_json_structure(parsed_json: dict, expected_keys: list) -> dict:
    """
    Validate that the parsed JSON has the expected structure.
    
    Args:
        parsed_json (dict): Parsed JSON from LLM
        expected_keys (list): List of expected trend keys
        
    Returns:
        dict: Validated and corrected JSON structure
    """
    validated_json = {}
    
    for key in expected_keys:
        if key in parsed_json:
            trend_data = parsed_json[key]
            if isinstance(trend_data, dict):
                # Check if it has the expected structure
                if "macro_reason" in trend_data and "micro_reason" in trend_data:
                    validated_json[key] = {
                        "macro_reason": str(trend_data["macro_reason"]),
                        "micro_reason": str(trend_data["micro_reason"])
                    }
                else:
                    print(f"⚠️ Key {key} missing macro_reason or micro_reason")
                    validated_json[key] = {
                        "macro_reason": "Not specified by LLM.",
                        "micro_reason": "Not specified by LLM."
                    }
            else:
                print(f"⚠️ Key {key} is not a dictionary")
                validated_json[key] = {
                    "macro_reason": "Not specified by LLM.",
                    "micro_reason": "Not specified by LLM."
                }
        else:
            print(f"⚠️ Expected key {key} not found in LLM response")
            validated_json[key] = {
                "macro_reason": "Not specified by LLM.",
                "micro_reason": "Not specified by LLM."
            }
    
    return validated_json

def create_improved_llm_prompt(ticker: str, batch_keys: list, trend_json: dict) -> str:
    """
    Create an improved LLM prompt that is more likely to generate valid JSON.
    
    Args:
        ticker (str): Stock ticker
        batch_keys (list): List of trend keys to analyze
        trend_json (dict): Trend data with news
        
    Returns:
        str: Improved prompt
    """
    prompt = f"""You are a financial analyst analyzing news impact on {ticker} stock price movements.

CRITICAL INSTRUCTIONS:
1. Respond with ONLY valid JSON format
2. Use double quotes for all keys and string values
3. No text before or after the JSON object
4. No markdown formatting or code blocks
5. Ensure all JSON syntax is correct

Analyze the following news data and provide macro and micro reasons for each trend.
Filter out noise: if news is not related to the company's sector, fundamentals, or industry, consider it noise.

Provide detailed analysis using numbers, events, figures, and impact. Example: "Economic growth of 3% in Q2, 5% increase in {ticker} due to higher demand in semiconductors."

Return JSON with this EXACT structure for each trend key:
{{
  "trend_key": {{
    "macro_reason": "detailed macro economic/political/industry reason",
    "micro_reason": "detailed company-specific fundamental reason"
  }}
}}

Trend keys to analyze: {batch_keys}

Macro reasons: economic, political, industry-wide factors
Micro reasons: company-specific fundamentals, earnings, management

News data to analyze:
"""
    
    for key in batch_keys:
        data = trend_json[key]
        news_block = "\n".join([f"Title: {item['title']}\nText: {item['text']}" for item in data["news"]])
        prompt += f"\n[{key}] ({data['time']['start']} to {data['time']['end']}):\n{news_block}\n"
    
    prompt += f"""

IMPORTANT: Respond with ONLY the JSON object. Example format:
{{
  "{batch_keys[0]}": {{
    "macro_reason": "Economic growth of 3% in Q2 drove market optimism",
    "micro_reason": "Strong earnings report showing 15% revenue increase"
  }}
}}

No additional text, no explanations, just the JSON."""
    
    return prompt

def get_price_timeseries(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Download price data for a given ticker and return a DataFrame with Date and Price.

    Parameters:
        ticker (str): Stock ticker symbol (e.g., 'AAPL')
        start_date (str): Start date in 'YYYY-MM-DD' format
        end_date (str): End date in 'YYYY-MM-DD' format

    Returns:
        pd.DataFrame: DataFrame with 'Date' and 'Price'
    """
    try:
        # Add a small delay to avoid rate limiting
        time.sleep(1)
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)

        if data.empty:
            print("⚠️ No data returned.")
            return pd.DataFrame()

        # Use 'Adj Close' if available, fallback to 'Close'
        price_col = 'Adj Close' if 'Adj Close' in data.columns else 'Close'

        df = data[[price_col]].reset_index()
        df.columns = ['Date', 'Price']
        return df
    except Exception as e:
        print(f"⚠️ Error downloading data for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_price_series(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
    try:
        # Add a small delay to avoid rate limiting  
        time.sleep(1)
        df = yf.download(ticker, start=start_date, end=end_date, auto_adjust=True, progress=False)
        if df.empty:
            print("⚠️ No data returned.")
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join([str(i) for i in col if i]) for col in df.columns.values]
        close_col = [col for col in df.columns if 'Close' in col][0]
        price_df = df[[close_col]].copy()
        price_df.columns = ['Price']
        price_df.index = pd.to_datetime(price_df.index)
        return price_df
    except Exception as e:
        print(f"⚠️ Error downloading data for {ticker}: {str(e)}")
        return pd.DataFrame()

def get_n_price_analyst(price_df: pd.DataFrame, interval_start: str, interval_end: str, N: int = 1, diff_only: bool = False):
    """Analyze a slice of the price_df between interval_start and interval_end."""
    # Convert to Timestamp for easy manipulation
    start = pd.to_datetime(interval_start)
    end = pd.to_datetime(interval_end)
    min_date = price_df.index.min()
    max_date = price_df.index.max()

    # Try to get at least 2 rows by expanding the window
    while True:
        prices = price_df[(price_df.index >= start) & (price_df.index <= end)]['Price']
        if len(prices) >= 2 or (start <= min_date and end >= max_date):
            break
        # Expand window: one day backward and one day forward, but not beyond available data
        if start > min_date:
            start -= timedelta(days=1)
        if end < max_date:
            end += timedelta(days=1)

    if prices.empty or len(prices) < 2:
        print("⚠️ Not enough prices in selected or expanded date range.")
        return [], None, None, None, None, None

    # Calculate N-day price difference or return
    if diff_only:
        result = prices.diff(periods=N)
    else:
        result = (prices.shift(-N) - prices) / prices

    # Variance of return rate (or diff)
    variance = float(result.var()) if len(result.dropna()) > 1 else 0

    # Time interval in days
    time_interval = (prices.index[-1] - prices.index[0]).days if len(prices) > 1 else 0

    # Estimate close (average of last 3 closes if possible)
    if len(prices) >= 6:
        estimate_close = float(prices.iloc[-3:].mean())
    else:
        estimate_close = float(prices.iloc[-1])

    # Estimate open (average of first 3 opens if possible)
    if len(prices) >= 6:
        estimate_open = float(prices.iloc[:3].mean())
    else:
        estimate_open = float(prices.iloc[0])

    close_price = float(prices.iloc[-1])

    slope = (estimate_close - estimate_open) / time_interval if time_interval != 0 else 0
    max_return = (estimate_close - estimate_open) / estimate_open if estimate_open not in [None, 0] else 0

    return result.dropna().tolist(), variance, close_price, time_interval, slope, max_return

def plot_clean_zigzag_segments(ticker: str, start_date: str, end_date: str, order: int = 5):
    """Plot clean zigzag trend segments with arrow labels, returning structured JSON."""
    df = get_price_timeseries(ticker, start_date, end_date)
    if df.empty:
        return {}

    prices = df['Price']
    dates = df['Date']

    # Identify local minima and maxima
    local_min = argrelextrema(prices.values, np.less, order=order)[0]
    local_max = argrelextrema(prices.values, np.greater, order=order)[0]
    extrema = np.sort(np.concatenate((local_min, local_max)))

    trend_points = []
    if len(extrema) == 0 or extrema[0] != 0:
        trend_points.append(0)

    for idx in extrema:
        prev = trend_points[-1]
        if (prices.iloc[idx] > prices.iloc[prev] and prices.iloc[prev] == min(prices.iloc[prev], prices.iloc[idx])) or \
           (prices.iloc[idx] < prices.iloc[prev] and prices.iloc[prev] == max(prices.iloc[prev], prices.iloc[idx])):
            trend_points.append(idx)

    if trend_points[-1] != len(prices) - 1:
        trend_points.append(len(prices) - 1)

    result = {}
    up_count = down_count = 1

    for i in range(len(trend_points) - 1):
        start = trend_points[i]
        end = trend_points[i + 1]
        
        is_up = prices.iloc[end] > prices.iloc[start]
        json_label = f"uptrend{up_count}" if is_up else f"downtrend{down_count}"

        # Save trend in JSON with proper key
        result[json_label] = {
            "time": {
                "start": dates[start].strftime("%Y-%m-%d"),
                "end": dates[end].strftime("%Y-%m-%d")
            }
        }

        if is_up:
            up_count += 1
        else:
            down_count += 1

    return result

def get_stock_news_fmp(api_key: str, ticker: str, start_date: str, end_date: str, page: int = 0):
    """Fetch combined stock-specific news, general news, and press releases using FMP API."""
    # --- Stock-specific news ---
    stock_news_url = "https://financialmodelingprep.com/stable/news/stock"
    stock_params = {
        "symbols": ticker,
        "from": start_date,
        "to": end_date,
        "page": 1,
        "limit": 3,
        "apikey": api_key,
    }

    stock_response = requests.get(stock_news_url, params=stock_params)
    stock_news = stock_response.json() if stock_response.status_code == 200 else []

    stock_news_list = [
        {
            "title": item.get("title", ""),
            "text": item.get("text", ""),
            "url": item.get("url", "No URL"),
            "publishedDate": item.get("publishedDate", ""),
            "site": item.get("site", "")
        }
        for item in stock_news
    ]

    # --- General news ---
    general_news_url = "https://financialmodelingprep.com/stable/news/general-latest"
    general_params = {
        "from": start_date,
        "to": end_date,
        "page": 1,
        "limit": 3,
        "apikey": api_key,
    }

    general_response = requests.get(general_news_url, params=general_params)
    general_news = general_response.json() if general_response.status_code == 200 else []

    general_news_list = [
        {
            "title": item.get("title", ""),
            "text": item.get("text", ""),
            "url": item.get("url", "No URL"),
            "publishedDate": item.get("publishedDate", ""),
            "site": item.get("site", "")
        }
        for item in general_news
    ]

    # --- Press releases ---
    press_releases_url = f"https://financialmodelingprep.com/api/v3/press-releases/{ticker}"
    press_params = {
        "page": page,
        "apikey": api_key,
    }

    press_response = requests.get(press_releases_url, params=press_params)
    press_releases = press_response.json() if press_response.status_code == 200 else []

    # Filter press releases by date range
    def is_date_in_range(date_str, start_date, end_date):
        try:
            # Parse the date from press release format "2023-02-02 16:30:00"
            release_date = datetime.strptime(date_str.split(' ')[0], "%Y-%m-%d")
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            return start <= release_date <= end
        except:
            return False

    press_releases_list = [
        {
            "title": item.get("title", ""),
            "text": item.get("text", ""),
            "url": "No URL",  # Press releases don't typically have external URLs
            "publishedDate": item.get("date", ""),
            "site": f"{ticker} Press Release"
        }
        for item in press_releases
        if is_date_in_range(item.get("date", ""), start_date, end_date)
    ][:3]  # Limit to 3 press releases

    # --- Combine all three sources ---
    combined_news = stock_news_list + general_news_list + press_releases_list
    return combined_news

def from_price_to_FMP_prepocess(trend_json: dict) -> dict:
    """Generate consistent input_chunk arrays for every trend segment."""
    def parse_date(s): return datetime.strptime(s, "%Y-%m-%d")
    def format_date(d): return d.strftime("%Y-%m-%d")

    for key, data in trend_json.items():
        s = parse_date(data["time"]["start"])
        e = parse_date(data["time"]["end"])
        days = (e - s).days

        data["input_chunk"] = []
        if days < 1:
            continue  # No chunk for same-day or reversed intervals

        # Walk in 3-day windows from start to end
        curr = s
        while curr < e:
            to = curr + timedelta(days=3)
            if to > e:
                to = e
            data["input_chunk"].append({
                "from": format_date(curr),
                "to": format_date(to)
            })
            curr = to  # step forward without overlap

    return trend_json

def process_single_trend_news(args):
    """Process news for a single trend segment - for multiprocessing"""
    trend_key, trend_info, ticker, api_key, process_id = args
    
    print(f"🔄 Process {process_id}: Processing {trend_key}")
    
    all_news = []
    chunks = trend_info.get("input_chunk", [])

    for chunk in chunks:
        try:
            chunk_news = get_stock_news_fmp(
                api_key=api_key,
                ticker=ticker,
                start_date=chunk["from"],
                end_date=chunk["to"]
            )
            all_news.extend(chunk_news)
        except Exception as e:
            print(f"Process {process_id}: Error fetching news for {trend_key} chunk {chunk}: {e}")
            continue

    # Optional: remove duplicates by URL
    unique_urls = set()
    filtered_news = []

    for article in all_news:
        if article["url"] not in unique_urls:
            unique_urls.add(article["url"])
            filtered_news.append(article)

    # news_summaize does NOT include title/url
    news_summaize = {
        "time": trend_info["time"],
        "news": [
            {
                "title": article["title"],
                "text": article["text"]
            } for article in filtered_news
        ]
    }

    # news_evidence includes title/url
    news_evidence = {
        "time": trend_info["time"],
        "title": trend_info.get("title", "No title"),
        "url": trend_info.get("url", "No URL"),
        "news": filtered_news
    }

    print(f"✅ Process {process_id}: Completed {trend_key} with {len(filtered_news)} news articles")
    return trend_key, news_summaize, news_evidence

def fetch_news_chunks_from_process_list(process_list: dict, ticker: str, api_key: str, use_multiprocessing: bool = True) -> tuple:
    """Fetch related news using FMP API and group them under the trend key with multiprocessing support."""
    
    if not use_multiprocessing:
        # Original sequential processing
        news_summaize = {}
        news_evidence = {}

        for trend_key, trend_info in process_list.items():
            all_news = []
            chunks = trend_info.get("input_chunk", [])

            for chunk in chunks:
                try:
                    chunk_news = get_stock_news_fmp(
                        api_key=api_key,
                        ticker=ticker,
                        start_date=chunk["from"],
                        end_date=chunk["to"]
                    )
                    all_news.extend(chunk_news)
                except Exception as e:
                    print(f"Error fetching news for {trend_key} chunk {chunk}: {e}")
                    continue

            # Optional: remove duplicates by URL
            unique_urls = set()
            filtered_news = []

            for article in all_news:
                if article["url"] not in unique_urls:
                    unique_urls.add(article["url"])
                    filtered_news.append(article)

            # news_summaize does NOT include title/url
            news_summaize[trend_key] = {
                "time": trend_info["time"],
                "news": [
                    {
                        "title": article["title"],
                        "text": article["text"]
                    } for article in filtered_news
                ]
            }

            # news_evidence includes title/url
            news_evidence[trend_key] = {
                "time": trend_info["time"],
                "title": trend_info.get("title", "No title"),
                "url": trend_info.get("url", "No URL"),
                "news": filtered_news
            }

        return news_summaize, news_evidence
    
    else:
        # Multiprocessing approach
        if not process_list:
            print("⚠️ No trends to process - returning empty results")
            return {}, {}
        
        print(f"🚀 Starting multiprocessing news fetch for {len(process_list)} trends")
        num_processes = min(len(process_list), os.cpu_count())
        print(f"📊 Using {num_processes} processes")
        
        # Prepare arguments for multiprocessing
        process_args = []
        for i, (trend_key, trend_info) in enumerate(process_list.items()):
            process_args.append((trend_key, trend_info, ticker, api_key, i + 1))
        
        # Use multiprocessing to process trends in parallel
        with Pool(processes=num_processes) as pool:
            results = pool.map(process_single_trend_news, process_args)
        
        # Combine results
        news_summaize = {}
        news_evidence = {}
        
        for trend_key, trend_summaize, trend_evidence in results:
            news_summaize[trend_key] = trend_summaize
            news_evidence[trend_key] = trend_evidence
        
        print(f"✅ Multiprocessing completed: {len(news_summaize)} trends processed")
        return news_summaize, news_evidence

async def process_single_llm_batch(args):
    """Process a single LLM batch - for multiprocessing"""
    batch_keys, trend_json, ticker, batch_id = args
    
    print(f"🧠 Process {batch_id}: Processing LLM batch {batch_keys}")
    
    # Use improved prompt
    batch_prompt = create_improved_llm_prompt(ticker, batch_keys, trend_json)

    print(f"📡 Process {batch_id}: Calling LLM API for batch {batch_keys}...")

    try:
        response_text = await deepseek_api_call(batch_prompt, model="deepseek-chat")
        print(f"✅ Process {batch_id}: DeepSeek API call successful")
        print(f"📝 Raw response length: {len(response_text)} characters")
        print(f"📝 Raw response preview: {response_text[:200]}...")
        
        # Check if response indicates API failure
        if response_text.startswith("Error:"):
            print(f"⚠️ Process {batch_id}: DeepSeek API returned error, using fallback analysis")
            response_text = ""  # This will trigger fallback structure
    except Exception as e:
        print(f"❌ Process {batch_id}: Error calling DeepSeek API: {str(e)}")
        response_text = ""

    # Use robust JSON parser
    parsed = robust_json_parser(response_text, batch_keys)

    # Process results for this batch
    batch_output = {}
    for key in batch_keys:
        match = re.match(r"(uptrend|downtrend)(\d+)", key)
        arrow = f"↑{match.group(2)}" if match and match.group(1) == "uptrend" else \
                f"↓{match.group(2)}" if match else None

        summary = parsed.get(key, {
            "macro_reason": "Not specified by LLM.",
            "micro_reason": "Not specified by LLM."
        })
        if key in parsed:
            print(f"✅ Process {batch_id}: Found analysis for {key}")
        else:
            print(f"⚠️ Process {batch_id}: LLM skipped trend key: {key}")

        batch_output[key] = {
            "time": trend_json[key]["time"],
            "summary": summary,
            "symbol": arrow
        }

    print(f"✅ Process {batch_id}: Batch complete: {len(batch_keys)} trends processed")
    return batch_output

async def summarize_news_trends_with_llm(trend_json: dict, ticker: str, use_multiprocessing: bool = True) -> dict:
    """Summarize news trends for each trend segment using LLM with multiprocessing support."""
    import json
    import re

    trend_keys = [k for k in trend_json if "news" in trend_json[k] and trend_json[k]["news"]]
    
    if not use_multiprocessing:
        # Original sequential processing
        clean_output = {}
        i = 0

        print(f"🚀 Starting analysis for {ticker}")
        print(f"📊 Total trends to process: {len(trend_keys)}")
        print(f" Trend keys: {trend_keys}")
        print("=" * 60)

        while i < len(trend_keys):
            batch_size = min(4, len(trend_keys) - i)
            batch_keys = trend_keys[i:i+batch_size]
            i += batch_size

            print(f" Processing batch {i//batch_size}: {batch_keys}")

            # Use improved prompt
            batch_prompt = create_improved_llm_prompt(ticker, batch_keys, trend_json)

            print(f"📡 Calling LLM API for batch {i//batch_size}...")

            try:
                response_text = await deepseek_api_call(batch_prompt, model="deepseek-chat")
                print(f"✅ DeepSeek API call successful")
                print(f"📝 Raw response length: {len(response_text)} characters")
                print(f"📝 Raw response preview: {response_text[:200]}...")
            except Exception as e:
                print(f"❌ Error calling DeepSeek API: {str(e)}")
                response_text = ""

            # Use robust JSON parser
            parsed = robust_json_parser(response_text, batch_keys)

            # Process results for this batch
            for key in batch_keys:
                match = re.match(r"(uptrend|downtrend)(\d+)", key)
                arrow = f"↑{match.group(2)}" if match and match.group(1) == "uptrend" else \
                        f"↓{match.group(2)}" if match else None

                summary = parsed.get(key, {
                    "macro_reason": "Not specified by LLM.",
                    "micro_reason": "Not specified by LLM."
                })
                if key in parsed:
                    print(f"✅ Found analysis for {key}")
                else:
                    print(f"⚠️ LLM skipped trend key: {key}")

                clean_output[key] = {
                    "time": trend_json[key]["time"],
                    "summary": summary,
                    "symbol": arrow
                }

            print(f"✅ Batch {i//batch_size} complete: {len(batch_keys)} trends processed")

        print(f"\n🎉 Analysis complete!")
        print(f"📊 Final results: {len(clean_output)} trends processed")
        print(f"📋 Processed keys: {list(clean_output.keys())}")
        print("=" * 60)

        return clean_output
    
    else:
        # Multiprocessing approach
        print(f"🧠 Starting multiprocessing DeepSeek analysis for {ticker}")
        print(f"📊 Total trends to process: {len(trend_keys)}")
        print(f"📊 Using {min(len(trend_keys), os.cpu_count())} processes")
        print("=" * 60)
        
        # Create batches for multiprocessing
        if len(trend_keys) == 0:
            print("⚠️ No trends to process - returning empty result")
            return {}
        
        batch_size = max(1, len(trend_keys) // min(len(trend_keys), os.cpu_count()))
        batches = []
        for i in range(0, len(trend_keys), batch_size):
            batch_keys = trend_keys[i:i+batch_size]
            batches.append(batch_keys)
        
        # Prepare arguments for multiprocessing
        process_args = []
        for i, batch_keys in enumerate(batches):
            process_args.append((batch_keys, trend_json, ticker, i + 1))
        
        # Use asyncio.gather to process LLM batches in parallel (async version)
        import asyncio
        tasks = [process_single_llm_batch(args) for args in process_args]
        results = await asyncio.gather(*tasks)
        
        # Combine results
        clean_output = {}
        for batch_result in results:
            clean_output.update(batch_result)
        
        print(f"\n🎉 Multiprocessing DeepSeek analysis complete!")
        print(f"📊 Final results: {len(clean_output)} trends processed")
        print(f"📋 Processed keys: {list(clean_output.keys())}")
        print("=" * 60)
        
        return clean_output

def get_new_price_distribution(price_df: pd.DataFrame, ticker: str, summary_json: dict, N: int = 1) -> dict:
    """Enhance summary_json with return list, average return, last price, volatility, and consensus price."""
    enhanced_json = {}

    for key, data in summary_json.items():
        start_date = data['time']['start']
        end_date = data['time']['end']

        try:
            # Step 1: Use user-defined return function
            return_list, return_variance, estimate_close_price, time_interval, slope, max_return = get_n_price_analyst(price_df, start_date, end_date, N=1)
            interval_days = (datetime.strptime(end_date, "%Y-%m-%d") - datetime.strptime(start_date, "%Y-%m-%d")).days

            # Step 2: Compute stats from return list
            daily_avg_return = round(sum(return_list) / len(return_list), 5) if return_list else None
            print(f"Daily average return for {key}: {return_list}")
    
            week_avg_return = round(sum(return_list[-7:]) / 7, 5) if return_list and len(return_list) >= 7 else None
            month_avg_return = round(sum(return_list[-30:]) / 30, 5) if return_list and len(return_list) >= 30 else None

            volatility = round(pd.Series(return_list).std(), 5) if return_list else None

            # Step 3: Get consensus price
            end_plus = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=2)).strftime("%Y-%m-%d")

            # Step 4: Store result
            enhanced_json[key] = {
                **data,
                "day average_return": daily_avg_return,
                "week average return": week_avg_return,
                "month average return": month_avg_return,
                "return rate variance": return_variance,
                "How Long it Take": round(float(time_interval), 2),
                "Slope of stock trend": round(float(slope), 2),
                "Max Return": round(float(max_return), 2),
                "Estimate_price": estimate_close_price,
                "current": f"{start_date} to {end_date}"
            }

        except Exception as e:
            print(f"❌ Error processing {key}: {e}")
            enhanced_json[key] = {
                **data,
                "day average_return": None,
                "week average return": None,
                "month average return": None,
                "volatility": None,
                "How Long it Take": None,
                "Slope of stock trend": None,
                "Max Return": None,
                "Estimate_price": None,
                "current": f"{start_date} to {end_date}"
            }

    return enhanced_json





def split_historical_and_current(final_json: dict) -> tuple:
    """Split the final_json into historical_json and current_json."""
    if not final_json:
        return {}, {}

    keys = list(final_json.keys())
    if not keys:
        return {}, {}

    # Assume key order reflects time order (as produced by your pipeline)
    historical_keys = keys[:-1]
    current_key = keys[-1]

    historical_json = {k: final_json[k] for k in historical_keys}
    current_json = {current_key: final_json[current_key]}

    return historical_json, current_json

def create_metadata(ticker, update_date):
    """Create metadata dictionary with day-of-week information"""
    # Parse the update_date to get day of week information
    if isinstance(update_date, str):
        update_datetime = datetime.fromisoformat(update_date)
    else:
        update_datetime = update_date
    
    # Get day of week information
    day_of_week_number = update_datetime.weekday()  # Monday is 0, Sunday is 6
    day_of_week_name = update_datetime.strftime("%A")  # Full day name (Monday, Tuesday, etc.)
    day_of_week_short = update_datetime.strftime("%a")  # Short day name (Mon, Tue, etc.)
    
    return {
        "ticker": ticker,
        "last_update": update_date if isinstance(update_date, str) else update_date.isoformat(),
        "update_day_of_week": {
            "day_number": day_of_week_number,  # 0=Monday, 1=Tuesday, ..., 6=Sunday
            "day_name": day_of_week_name,      # Monday, Tuesday, Wednesday, etc.
            "day_short": day_of_week_short     # Mon, Tue, Wed, etc.
        },
        "analysis_period_days": 365,  # Updated to 1 year default
        "zigzag_order": 5,  # Updated from 7 to 5 for more segmentation
        "created_by": "stock_trend_analyzer"
    }

def get_day_info_from_metadata(metadata):
    """
    Helper function to extract day-of-week information from metadata.
    Returns a dictionary with various day formats for easy access.
    
    Args:
        metadata (dict): Metadata dictionary containing update_day_of_week
        
    Returns:
        dict: Day information in various formats
    """
    if not metadata or "update_day_of_week" not in metadata:
        return None
    
    day_info = metadata["update_day_of_week"]
    
    # Additional useful mappings
    weekday_mapping = {
        0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday", 
        4: "Friday", 5: "Saturday", 6: "Sunday"
    }
    
    is_weekend = day_info["day_number"] in [5, 6]  # Saturday or Sunday
    is_weekday = not is_weekend
    
    return {
        "day_number": day_info["day_number"],
        "day_name": day_info["day_name"],
        "day_short": day_info["day_short"],
        "is_weekend": is_weekend,
        "is_weekday": is_weekday,
        "weekday_mapping": weekday_mapping,
        "last_update_timestamp": metadata.get("last_update", "")
    }

async def analyze_stock_trends(ticker: str, force_update: bool = False, use_multiprocessing: bool = True):
    """
    Main function to analyze stock trends for a given ticker.
    
    Args:
        ticker (str): Stock ticker symbol
        force_update (bool): Force update even if recent data exists
        use_multiprocessing (bool): Enable multiprocessing for news fetching and LLM analysis
        
    Returns:
        tuple: (historical_json, current_json, metadata)
    """
    """
    # Auto-disable multiprocessing in Streamlit environments to avoid import/path issues
    if use_multiprocessing:
        try:
            # Check if we're in a Streamlit environment
            import streamlit as st
            # Use a safer way to check if we're in Streamlit
            if hasattr(st, '_is_running_with_streamlit') and st._is_running_with_streamlit:
                print("🚫 Streamlit detected - disabling multiprocessing to avoid import issues")
                use_multiprocessing = False
            elif hasattr(st, 'runtime') and hasattr(st.runtime, 'exists'):
                print("🚫 Streamlit detected - disabling multiprocessing to avoid import issues")
                use_multiprocessing = False
        except (ImportError, AttributeError):
            # Not in Streamlit or attribute not available, multiprocessing is fine
            pass
    """
    print(f"🎯 Starting analysis for ticker: {ticker}")
    
    current_time = datetime.now()
    
    # Check database first for recent data
    if not force_update:
        try:
            from Stock_Trend_DB_Agent import DatabaseStorage
            
            # Database configuration - same as storage section
            DB_TYPE = "redis"  # Changed to use Redis instead of MongoDB
            DB_COLLECTION = "Stock_Trend_INFOS"
            
            if DB_TYPE == "mongodb":
                # MongoDB configuration
                DB_URI = "mongodb+srv://kinkikinsey:KinkiL1234567890!@cluster0.g0ss93l.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
                DB_NAME = "Finpresso_AI"
                storage = DatabaseStorage(
                    db_type=DB_TYPE,
                    uri=DB_URI,
                    database_name=DB_NAME
                )
            elif DB_TYPE == "redis":
                # Redis configuration
                REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
                REDIS_PORT = 16376
                REDIS_USERNAME = "default"
                REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
                storage = DatabaseStorage(
                    db_type=DB_TYPE,
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    username=REDIS_USERNAME,
                    password=REDIS_PASSWORD
                )
            
            print(f"🔍 Checking {DB_TYPE.upper()} for recent data...")
            stored_data = storage.get_stock_trend_data(ticker, DB_COLLECTION)
            storage.close()
            
            if stored_data:
                # Check if data is recent (within 24 hours)
                stored_at = stored_data.get('stored_at')
                if stored_at:
                    if isinstance(stored_at, str):
                        stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                    else:
                        stored_datetime = stored_at
                    
                    hours_since_update = (current_time - stored_datetime).total_seconds() / 3600
                    
                    if hours_since_update < 24:
                        print(f"📅 Recent data found in database (updated {hours_since_update:.1f} hours ago)")
                        print("✅ Using existing data from database")
                        
                        historical_json = stored_data.get('historical_trends', {})
                        current_json = stored_data.get('current_trends', {})
                        metadata = stored_data.get('metadata', {})
                        
                        print(f"📈 Historical trends: {len(historical_json)} segments")
                        print(f"📊 Current trend: {len(current_json)} segment(s)")
                        
                        return historical_json, current_json, metadata
                    else:
                        print(f"📅 Database data is {hours_since_update:.1f} hours old, performing fresh analysis...")
                else:
                    print("📅 No timestamp found in database, performing fresh analysis...")
            else:
                print("📅 No data found in database for this ticker, performing fresh analysis...")
                
        except Exception as e:
            print(f"⚠️ Warning: Could not check database: {e}")
            print("🆕 Proceeding with fresh analysis...")
    
    print("🆕 Performing fresh analysis...")
    
    # Calculate date range with fallback periods
    end_date = (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Try 1 year first, then fallback to 6 months, then 3 months
    periods_to_try = [365, 182, 90]  # 1 year, 6 months, 3 months
    price_data = None
    start_date = None
    
    for days in periods_to_try:
        test_start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
        print(f"🔄 Trying {days} days period: {test_start} to {end_date}")
        
        test_data = get_price_series(ticker, test_start, end_date)
        if not test_data.empty and len(test_data) >= 10:  # Minimum 10 data points
            price_data = test_data
            start_date = test_start
            print(f"✅ Found data for {days} days period ({len(test_data)} data points)")
            break
        else:
            print(f"⚠️ Insufficient data for {days} days period")
    
    if price_data is None:
        print("❌ No sufficient data available for any period")
        error_metadata = create_metadata(ticker, current_time.isoformat())
        error_metadata["error"] = "No sufficient price data available for analysis"
        error_metadata["analysis_period_days"] = 0
        return {}, {}, error_metadata
    
    print(f"📊 Using analysis period: {start_date} to {end_date}")
    print(f"📈 Data points: {len(price_data)}")
    
    try:
        # Step 1: Get price trend segments with order=5 for more segmentation
        print("1️⃣ Analyzing price trends with enhanced segmentation...")
        time_list = plot_clean_zigzag_segments(ticker, start_date, end_date, order=5)
        
        # Validate trend segments
        if not time_list:
            print("⚠️ No trend segments found with order=5, trying with order=3...")
            time_list = plot_clean_zigzag_segments(ticker, start_date, end_date, order=3)
            
            if not time_list:
                print("⚠️ Still no trend segments found, creating fallback analysis...")
                # Create simple fallback trend from available data
                first_date = price_data.index.min().strftime("%Y-%m-%d")
                last_date = price_data.index.max().strftime("%Y-%m-%d")
                first_price = float(price_data.iloc[0]['Price'])
                last_price = float(price_data.iloc[-1]['Price'])
                
                trend_type = "uptrend1" if last_price > first_price else "downtrend1"
                fallback_metadata = create_metadata(ticker, current_time.isoformat())
                fallback_metadata["warning"] = "No trend segments found - using fallback analysis"
                fallback_metadata["analysis_period_days"] = (datetime.today() - datetime.strptime(start_date, "%Y-%m-%d")).days
                fallback_metadata["zigzag_order"] = 5
                
                current_json = {
                    trend_type: {
                        "time": {"start": first_date, "end": last_date},
                        "summary": {
                            "macro_reason": "Limited trend data available for comprehensive analysis",
                            "micro_reason": f"Price moved from {first_price:.2f} to {last_price:.2f} over available period"
                        },
                        "symbol": "↑1" if last_price > first_price else "↓1"
                    }
                }
                return {}, current_json, fallback_metadata
        
        print(f"✅ Found {len(time_list)} trend segments")
        
        # Step 2: Process trend segments for news fetching
        print("2️⃣ Processing trend segments...")
        process_list = from_price_to_FMP_prepocess(time_list)
        
        # Step 3: Fetch news for each trend segment
        if use_multiprocessing:
            print("3️⃣ Fetching news data with multiprocessing...")
        else:
            print("3️⃣ Fetching news data sequentially...")
        news_result, news_evidence = fetch_news_chunks_from_process_list(process_list, ticker, FMP_API_KEY, use_multiprocessing=use_multiprocessing)
        
        # Step 4: Analyze news with LLM
        if use_multiprocessing:
            print("4️⃣ Analyzing news with DeepSeek using multiprocessing...")
        else:
            print("4️⃣ Analyzing news with DeepSeek sequentially...")
        summary_json = await summarize_news_trends_with_llm(news_result, ticker=ticker, use_multiprocessing=use_multiprocessing)
        
        # Step 5: Get price data and calculate distributions
        print("5️⃣ Calculating price distributions...")
        price_data = get_price_series(ticker, start_date, end_date)
        final_json = get_new_price_distribution(price_data, ticker, summary_json)
        
        # Step 6: Split into historical and current
        print("6️⃣ Splitting historical and current trends...")
        historical_json, current_json = split_historical_and_current(final_json)
        
        # Step 7: Create metadata with actual period information
        print("7️⃣ Creating metadata...")
        update_timestamp = current_time.isoformat()
        metadata = create_metadata(ticker, update_timestamp)
        
        # Update metadata with actual analysis period used
        actual_days = (datetime.today() - datetime.strptime(start_date, "%Y-%m-%d")).days
        metadata["analysis_period_days"] = actual_days
        metadata["actual_start_date"] = start_date
        metadata["actual_end_date"] = end_date
        metadata["data_points_used"] = len(price_data)
        metadata["zigzag_order"] = 5  # Updated from 7 to 5
        
        # Add period information
        if actual_days >= 365:
            metadata["period_type"] = "1_year"
        elif actual_days >= 182:
            metadata["period_type"] = "6_months"
        elif actual_days >= 90:
            metadata["period_type"] = "3_months"
        else:
            metadata["period_type"] = "custom"
            metadata["warning"] = f"Using custom period of {actual_days} days"
        
        print(f"✅ Analysis complete for {ticker}")
        print(f"📈 Historical trends: {len(historical_json)} segments")
        print(f"📊 Current trend: {len(current_json)} segment(s)")
        print(f"📅 Analysis period: {actual_days} days ({metadata['period_type']})")
        print(f"📊 Data points: {len(price_data)}")
        
        return historical_json, current_json, metadata
        
    except Exception as e:
        print(f"❌ Error during analysis: {str(e)}")
        raise

if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Stock Trend Storage Agent')
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol (e.g., AAPL)')
    parser.add_argument('--force-update', action='store_true', help='Force fresh analysis')
    parser.add_argument('--no-multiprocessing', action='store_true', help='Disable multiprocessing')
    
    args = parser.parse_args()
    
    ticker = args.ticker.upper()
    force_update = args.force_update
    use_multiprocessing = not args.no_multiprocessing
    
    try:
        import asyncio
        historical_json, current_json, metadata = asyncio.run(analyze_stock_trends(ticker, force_update, use_multiprocessing))
        
        print("\n" + "="*60)
        print("📋 ANALYSIS SUMMARY")
        print("="*60)
        print(f"Ticker: {metadata['ticker']}")
        print(f"Last Update: {metadata['last_update']}")
        print(f"Update Day: {metadata['update_day_of_week']['day_name']} ({metadata['update_day_of_week']['day_short']})")
        print(f"Historical Trends: {len(historical_json)}")
        print(f"Current Trends: {len(current_json)}")
        print("="*60)
        
        # Call DB function to store the data
        try:
            from Stock_Trend_DB_Agent import DatabaseStorage
            print("\n📊 Storing in database...")
            
            # Database configuration - you can easily switch between MongoDB and Redis
            DB_TYPE = "redis"  # Changed to use Redis instead of MongoDB
            DB_COLLECTION = "Stock_Trend_INFOS"
            
            if DB_TYPE == "mongodb":
                # MongoDB configuration
                DB_URI = "mongodb+srv://kinkikinsey:KinkiL1234567890!@cluster0.g0ss93l.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
                DB_NAME = "Finpresso_AI"
                storage = DatabaseStorage(
                    db_type=DB_TYPE,
                    uri=DB_URI,
                    database_name=DB_NAME
                )
            elif DB_TYPE == "redis":
                # Redis configuration
                REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
                REDIS_PORT = 16376
                REDIS_USERNAME = "default"
                REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
                storage = DatabaseStorage(
                    db_type=DB_TYPE,
                    host=REDIS_HOST,
                    port=REDIS_PORT,
                    username=REDIS_USERNAME,
                    password=REDIS_PASSWORD
                )
            
            success = storage.store_stock_trend_data(
                ticker=ticker,
                current_json=current_json,
                historical_json=historical_json,
                metadata=metadata,
                collection_name=DB_COLLECTION
            )
            
            if success:
                print(f"✅ Successfully stored in {DB_TYPE.upper()} database!")
            else:
                print(f"❌ Failed to store in {DB_TYPE.upper()} database!")
            
            storage.close()
            
        except Exception as e:
            print(f"⚠️ Warning: Could not store in database: {e}")
        
    except Exception as e:
        print(f"❌ Analysis failed: {str(e)}")
        sys.exit(1)
