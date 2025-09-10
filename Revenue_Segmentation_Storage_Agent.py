#!/usr/bin/env python3
"""
Revenue Segmentation Storage Agent
Converts Jupyter notebook functionality into a standalone service for revenue segmentation analysis.
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
import datetime
import json
import certifi
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import ssl
import re
from tavily import TavilyClient
from LLM_Call_Agent import LLMCallAgent

# API Keys
FMP_API_KEY = '9dfbbfa29d93f4793f246e8fb5ca5e74'
Tavily_API_KEY = "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"

class RevenueSegmentationStorageAgent:
    """
    Revenue Segmentation Storage Agent for processing stock ticker data.
    """
    
    def __init__(self, llm_provider="deepseek"):
        """
        Initialize the Revenue Segmentation Storage Agent.
        
        Args:
            llm_provider (str): LLM provider to use ("openai" or "deepseek")
        """
        # Use shared clients for LLM operations
        try:
            from shared_clients import shared_clients
            self.llm_agent = shared_clients.get_llm_agent()
        except ImportError:
            # Fallback to direct LLM agent if shared clients not available
            self.llm_agent = LLMCallAgent(default_provider=llm_provider)
        self.tavily_client = TavilyClient(Tavily_API_KEY)
        print(f"🤖 Revenue Segmentation Storage Agent initialized with {llm_provider}")
    
    def get_financial_statement(self, url):
        """Get financial statement data from URL."""
        try:
            response = urlopen(Request(url), cafile=certifi.where())
            data = response.read().decode("utf-8")
            return json.loads(data)
        except HTTPError as e:
            print(f"HTTP Error: {e.code} - {e.reason}")
        except URLError as e:
            print(f"URL Error: {e.reason}")
        except Exception as e:
            print(f"Unexpected Error: {e}")
    
    def extract_answer_and_contents(self, full_response: dict) -> dict:
        """Extract answer and contents from Tavily response."""
        answer = full_response.get("answer", "No answer found.")
        contents = [r.get("content") for r in full_response.get("results", []) if r.get("content")]
        return {"answer": answer, "sources_content": contents}
    
    def search_ticker_product_revenue(self, ticker: str) -> dict:
        """Search for ticker product revenue information using Tavily."""
        query = f"What is stock ticker: {ticker}, company product, I want any source mention how it revenue or product, the financial statement, or the earning report annoucement from latest"
        response = self.tavily_client.search(
            query=query,
            topic="general",
            search_depth="advanced",
            max_results=20,
            time_range="year",
            include_answer="advanced",
            chunks_per_source=5
        )
        return self.extract_answer_and_contents(response)
    
    def revenue_segmentation_tool(self, ticker, max_years_back=5):
        """Get revenue segmentation data from FMP API or fallback to search."""
        TICKER = ticker.upper()
        now = datetime.now()
        current_year = now.year
        current_month = now.month

        # Determine current quarter
        if current_month <= 3:
            current_quarter = "Q1"
        elif current_month <= 6:
            current_quarter = "Q2"
        elif current_month <= 9:
            current_quarter = "Q3"
        else:
            current_quarter = "Q4"

        # Build quarter fallback order based on current quarter
        quarter_priority = {
            "Q1": ["Q1"],
            "Q2": ["Q2", "Q1"],
            "Q3": ["Q3", "Q2", "Q1"],
            "Q4": ["Q4", "Q3", "Q2", "Q1"]
        }

        attempts = 0
        print("📡 Getting Raw Financial Data from FMP API...")

        for y in range(current_year, current_year - max_years_back, -1):
            quarters_to_try = quarter_priority[current_quarter] if y == current_year else ["Q4", "Q3", "Q2", "Q1"]

            # Step 1: Try quarters in defined order
            for q in quarters_to_try:
                print(f"🔎 Trying: {y} {q}")
                url = f"https://financialmodelingprep.com/stable/financial-reports-json?symbol={TICKER}&year={y}&period={q}&apikey={FMP_API_KEY}"
                data = self.get_financial_statement(url)
                attempts += 1
                if data and isinstance(data, dict) and data.get("symbol"):
                    print(f"✅ Found data for {TICKER} - {y} {q}")
                    return data
                if attempts == 2:
                    print("⚠️ 2 attempts failed, switching to alternative search...")
                    return self.search_ticker_product_revenue(TICKER)

            # Step 2: Try full fiscal year
            print(f"🔎 Trying: {y} FY")
            url = f"https://financialmodelingprep.com/stable/financial-reports-json?symbol={TICKER}&year={y}&period=FY&apikey={FMP_API_KEY}"
            data = self.get_financial_statement(url)
            attempts += 1
            if data and isinstance(data, dict) and data.get("symbol"):
                print(f"✅ Found data for {TICKER} - {y} FY")
                return data
            if attempts == 2:
                print("⚠️ 2 attempts failed, switching to alternative search...")
                return self.search_ticker_product_revenue(TICKER)

        # Step 3: If all years exhausted
        print(f"❌ No financial report found in FMP for {TICKER} after {max_years_back} years.")
        return self.search_ticker_product_revenue(TICKER)
    
    def analyze_financial_statement(self, financial_text: str) -> dict:
        """Analyze financial statement using LLM."""
        print(f"Calling {self.llm_agent.default_provider} to process the revenue statement")
        
        prompt = f"""
You are a financial analyst AI. Given the following financial statement, extract and structure the company's business performance into JSON format. Focus on:

1. What goods/services generate revenue?
2. What percentage of revenue each contributes?
3. Revenue Amount
4. Who are the target customers or the revenue method?
5. Segment of these customers, in very detail
6. What these goods/services are used for, how to help the customer?

Return JSON in this structure:

{{
  "business_segments": [
    {{
      "name": "Product or Service Name", (in very detail, like the specific product type, model, etc.) (if not read from the text, use 'Not specified')
      "percentage_of_total_revenue": "xx%",(if not read from the text, state "Guess xxx % ", then You will base on the information input guess out a percentage)
      "Revenue Amount": "xxx"(if not read from the text, use state "Guess xxx % ")
      "target_customer_or_revenue_method": "Description of target customers or revenue method, in very detail (if not read from the text, use state "Guess xxx % ",
      "Segment of these customers, in very detail": "xxx"(if not read from the text, state "Guess xxx % ", then You will base on the information input, the density, the significance of the words guess out a percentage)
      "Usage": "xxx"(if not read from the text, use state "Guess xxx % ")
    }}
  ]
}}

Here is the financial statement:
{financial_text}
You need to make very very detailed segment to the financial statement, and make sure the segment is correct.
You are an API call, hence do not return any text outside of the JSON structure, because the user will parse the JSON response.
"""
        
        response = self.llm_agent.call_llm(prompt, system_message="You are an financial report analyst as API agent")

        response_cleaned = re.search(r'\{.*\}', response, re.DOTALL)
        if response_cleaned:
            try:
                return json.loads(response_cleaned.group())
            except json.JSONDecodeError as e:
                print("JSON parse error:", e)
                print("Raw content:", response_cleaned.group())
                return {}
        else:
            print("No JSON object found in response.")
            print("Raw response:", response)
            return {}
    
    def get_upcoming_earnings(self, ticker):
        """Get upcoming earnings information for a ticker."""
        FROM_DATE = datetime.today().strftime("%Y-%m-%d")
        TO_DATE = (datetime.today() + relativedelta(months=4)).strftime("%Y-%m-%d")
        
        earning_url = f"https://financialmodelingprep.com/api/v3/earning_calendar?from={FROM_DATE}&to={TO_DATE}&apikey={FMP_API_KEY}"
        
        def get_jsonparsed_data(url):
            context = ssl.create_default_context(cafile=certifi.where())
            try:
                response = urlopen(Request(url), context=context)
                data = response.read().decode("utf-8")
                return json.loads(data)
            except HTTPError as e:
                print(f"HTTP Error: {e.code} - {e.reason}")
            except URLError as e:
                print(f"URL Error: {e.reason}")
            except Exception as e:
                print(f"Unexpected Error: {e}")
        
        earnings = get_jsonparsed_data(earning_url)
        if earnings:
            for item in earnings:
                if item["symbol"].upper() == ticker.upper():
                    return {
                        "symbol": item["symbol"],
                        "date": item["date"],
                        "eps_estimated": item.get("epsEstimated"),
                        "time": item.get("time"),
                        "revenue_estimated": item.get("revenueEstimated"),
                        "source": "FMP_API"
                    }
        
        # FMP didn't return earnings, use Tavily fallback
        print(f"⚠️ No earnings found in FMP for {ticker}, using Tavily fallback...")
        return self._get_earnings_with_tavily_fallback(ticker)
    
    def _get_earnings_with_tavily_fallback(self, ticker):
        """Fallback method to get earnings dates using Tavily search when FMP fails."""
        try:
            print(f"🔍 Searching Tavily for {ticker} earnings dates...")
            
            # Search for earnings dates using Tavily
            query = f"What is the coming earning report date of {ticker}"
            response = self.tavily_client.search(
                query=query,
                topic="finance",
                search_depth="advanced",
                max_results=10,
                time_range="month",
                include_answer="advanced",
                chunks_per_source=3
            )
            
            # Use LLM to extract and organize the dates
            extracted_dates = self._extract_earnings_dates_with_llm(ticker, response)
            
            if extracted_dates and "earnings_dates" in extracted_dates:
                # Get the next earnings date
                next_earnings = extracted_dates.get("next_earnings", "Not specified")
                
                return {
                    "symbol": ticker.upper(),
                    "date": next_earnings,
                    "eps_estimated": None,
                    "time": None,
                    "revenue_estimated": None,
                    "source": "Tavily_Fallback",
                    "tavily_data": extracted_dates,
                    "message": f"Earnings date found via Tavily search: {next_earnings}"
                }
            else:
                # Even Tavily failed
                return {
                    "symbol": ticker.upper(),
                    "date": None,
                    "eps_estimated": None,
                    "time": None,
                    "revenue_estimated": None,
                    "source": "Tavily_Fallback",
                    "message": f"No upcoming earnings found for {ticker} via any method"
                }
                
        except Exception as e:
            print(f"❌ Tavily fallback failed for {ticker}: {e}")
            return {
                "symbol": ticker.upper(),
                "date": None,
                "eps_estimated": None,
                "time": None,
                "revenue_estimated": None,
                "source": "Tavily_Fallback_Error",
                "message": f"Error in Tavily fallback for {ticker}: {str(e)}"
            }
    
    def _extract_earnings_dates_with_llm(self, ticker, tavily_response):
        """Use LLM to extract earnings dates from Tavily response."""
        try:
            prompt = f"""
You are a financial data analyst. Extract all the earnings report dates from this Tavily search response.

Return ONLY a JSON object with this structure:
{{
    "ticker": "{ticker}",
    "earnings_dates": [
        {{
            "source": "source_name",
            "date": "YYYY-MM-DD",
            "time": "amc/pmc/not_specified",
            "notes": "any additional info"
        }}
    ],
    "next_earnings": "YYYY-MM-DD",
    "summary": "brief summary of findings"
}}

Here's the Tavily response:
{json.dumps(tavily_response, indent=2)}

Extract ALL dates mentioned and organize them by source. If multiple sources mention the same date, include all sources.
Return only valid JSON, no other text.
"""
            
            response = self.llm_agent.call_llm(
                prompt, 
                system_message="You are a financial data analyst. Return only valid JSON."
            )
            
            # Try to parse JSON from response
            response_cleaned = re.search(r'\{.*\}', response, re.DOTALL)
            if response_cleaned:
                try:
                    return json.loads(response_cleaned.group())
                except json.JSONDecodeError as e:
                    print(f"JSON parse error in LLM response: {e}")
                    return None
            else:
                print("No JSON object found in LLM response")
                return None
                
        except Exception as e:
            print(f"Error in LLM earnings extraction: {e}")
            return None
    
    async def process_ticker(self, ticker: str) -> dict:
        """
        Process a ticker to generate revenue segmentation analysis and upcoming earnings data.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict: Complete analysis output with revenue segmentation and metadata
        """
        try:
            print(f"🔍 Processing ticker: {ticker}")
            
            # Get raw financial data
            raw_source_data = self.revenue_segmentation_tool(ticker)
            if not raw_source_data:
                return {"error": f"Failed to get financial data for {ticker}"}
            
            # Process with LLM for revenue segmentation
            llm_process_data = self.analyze_financial_statement(raw_source_data)
            if not llm_process_data:
                return {"error": f"Failed to process data with LLM for {ticker}"}
            
            # Get upcoming earnings (for update timing)
            upcoming_earnings = self.get_upcoming_earnings(ticker)
            
            # Create output with CORRECT structure (matching stock trend pattern)
            output = {
                "ticker": ticker.upper(),
                "revenue_segmentation": llm_process_data,
                "metadata": {  # ✅ Clean metadata structure
                    "last_update": datetime.now().isoformat(),
                    "next_earnings_date": upcoming_earnings.get('next_earnings') or upcoming_earnings.get('date'),
                    "earnings_source": upcoming_earnings.get('source', 'Unknown'),
                    "analysis_type": "revenue_segmentation_analyzer",
                    "segment_count": len(llm_process_data.get('business_segments', []))
                }
            }
            
            print(f"✅ Successfully processed {ticker}")
            return output
            
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            return {"error": f"Processing failed for {ticker}: {str(e)}"}


def main():
    """Main function for testing the Revenue Segmentation Storage Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Revenue Segmentation Storage Agent')
    parser.add_argument('ticker', help='Stock ticker symbol to process')
    parser.add_argument('--llm-provider', choices=['openai', 'deepseek'], default='deepseek', 
                       help='LLM provider to use')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = RevenueSegmentationStorageAgent(llm_provider=args.llm_provider)
    
    # Process ticker
    result = agent.process_ticker(args.ticker)
    
    # Print results
    print(f"\n📈 Revenue Segmentation Results for {args.ticker}:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    # Example usage:
    # python Revenue_Segmentation_Storage_Agent.py AAPL
    # python Revenue_Segmentation_Storage_Agent.py TSLA --llm-provider openai
    main()
