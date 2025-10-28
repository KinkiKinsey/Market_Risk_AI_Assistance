#!/usr/bin/env python3
"""
Earnings and Future Storage Agent
Handles fetching earnings transcript, next earnings date, and future business development.
Follows the same pattern as other Storage Agents (Stock_Trend_Storage_Agent, Revenue_Segmentation_Storage_Agent).
"""

import sys
import os
from pathlib import Path

# Fix import paths for multiprocessing in Streamlit
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import requests
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from tavily import TavilyClient
from LLM_Call_Agent import LLMCallAgent

# Configure logging (minimal output)
logging.basicConfig(
    level=logging.WARNING,  # Changed to WARNING to reduce console output
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # Console only, no log files
    ]
)

class EarningsAndFutureStorageAgent:
    """
    Earnings and Future Storage Agent for processing stock ticker data.
    Follows the same pattern as Revenue_Segmentation_Storage_Agent.
    """
    
    def __init__(self, fmp_api_key: str = None, tavily_api_key: str = None, llm_provider: str = "deepseek"):
        """
        Initialize the Earnings and Future Storage Agent.
        
        Args:
            fmp_api_key (str): Financial Modeling Prep API key
            tavily_api_key (str): Tavily API key
            llm_provider (str): LLM provider to use ("openai" or "deepseek")
        """
        # Use shared clients for LLM operations
        try:
            from shared_clients import shared_clients
            self.llm_agent = shared_clients.get_llm_agent()
            logging.info("✅ Using shared LLM client")
        except ImportError:
            # Fallback to direct LLM agent if shared clients not available
            self.llm_agent = LLMCallAgent(default_provider=llm_provider)
            logging.info(f"⚠️ Using direct LLM client ({llm_provider})")
        
        # API keys - use provided or fallback to defaults
        # Import centralized config
        import sys
        import os
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from config import FMP_API_KEY, TAVILY_API_KEY as DEFAULT_TAVILY_KEY
        
        # Use provided API keys or require from config
        self.fmp_api_key = fmp_api_key if fmp_api_key else FMP_API_KEY
        self.tavily_api_key = tavily_api_key if tavily_api_key else DEFAULT_TAVILY_KEY
        if not self.fmp_api_key:
            raise ValueError("FMP_API_KEY is required in config.env")
        if not self.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is required in config.env")
        
        # Initialize Tavily client
        self.tavily_client = TavilyClient(self.tavily_api_key)
        
        logging.info(f"🤖 Earnings and Future Storage Agent initialized with {llm_provider}")
        logging.info(f"   - FMP API Key: {'***' + self.fmp_api_key[-4:] if self.fmp_api_key else 'Not provided'}")
        logging.info(f"   - Tavily API Key: {'***' + self.tavily_api_key[-4:] if self.tavily_api_key else 'Not provided'}")
    
    def get_company_name(self, ticker: str) -> str:
        """
        Get company full name from ticker using COT (Chain of Thought) approach.
        
        Priority:
        1. Try FMP API (fast, accurate, free)
        2. Fallback to Tavily if FMP fails
        3. Return ticker as last resort
        
        Args:
            ticker (str): Stock ticker symbol (e.g., 'AAPL', 'TSLA')
            
        Returns:
            str: Company full name (e.g., 'Apple Inc.', 'Tesla Inc.')
        """
        ticker_upper = ticker.upper()
        logging.info(f"🔍 COT Step 1: Getting company name for {ticker_upper}...")
        
        # Method 1: Try FMP API first (fast, accurate)
        try:
            from config import FMP_API_V3_URL
            url = f"{FMP_API_V3_URL}/profile/{ticker_upper}"
            params = {'apikey': self.fmp_api_key}
            
            logging.info(f"   📡 Trying FMP API...")
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    company_name = data[0].get('companyName', '')
                    if company_name:
                        logging.info(f"   ✅ FMP API success: {company_name}")
                        return company_name
            
            logging.warning(f"   ⚠️ FMP API returned no data")
        except Exception as e:
            logging.warning(f"   ⚠️ FMP API failed: {e}")
        
        # Method 2: Fallback to Tavily search
        try:
            logging.info(f"   🔍 Fallback to Tavily search...")
            query = f"what is the company name for stock ticker {ticker_upper}, return only the company name"
            
            response = self.tavily_client.search(
                query=query,
                include_answer="advanced",
                search_depth="advanced"
            )
            
            if response and 'answer' in response:
                company_name = response['answer'].strip()
                
                # Clean up response
                if '\n' in company_name:
                    company_name = company_name.split('\n')[0]
                if '.' in company_name and len(company_name) > 50:
                    # If answer is too long, take first sentence
                    company_name = company_name.split('.')[0] + '.'
                
                logging.info(f"   ✅ Tavily success: {company_name}")
                return company_name
            
            logging.warning(f"   ⚠️ Tavily returned no answer")
        except Exception as e:
            logging.warning(f"   ⚠️ Tavily search failed: {e}")
        
        # Method 3: Last resort - return ticker
        logging.warning(f"   ⚠️ All methods failed, using ticker: {ticker_upper}")
        return ticker_upper
    
    def get_latest_earnings_transcript(self, ticker: str) -> Dict:
        """
        Get the most recent earnings transcript for a ticker using FMP API.
        
        Args:
            ticker (str): Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            dict: Latest earnings transcript data or error message
        """
        try:
            # First, get the most recent transcript dates
            from config import FMP_STABLE_URL
            dates_url = f"{FMP_STABLE_URL}/earning-call-transcript-dates"
            dates_params = {
                'symbol': ticker.upper(),
                'apikey': self.fmp_api_key
            }
            
            logging.info(f"🔍 Fetching transcript dates for {ticker}...")
            dates_response = requests.get(dates_url, params=dates_params, timeout=30)
            
            if dates_response.status_code != 200:
                logging.error(f"❌ Failed to get transcript dates: {dates_response.status_code}")
                return {'error': f'Failed to get transcript dates: {dates_response.status_code}'}
            
            dates_data = dates_response.json()
            if not dates_data or len(dates_data) == 0:
                logging.warning(f"⚠️ No transcript dates found for {ticker}")
                return {'error': 'No transcript dates available'}
            
            # Get the most recent transcript date
            latest_date = dates_data[0]
            year = latest_date.get('fiscalYear')
            quarter = latest_date.get('quarter')
            
            if not year or not quarter:
                logging.error(f"❌ Invalid date data for {ticker}: {latest_date}")
                return {'error': 'Invalid date data'}
            
            logging.info(f"📅 Latest transcript: {ticker} Q{quarter} {year}")
            
            # Now get the actual transcript
            transcript_url = f"{FMP_STABLE_URL}/earning-call-transcript"
            transcript_params = {
                'symbol': ticker.upper(),
                'year': year,
                'quarter': quarter,
                'apikey': self.fmp_api_key
            }
            
            logging.info(f"📄 Fetching transcript for {ticker} Q{quarter} {year}...")
            transcript_response = requests.get(transcript_url, params=transcript_params, timeout=30)
            
            if transcript_response.status_code == 200:
                transcript_data = transcript_response.json()
                if transcript_data and len(transcript_data) > 0:
                    transcript = transcript_data[0]
                    logging.info(f"✅ Found earnings transcript for {ticker}")
                    logging.info(f"📅 Date: {transcript.get('date', 'Unknown')}")
                    logging.info(f"📊 Period: {transcript.get('period', 'Unknown')}")
                    logging.info(f"📈 Year: {transcript.get('year', 'Unknown')}")
                    logging.info(f"📝 Content length: {len(transcript.get('content', ''))} characters")
                    return transcript
                else:
                    logging.warning(f"⚠️ No transcript content found for {ticker}")
                    return {'error': 'No transcript content available'}
            else:
                logging.error(f"❌ Failed to get transcript: {transcript_response.status_code}")
                return {'error': f'Failed to get transcript: {transcript_response.status_code}'}
                
        except requests.exceptions.Timeout:
            logging.error(f"❌ Request timeout for {ticker}")
            return {'error': 'Request timeout'}
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Request error: {e}")
            return {'error': f'Request error: {str(e)}'}
        except Exception as e:
            logging.error(f"❌ Unexpected error: {e}")
            return {'error': f'Unexpected error: {str(e)}'}
    
    def get_next_earnings_date(self, ticker: str) -> Dict:
        """
        Get the next upcoming earnings date for a ticker using FMP API.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Next earnings date or error message
        """
        try:
            # Calculate date range (next 365 days)
            today = datetime.now()
            future_date = today + timedelta(days=365)
            
            url = f"{FMP_STABLE_URL}/earnings-calendar"
            params = {
                'from': today.strftime('%Y-%m-%d'),
                'to': future_date.strftime('%Y-%m-%d'),
                'apikey': self.fmp_api_key
            }
            
            logging.info(f"📅 Fetching earnings calendar for {ticker}...")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    # Find the ticker in the results
                    for earnings in data:
                        if earnings.get('symbol', '').upper() == ticker.upper():
                            logging.info(f"✅ Found next earnings date for {ticker}")
                            logging.info(f"📅 Date: {earnings.get('date', 'Unknown')}")
                            logging.info(f"📊 EPS Estimate: {earnings.get('epsEstimated', 'N/A')}")
                            return earnings
                    
                    logging.warning(f"⚠️ No earnings date found for {ticker} in next 365 days")
                    return {'error': 'No upcoming earnings found'}
                else:
                    logging.warning(f"⚠️ No earnings calendar data available")
                    return {'error': 'No earnings calendar data'}
            else:
                logging.error(f"❌ Failed to get earnings calendar: {response.status_code}")
                return {'error': f'Failed to get earnings calendar: {response.status_code}'}
                
        except Exception as e:
            logging.error(f"❌ Error getting next earnings date: {e}")
            return {'error': f'Error: {str(e)}'}
    
    def get_earnings_info_tavily_fallback(self, ticker: str) -> Dict:
        """
        Use Tavily search to get earnings data when FMP API fails.
        Focus on earnings metrics and business plans, not transcripts.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Earnings data from Tavily search
        """
        try:
            logging.info(f"🔍 Using Tavily search for {ticker} earnings data...")
            
            # Search 1: Key earnings metrics and financial results (NO transcripts)
            query1 = f"stock {ticker} current earning season summary revenue EPS profit margin financial metrics"
            logging.info(f"📊 Search 1: Key earnings metrics for {ticker}...")
            
            response1 = self.tavily_client.search(
                query=query1,
                include_answer="advanced",
                topic="finance",
                search_depth="advanced",
                max_results=5
            )
            
            # Search 2: Future business plans and outlook (NO transcripts)
            query2 = f"{ticker} future business plan outlook guidance current quarter strategy growth plans"
            logging.info(f"🚀 Search 2: Future business plans for {ticker}...")
            
            response2 = self.tavily_client.search(
                query=query2,
                include_answer="advanced",
                topic="finance",
                search_depth="advanced",
                max_results=5
            )
            
            # Extract content from both searches
            earnings_metrics = []
            business_plans = []
            
            # Process Search 1 results (earnings metrics)
            if 'results' in response1:
                for result in response1['results']:
                    if 'content' in result and result['content']:
                        # Filter out transcript content
                        content = result['content']
                        if 'transcript' not in content.lower() and 'call' not in content.lower():
                            earnings_metrics.append(content)
            
            # Process Search 2 results (business plans)
            if 'results' in response2:
                for result in response2['results']:
                    if 'content' in result and result['content']:
                        # Filter out transcript content
                        content = result['content']
                        if 'transcript' not in content.lower() and 'call' not in content.lower():
                            business_plans.append(content)
            
            # Combine results
            combined_content = "\n\n".join(earnings_metrics + business_plans)
            
            if combined_content:
                logging.info(f"✅ Successfully retrieved earnings data from Tavily for {ticker}")
                logging.info(f"📊 Content length: {len(combined_content)} characters")
                return {
                    'content': combined_content,
                    'source': 'Tavily_Search',
                    'searches_performed': 2,
                    'earnings_metrics_count': len(earnings_metrics),
                    'business_plans_count': len(business_plans)
                }
            else:
                logging.warning(f"⚠️ No relevant earnings data found via Tavily for {ticker}")
                return {'error': 'No relevant earnings data found via Tavily'}
                
        except Exception as e:
            logging.error(f"❌ Error in Tavily fallback for {ticker}: {e}")
            return {'error': f'Tavily fallback error: {str(e)}'}
    
    def get_upcoming_earnings_tavily_fallback(self, ticker: str) -> Dict:
        """
        Use Tavily search to find upcoming earnings date when FMP API fails.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Upcoming earnings date from Tavily search
        """
        try:
            logging.info(f"🔍 Using Tavily search for {ticker} upcoming earnings...")
            
            # Search for upcoming earnings date
            query = f"{ticker} future business plan outlook guidance current quarter strategy growth plans"
            logging.info(f"📅 Search: Upcoming earnings for {ticker}...")
            
            response = self.tavily_client.search(
                query=query,
                include_answer="advanced",
                topic="finance",
                search_depth="advanced",
                max_results=3
            )
            
            # Extract date information from results
            if 'results' in response:
                for result in response['results']:
                    if 'content' in result and result['content']:
                        content = result['content']
                        # Look for date patterns in the content
                        if any(keyword in content.lower() for keyword in ['earnings', 'quarter', 'fiscal', 'report']):
                            logging.info(f"✅ Found earnings-related content for {ticker}")
                            return {
                                'content': content,
                                'source': 'Tavily_Search',
                                'date': None,  # Would need more sophisticated date extraction
                                'type': 'upcoming_earnings'
                            }
            
            logging.warning(f"⚠️ No upcoming earnings info found via Tavily for {ticker}")
            return {'error': 'No upcoming earnings info found via Tavily'}
            
        except Exception as e:
            logging.error(f"❌ Error in Tavily upcoming earnings fallback for {ticker}: {e}")
            return {'error': f'Tavily upcoming earnings fallback error: {str(e)}'}
    
    def get_future_business_development(self, ticker: str) -> Dict:
        """
        Use Tavily search to get future business development and strategy planning.
        Using COT (Chain of Thought): First get company name, then search with full name.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            dict: Future business development content
        """
        try:
            logging.info(f"🚀 Getting future business development for {ticker}...")
            
            # COT Step 1: Get company full name first
            company_name = self.get_company_name(ticker)
            logging.info(f"📋 COT Step 2: Using company name '{company_name}' for searches...")
            
            # Search 1: Use company name instead of ticker
            query1 = f"what is {company_name}, recent business plan / strategy to overcome its difficulties/maintain its advantage or success"
            logging.info(f"🔍 Search 1: {query1}")
            
            response1 = self.tavily_client.search(
                query=query1,
                include_answer="advanced",
                topic="finance",
                search_depth="advanced",
                max_results=5
            )
            
            # Search 2: Growth and future plans with company name
            query2 = f"{company_name} company strategy growth plans expansion initiatives future outlook business transformation"
            logging.info(f"🔍 Search 2: {query2}")
            
            response2 = self.tavily_client.search(
                query=query2,
                include_answer="advanced",
                topic="finance",
                search_depth="advanced",
                max_results=5
            )
            
            # Extract content from both searches
            strategy_content = []
            growth_content = []
            
            # Process Search 1 results (strategy to overcome difficulties)
            if 'results' in response1:
                for result in response1['results']:
                    if 'content' in result and result['content']:
                        content = result['content']
                        if 'transcript' not in content.lower() and 'call' not in content.lower():
                            strategy_content.append(content)
            
            # Process Search 2 results (growth and expansion)
            if 'results' in response2:
                for result in response2['results']:
                    if 'content' in result and result['content']:
                        content = result['content']
                        if 'transcript' not in content.lower() and 'call' not in content.lower():
                            growth_content.append(content)
            
            # Combine content
            combined_strategy = " | ".join(strategy_content)
            combined_growth = " | ".join(growth_content)
            
            # Get answers
            strategy_answer = response1.get('answer', '')
            growth_answer = response2.get('answer', '')
            
            # Create structured result
            combined_content = f"BUSINESS STRATEGY & DIFFICULTIES OVERCOME:\n\n{strategy_answer}\n\nGROWTH PLANS & FUTURE OUTLOOK:\n\n{growth_answer}"
            
            if combined_content:
                logging.info(f"✅ Successfully retrieved future business development for {ticker}")
                logging.info(f"🎯 Strategy content length: {len(combined_strategy)} characters")
                logging.info(f"🚀 Growth content length: {len(combined_growth)} characters")
                return {
                    'content': combined_content,
                    'company_name': company_name,  # NEW: Include company name in output
                    'strategy_content': combined_strategy,
                    'growth_content': combined_growth,
                    'data_source': 'Tavily_Search',
                    'search_queries': [query1, query2]
                }
            else:
                logging.warning(f"⚠️ No future business development found for {ticker}")
                return {'error': 'No future business development found'}
                
        except Exception as e:
            logging.error(f"❌ Error getting future business development for {ticker}: {e}")
            return {'error': f'Future business development error: {str(e)}'}
    
    async def process_ticker(self, ticker: str) -> Dict:
        """
        Process a ticker to generate earnings and future analysis.
        Follows the same pattern as Revenue_Segmentation_Storage_Agent.process_ticker().
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict: Complete analysis output with earnings and future data
        """
        try:
            logging.info(f"🔍 Processing ticker: {ticker}")
            
            # Step 1: Try to get latest earnings transcript
            logging.info(f"📄 Step 1: Getting latest earnings transcript...")
            transcript_info = self.get_latest_earnings_transcript(ticker)
            
            # Step 2: If transcript fails, use Tavily search as fallback
            if 'error' in transcript_info:
                logging.info(f"⚠️ Earnings transcript not available, using Tavily search fallback...")
                transcript_info = self.get_earnings_info_tavily_fallback(ticker)
            
            # Step 3: Get next earnings date from calendar
            logging.info(f"📅 Step 3: Getting next earnings date...")
            next_earnings_info = self.get_next_earnings_date(ticker)
            
            # Step 4: If next earnings fails, try Tavily search for upcoming earnings
            if 'error' in next_earnings_info:
                logging.info(f"⚠️ Next earnings date not available, using Tavily search fallback...")
                next_earnings_info = self.get_upcoming_earnings_tavily_fallback(ticker)
            
            # Step 5: ALWAYS get future business development and strategy planning
            logging.info(f"🚀 Step 5: Getting future business development and strategy planning...")
            future_development = self.get_future_business_development(ticker)
            
            # Extract data
            transcript_content = transcript_info.get('content', '') if 'error' not in transcript_info else ''
            earning_date = next_earnings_info.get('date', None) if 'error' not in next_earnings_info else None
            future_content = future_development.get('content', '') if 'error' not in future_development else ''
            
            # Create output with CORRECT structure (matching other Storage Agents)
            output = {
                "ticker": ticker.upper(),
                "earnings_and_future": {
                    "transcript": transcript_content,
                    "earning_date": earning_date,
                    "future_development": future_content
                },
                "metadata": {
                    "last_update": datetime.now().isoformat(),
                    "data_source": 'FMP_API' if 'error' not in transcript_info else 'Tavily_Search',
                    "transcript_source": 'FMP_API' if 'error' not in transcript_info else 'Tavily_Search',
                    "earning_date_source": 'FMP_API' if 'error' not in next_earnings_info else 'Tavily_Search',
                    "future_development_source": 'Tavily_Search',
                    "analysis_type": "earnings_and_future_analyzer",
                    "transcript_length": len(transcript_content),
                    "future_development_length": len(future_content),
                    "has_earning_date": earning_date is not None
                }
            }
            
            logging.info(f"✅ Successfully processed {ticker}")
            logging.info(f"   - Transcript length: {len(transcript_content)}")
            logging.info(f"   - Earning date: {earning_date}")
            logging.info(f"   - Future development length: {len(future_content)}")
            
            return output
            
        except Exception as e:
            logging.error(f"❌ Error processing {ticker}: {e}")
            return {"error": f"Processing failed for {ticker}: {str(e)}"}


def main():
    """Main function for testing the Earnings and Future Storage Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Earnings and Future Storage Agent')
    parser.add_argument('ticker', help='Stock ticker symbol to process')
    parser.add_argument('--fmp-api-key', help='Financial Modeling Prep API key')
    parser.add_argument('--tavily-api-key', help='Tavily API key')
    parser.add_argument('--llm-provider', choices=['openai', 'deepseek'], default='deepseek', 
                       help='LLM provider to use')
    
    args = parser.parse_args()
    
    # Initialize agent
    agent = EarningsAndFutureStorageAgent(
        fmp_api_key=args.fmp_api_key,
        tavily_api_key=args.tavily_api_key,
        llm_provider=args.llm_provider
    )
    
    # Process ticker
    import asyncio
    result = asyncio.run(agent.process_ticker(args.ticker))
    
    # Print results
    print(f"\n📈 Earnings and Future Results for {args.ticker}:")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    # Example usage:
    # python Earnings_and_Future_Storage_Agent.py AAPL
    # python Earnings_and_Future_Storage_Agent.py TSLA --llm-provider openai
    main()