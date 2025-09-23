#!/usr/bin/env python3
"""
Financial Metrics Storage Agent
Downloads financial data and stores it in database.
Input: ticker symbol
Output: financial metrics information
"""

import requests
import json
import LLM_Call_Agent
from datetime import datetime
from LLM_Call_Agent import LLMCallAgent
from tavily import TavilyClient

# API Keys
fmp_api_key = "9dfbbfa29d93f4793f246e8fb5ca5e74"
tavily_api_key = "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"

def Valudation_Analysis_Agent(prompt, financial_metrics):
    """
    Simple LLM function to analyze financial metrics using centralized LLM agent
    
    Args:
        prompt (str): The analysis prompt/question
        financial_metrics (dict): Financial data to analyze
    
    Returns:
        str: LLM analysis result
    """
    try:
        # Initialize centralized LLM agent (will auto-import API keys)
        llm_agent = LLMCallAgent(
            default_provider="deepseek",
            default_model="deepseek-chat"
        )
        
        # Format the financial metrics for the prompt
        metrics_text = json.dumps(financial_metrics, indent=2)
        
        full_prompt = f"""
        You are a financial analyst AI. 
        The below is the user query that ask for informaiton about the valudation of the stock, please read the user query and the financial data, and provide a clear, concise analysis based on the above financial data.
User Query::
{prompt}


Financial Data:
{metrics_text}

Please provide a clear, concise analysis based on the above financial data.
"""
        
        # Call the centralized LLM agent
        response = llm_agent.call_llm(
            prompt=full_prompt,
            system_message="You are a financial analyst AI. Provide clear, insightful analysis of financial data.",
            max_tokens=500,
            temperature=0.3
        )
        
        return response
        
    except Exception as e:
        return f"Error calling LLM: {e}"

def get_latest_quarterly_valuation_metrics(ticker, api_key):
    """
    Fetch only the latest quarterly valuation metrics for a given ticker from FMP API
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        api_key (str): Your FMP API key
    
    Returns:
        dict: Latest quarterly financial metrics with only key valuation parameters
    """
    url = f"https://financialmodelingprep.com/stable/key-metrics?symbol={ticker}&period=quarter&limit=1&apikey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        if not data:
            return None
            
        # Get the latest quarterly record (first one since limit=1)
        latest_record = data[0]
        
        # Define the key valuation parameters to keep
        key_params = {
            # Core valuation multiples
            "evToEBITDA": "EV/EBITDA",
            "evToSales": "EV/Sales", 
            "earningsYield": "EarningsYield",
            "freeCashFlowYield": "FreeCashFlowYield",
            
            # Profitability & efficiency
            "roe": "ReturnOnEquity",
            "roic": "ReturnOnInvestedCapital", 
            "roa": "ReturnOnAssets",
            
            # Balance sheet & risk
            "marketCap": "MarketCap",
            "enterpriseValue": "EnterpriseValue",
            "netDebtToEBITDA": "NetDebtToEBITDA",
            "currentRatio": "CurrentRatio",
            
            # Supporting context
            "workingCapital": "WorkingCapital",
            "incomeQuality": "IncomeQuality",
            "capexToOperatingCashFlow": "CapexToOperatingCashFlow"
        }
        
        # Create filtered record with only key parameters
        filtered_record = {
            "symbol": latest_record.get("symbol"),
            "date": latest_record.get("date"),
            "fiscalYear": latest_record.get("fiscalYear"),
            "period": latest_record.get("period"),
            "reportedCurrency": latest_record.get("reportedCurrency")
        }
        
        # Add only the key valuation metrics
        for api_key_name, display_name in key_params.items():
            if api_key_name in latest_record:
                filtered_record[display_name] = latest_record[api_key_name]
        
        return filtered_record
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None

def get_one_month_year_stock_prices_df(ticker, api_key):
    """
    Fetch one year of unadjusted stock prices and return as a time series DataFrame
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        api_key (str): Your FMP API key
    
    Returns:
        pandas.DataFrame: Time series DataFrame with date index and close price column
    """
    import pandas as pd
    from datetime import datetime, timedelta
    
    # Calculate dates for one year ago to today
    end_date = datetime.now()
    start_date = end_date - timedelta(days=31)
    
    # Format dates as YYYY-MM-DD
    from_date = start_date.strftime("%Y-%m-%d")
    to_date = end_date.strftime("%Y-%m-%d")
    
    url = f"https://financialmodelingprep.com/stable/historical-price-eod/non-split-adjusted?symbol={ticker}&from={from_date}&to={to_date}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Convert date column to datetime and set as index
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        
        # Sort by date (oldest to newest)
        df = df.sort_index()
        
        # Select only the close price column
        df = df[['adjClose']].rename(columns={'adjClose': 'close_price'})
        
        return df
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON response: {e}")
        return None
    except Exception as e:
        print(f"Error processing data: {e}")
        return None

def get_latest_dcf_valuation_with_fallback(ticker, api_key, tavily_api_key):
    """
    Fetch the latest DCF valuation for a given ticker from FMP API.
    If DCF doesn't exist OR is negative, fall back to Tavily search to find top 3 DCF estimates.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        api_key (str): Your FMP API key
        tavily_api_key (str): Your Tavily API key
    
    Returns:
        dict: DCF valuation data with top 3 highest score results
    """
    from tavily import TavilyClient
    
    # First try FMP API
    url = f"https://financialmodelingprep.com/stable/discounted-cash-flow?symbol={ticker}&apikey={api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        if data and len(data) > 0:
            # FMP DCF data exists, check if it's valid (not negative)
            latest_record = data[0]
            dcf_value = latest_record.get('dcf')
            stock_price = latest_record.get('Stock Price')
            
            # Check if DCF value is valid (exists and is positive)
            if dcf_value is not None and dcf_value > 0:
                # Valid positive DCF from FMP, return it
                fmp_dcf_result = {
                    "symbol": ticker,
                    "date": latest_record.get('date', 'Unknown'),
                    "source": 'FMP API',
                    "top_3_dcf_results": [{
                        "dcf_value": dcf_value,
                        "score": 1.0,  # FMP data gets highest score
                        "title": f"FMP API DCF for {ticker}",
                        "url": "FMP API",
                        "content_preview": f"DCF Value: ${dcf_value}, Stock Price: ${stock_price}"
                    }],
                    "total_dcf_results_found": 1,
                    "search_query": "FMP API Direct",
                    "dcf": dcf_value,  # Keep original field for compatibility
                    "Stock Price": stock_price  # Keep original field for compatibility
                }
                
                print(f"✅ FMP DCF data found for {ticker}: ${dcf_value}")
                return fmp_dcf_result
            else:
                # DCF exists but is negative or invalid, fall back to Tavily
                print(f"⚠️ FMP DCF data for {ticker} is invalid (value: {dcf_value}), falling back to Tavily search...")
            
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        print(f"FMP API error: {e}")
    
    # If FMP DCF doesn't exist OR is negative, try Tavily search
    print(f"DCF data not found or invalid in FMP for {ticker}, searching with Tavily...")
    
    try:
        tavily_client = TavilyClient(api_key=tavily_api_key)
        
        # Search for DCF valuation
        search_query = f"{ticker} stock DCF valuation intrinsic value discounted cash flow analysis"
        search_result = tavily_client.search(
            query=search_query,
            search_depth="basic",
            max_results=15  # Get more results to find top 3
        )
        
        # Find all results with DCF values and scores
        dcf_results = []
        
        for result in search_result.get("results", []):
            content = result.get("content", "").lower()
            score = result.get("score", 0)
            
            # Look for DCF-related content
            if "dcf" in content or "discounted cash flow" in content or "intrinsic value" in content:
                # Extract dollar amounts - improved regex to capture larger values
                import re
                
                # Look for DCF-specific patterns first
                dcf_patterns = [
                    r'dcf value.*?\$([\d,]+\.?\d*)',  # "DCF Value is $1,078.6"
                    r'intrinsic value.*?\$([\d,]+\.?\d*)',  # "Intrinsic Value $1,078.6"
                    r'fair value.*?\$([\d,]+\.?\d*)',  # "Fair Value $1,078.6"
                    r'valuation.*?\$([\d,]+\.?\d*)',  # "Valuation $1,078.6"
                ]
                
                dcf_value = None
                for pattern in dcf_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        # Remove commas and convert to float
                        dcf_value = float(match.group(1).replace(',', ''))
                        break
                
                # If no DCF-specific pattern found, look for any large dollar amount
                if not dcf_value:
                    # Look for dollar amounts that are likely DCF values (large numbers)
                    dollar_amounts = re.findall(r'\$([\d,]+\.?\d*)', result.get("content", ""))
                    for amount in dollar_amounts:
                        amount_clean = float(amount.replace(',', ''))
                        # Filter for reasonable DCF values (not too small, not too large)
                        if 50 <= amount_clean <= 2000:  # Adjust range as needed
                            dcf_value = amount_clean
                            break
                
                if dcf_value:
                    dcf_results.append({
                        "dcf_value": dcf_value,
                        "score": score,
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content_preview": result.get("content", "")[:300] + "..."
                    })
        
        # Sort by score (highest first) and get top 3
        dcf_results.sort(key=lambda x: x['score'], reverse=True)
        top_2_results = dcf_results[:2]
        
        # Return top 3 results
        if top_2_results:
            return {
                "symbol": ticker,
                "date": "Search-based estimate",
                "source": "Tavily Search - Top 3 Results",
                "top_3_dcf_results": top_2_results,
                "total_dcf_results_found": len(dcf_results),
                "search_query": search_query
            }
        else:
            return {
                "symbol": ticker,
                "date": "Search-based estimate",
                "source": "Tavily Search",
                "dcf": None,
                "message": "No DCF values found in search results"
            }
        
    except Exception as e:
        print(f"Tavily search error: {e}")
        return None

def get_ticker_sector_info_with_fallback(ticker, fmp_api_key, tavily_api_key):
    """
    Get ticker sector and company description using FMP API with Tavily fallback - NO PARSING
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
        fmp_api_key (str): Your FMP API key
        tavily_api_key (str): Your Tavily API key
    
    Returns:
        dict: Raw data from either FMP or Tavily
    """
    # First try FMP API
    url = f"https://financialmodelingprep.com/stable/search-exchange-variants?symbol={ticker}&apikey={fmp_api_key}"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        
        if data:
            # FMP data found, return it
            ticker_info = data[0]
            result = {
                "ticker": ticker_info.get("symbol"),
                "sector": ticker_info.get("industry", "Unknown"),
                "description": ticker_info.get("companyName", "Unknown"),
                "source": "FMP API"
            }
            print(f"✅ FMP data found for {ticker}")
            return result
            
    except Exception as e:
        print(f"⚠️ FMP API error for {ticker}: {e}")
    
    # If FMP doesn't have data, fall back to Tavily search
    print(f" FMP data not found for {ticker}, searching with Tavily...")
    
    try:
        tavily_client = TavilyClient(api_key=tavily_api_key)
        
        # Search for company information
        search_query = f"{ticker} stock company sector industry business description what does this company do"
        search_result = tavily_client.search(
            query=search_query,
            search_depth="advanced",
            max_results=5
        )
        
        # Just collect all the raw content without parsing
        all_content = ""
        
        print(f"\n🔍 DEBUG: Tavily Search Results for '{ticker}'")
        print("="*80)
        print(f"Search Query: {search_query}")
        print(f"Total Results: {len(search_result.get('results', []))}")
        print("="*80)
        
        # Collect all content from all results
        for i, result in enumerate(search_result.get("results", []), 1):
            title = result.get('title', 'No title')
            url = result.get('url', 'No URL')
            content = result.get('content', '')
            
            print(f"\n📄 RESULT #{i}")
            print(f"Title: {title}")
            print(f"URL: {url}")
            print(f"Content Length: {len(content)} characters")
            
            # Add to all_content
            all_content += f"\n\n--- SOURCE #{i}: {title} ({url}) ---\n{content}"
        
        # Return the raw, unprocessed data
        return {
            "ticker": ticker,
            "sector": "See full description below",  # No parsing, just placeholder
            "description": all_content.strip(),  # ALL the raw content
            "source": "Tavily Search - Raw Output"
        }
        
    except Exception as e:
        print(f"❌ Tavily search error: {e}")
        return {
            "error": f"Both FMP and Tavily failed: {e}",
            "ticker": ticker
        }

def combine_existing_financial_data(ticker, financial_metrics, dcf_data, stock_df, ticker_description_result=None):
    """
    Combine existing financial data sources into one comprehensive JSON structure
    
    Args:
        ticker (str): Stock ticker symbol
        financial_metrics (dict): Valuation metrics data
        dcf_data (dict): DCF valuation data
        stock_df (DataFrame): Stock price data
    
    Returns:
        dict: Combined financial data from all sources
    """
    try:
        # Combine all data into one structure
        combined_data = {
            "ticker": ticker,
            "data_retrieved_at": datetime.now().isoformat(),
            "data_sources": {
                "valuation_metrics": {
                    "source": "FMP API - Key Metrics",
                    "data": financial_metrics
                },
                "dcf_valuation": {
                    "source": dcf_data.get("source", "Unknown") if dcf_data else "Unknown",
                    "data": dcf_data
                },
                "stock_prices": {
                    "source": "FMP API - Stock Prices",
                    "data": stock_df.to_dict('records') if stock_df is not None else None
                },
                "ticker_description": {
                    "source": ticker_description_result.get("source", "Unknown") if ticker_description_result else "Unknown",
                    "data": ticker_description_result
                }
            },
            "summary": {
                "has_valuation_metrics": financial_metrics is not None,
                "has_dcf_data": dcf_data is not None,
                "has_stock_prices": stock_df is not None,
                "has_ticker_description": ticker_description_result is not None,
                "total_data_points": len(stock_df) if stock_df is not None else 0
            }
        }
        
        return combined_data
        
    except Exception as e:
        print(f"❌ Error combining financial data: {e}")
        return None

def restructure_financial_data(combined_data):
    """
    Restructure combined financial data into a cleaner, more organized format
    
    Args:
        combined_data (dict): Combined financial data from combine_existing_financial_data
    
    Returns:
        dict: Restructured data with financial_metrics, dcf, and price sections
    """
    try:
        # Extract the four main data sections
        valuation_metrics = combined_data['data_sources']['valuation_metrics']['data']
        dcf_data = combined_data['data_sources']['dcf_valuation']['data']
        stock_prices = combined_data['data_sources']['stock_prices']['data']
        ticker_description = combined_data['data_sources']['ticker_description']['data']
        
        # Restructure into clean format
        restructured_data = {
            "ticker": combined_data['ticker'],
            "data_retrieved_at": combined_data['data_retrieved_at'],
            
            "financial_metrics": {
                "symbol": valuation_metrics.get('symbol'),
                "date": valuation_metrics.get('date'),
                "fiscal_year": valuation_metrics.get('fiscalYear'),
                "period": valuation_metrics.get('period'),
                "currency": valuation_metrics.get('reportedCurrency'),
                
                # Core valuation multiples
                "ev_to_ebitda": valuation_metrics.get('EV/EBITDA'),
                "ev_to_sales": valuation_metrics.get('EV/Sales'),
                "earnings_yield": valuation_metrics.get('EarningsYield'),
                "free_cash_flow_yield": valuation_metrics.get('FreeCashFlowYield'),
                
                # Profitability & efficiency
                "roe": valuation_metrics.get('ReturnOnEquity'),
                "roic": valuation_metrics.get('ReturnOnInvestedCapital'),
                "roa": valuation_metrics.get('ReturnOnAssets'),
                
                # Balance sheet & risk
                "market_cap": valuation_metrics.get('MarketCap'),
                "enterprise_value": valuation_metrics.get('EnterpriseValue'),
                "net_debt_to_ebitda": valuation_metrics.get('NetDebtToEBITDA'),
                "current_ratio": valuation_metrics.get('CurrentRatio'),
                
                # Supporting context
                "working_capital": valuation_metrics.get('WorkingCapital'),
                "income_quality": valuation_metrics.get('IncomeQuality'),
                "capex_to_operating_cf": valuation_metrics.get('CapexToOperatingCashFlow')
            },
            
            "dcf": {
                "symbol": dcf_data.get('symbol'),
                "source": dcf_data.get('source'),
                "date": dcf_data.get('date'),
                "total_results_found": dcf_data.get('total_dcf_results_found', 0),
                
                # Top DCF results (keep top 3)
                "top_results": dcf_data.get('top_3_dcf_results', []),
                
                # Best DCF estimate (highest score)
                "best_estimate": None,
                "best_score": 0,
                "best_source": None
            },
            
            "price": {
                "symbol": combined_data['ticker'],
                "total_data_points": combined_data['summary']['total_data_points'],
                "latest_price": None,
                "price_history": [],
                "price_summary": {}
            },
            
            "ticker_description": {
                "symbol": ticker_description.get('ticker') if ticker_description else None,
                "sector": ticker_description.get('sector') if ticker_description else "Unknown",
                "description": ticker_description.get('description') if ticker_description else "Unknown",
                "source": ticker_description.get('source') if ticker_description else "Unknown"
            }
        }
        
        # Set best DCF estimate (highest score)
        if restructured_data['dcf']['top_results']:
            best_result = max(restructured_data['dcf']['top_results'], key=lambda x: x['score'])
            restructured_data['dcf']['best_estimate'] = best_result['dcf_value']
            restructured_data['dcf']['best_score'] = best_result['score']
            restructured_data['dcf']['best_source'] = best_result['url']
        
        # Process price data
        if stock_prices:
            # Extract close prices and convert to float
            close_prices = [float(price['close_price']) for price in stock_prices if 'close_price' in price]
            
            if close_prices:
                restructured_data['price']['latest_price'] = close_prices[-1]  # Most recent
                restructured_data['price']['price_history'] = close_prices
                
                # Calculate price summary statistics
                restructured_data['price']['price_summary'] = {
                    "min_price": min(close_prices),
                    "max_price": max(close_prices),
                    "avg_price": sum(close_prices) / len(close_prices),
                    "latest_price": close_prices[-1],
                    "price_change": close_prices[-1] - close_prices[0],
                    "price_change_pct": ((close_prices[-1] - close_prices[0]) / close_prices[0]) * 100 if close_prices[0] != 0 else 0
                }
        
        return restructured_data
        
    except Exception as e:
        print(f"❌ Error restructuring financial data: {e}")
        return None

async def process_financial_metrics(ticker):
    """
    Main function to process financial metrics for a ticker.
    
    Args:
        ticker (str): Stock ticker symbol
    
    Returns:
        dict: Processed financial metrics data with metadata
    """
    try:
        print(f"🚀 Starting financial metrics analysis for {ticker}")
        
        # Get all financial data
        financial_metrics = get_latest_quarterly_valuation_metrics(ticker, fmp_api_key)
        dcf_data = get_latest_dcf_valuation_with_fallback(ticker, fmp_api_key, tavily_api_key)
        stock_df = get_one_month_year_stock_prices_df(ticker, fmp_api_key)
        ticker_description_result = get_ticker_sector_info_with_fallback(ticker, fmp_api_key, tavily_api_key)
        
        # Combine and restructure data
        combined_data = combine_existing_financial_data(ticker, financial_metrics, dcf_data, stock_df, ticker_description_result)
        result_metrics = restructure_financial_data(combined_data)
        
        # Create metadata with latest update time
        metadata = {
            "ticker": ticker,
            "latest_update_time": datetime.now().isoformat(),
            "update_timestamp": int(datetime.now().timestamp()),
            "update_day_of_week": {
                "day_number": datetime.now().weekday(),  # 0=Monday, 1=Tuesday, ..., 6=Sunday
                "day_name": datetime.now().strftime("%A"),  # Monday, Tuesday, Wednesday, etc.
                "day_short": datetime.now().strftime("%a")  # Mon, Tue, Wed, etc.
            },
            "data_sources": {
                "valuation_metrics": "FMP API - Key Metrics",
                "dcf_valuation": dcf_data.get("source", "Unknown") if dcf_data else "Unknown",
                "stock_prices": "FMP API - Stock Prices",
                "ticker_description": ticker_description_result.get("source", "Unknown") if ticker_description_result else "Unknown"
            },
            "analysis_period": "Latest quarterly + 1 month historical",
            "created_by": "financial_metrics_storage_agent",
            "version": "1.0"
        }
        
        # Create final output with both financial metrics and metadata
        final_output = {
            "financial_metrics": result_metrics,
            "metadata": metadata,
            "summary": {
                "ticker": ticker,
                "analysis_completed_at": datetime.now().isoformat(),
                "total_data_points": result_metrics.get("price", {}).get("total_data_points", 0) if result_metrics else 0,
                "has_valuation_data": result_metrics.get("financial_metrics") is not None if result_metrics else False,
                "has_dcf_data": result_metrics.get("dcf", {}).get("best_estimate") is not None if result_metrics else False,
                "has_price_data": result_metrics.get("price", {}).get("latest_price") is not None if result_metrics else False,
                "has_ticker_description": result_metrics.get("ticker_description", {}).get("description") is not None if result_metrics else False
            }
        }
        
        print(f"✅ Financial metrics analysis completed for {ticker}")
        print(f"📅 Latest update time: {metadata['latest_update_time']}")
        print(f"📊 Data summary: {final_output['summary']['total_data_points']} price points, DCF: {'✅' if final_output['summary']['has_dcf_data'] else '❌'}")
        
        return final_output
        
    except Exception as e:
        print(f"❌ Error processing financial metrics for {ticker}: {e}")
        return None

def save_to_json(data, filename=None):
    """
    Save financial data to JSON file.
    
    Args:
        data (dict): Financial data to save
        filename (str): Optional custom filename
    """
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{data.get('ticker', 'unknown')}_financial_metrics_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"✅ Financial data saved to: {filename}")
        return filename
    except Exception as e:
        print(f"❌ Error saving to JSON: {e}")
        return None

def main():
    """Main function to handle command line arguments and execute financial metrics analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Financial Metrics Storage Agent')
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol (e.g., UNH, AAPL, TSLA)')
    parser.add_argument('--save-json', action='store_true', help='Save results to JSON file')
    parser.add_argument('--analyze', action='store_true', help='Run LLM analysis on results')
    
    args = parser.parse_args()
    
    try:
        ticker = args.ticker.upper()
        print(f"🎯 Processing financial metrics for {ticker}")
        
        # Process financial metrics
        import asyncio
        result = asyncio.run(process_financial_metrics(ticker))
        
        if result:
            print(f"✅ Successfully processed {ticker}")
            
            # Extract financial metrics from the new structure
            financial_metrics = result.get('financial_metrics', {})
            metadata = result.get('metadata', {})
            summary = result.get('summary', {})
            
            print(f"📊 Financial Metrics: {'✅' if financial_metrics.get('financial_metrics') else '❌'}")
            print(f" DCF Data: {'✅' if financial_metrics.get('dcf', {}).get('best_estimate') else '❌'}")
            print(f"💰 Price Data: {'✅' if financial_metrics.get('price', {}).get('latest_price') else '❌'}")
            
            # Save to JSON if requested
            if args.save_json:
                filename = save_to_json(result)
                if filename:
                    print(f"💾 Data saved to: {filename}")
            
            # Run LLM analysis if requested
            if args.analyze:
                prompt = "Is current stock price overvalued or undervalued based on the financial metrics?"
                analysis = Valudation_Analysis_Agent(prompt, financial_metrics)
                print(f"\n🤖 LLM Analysis:\n{analysis}")
            
            # Display summary
            print(f"\n📋 Data Summary:")
            print(f"   - Ticker: {ticker}")
            print(f"   - Latest Update: {metadata.get('latest_update_time', 'N/A')}")
            print(f"   - Update Day: {metadata.get('update_day_of_week', {}).get('day_name', 'N/A')}")
            print(f"   - Latest Price: ${financial_metrics.get('price', {}).get('latest_price', 'N/A')}")
            print(f"   - Market Cap: ${financial_metrics.get('financial_metrics', {}).get('market_cap', 'N/A'):,}")
            print(f"   - EV/EBITDA: {financial_metrics.get('financial_metrics', {}).get('ev_to_ebitda', 'N/A')}")
            print(f"   - Best DCF Estimate: ${financial_metrics.get('dcf', {}).get('best_estimate', 'N/A')}")
            
            # Display metadata
            print(f"\n📅 Metadata:")
            print(f"   - Analysis Period: {metadata.get('analysis_period', 'N/A')}")
            print(f"   - Data Sources: {', '.join(metadata.get('data_sources', {}).values())}")
            print(f"   - Created By: {metadata.get('created_by', 'N/A')}")
            print(f"   - Version: {metadata.get('version', 'N/A')}")
            
        else:
            print(f"❌ Failed to process financial metrics for {ticker}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️ Operation cancelled by user")
    except Exception as e:
        print(f"❌ Critical error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Example usage:
    # python Financial_Metrics_Storage_Agent.py --ticker UNH --save-json --analyze
    # python Financial_Metrics_Storage_Agent.py --ticker AAPL --save-json
    
    main()
