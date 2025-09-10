#!/usr/bin/env python3
"""
Earnings and Future Read Agent
A natural language interface for querying earnings and future development data from Redis database.
"""

import sys
import os
from pathlib import Path

# Fix import paths for multiprocessing in Streamlit
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import argparse
from pathlib import Path
import redis
from Earnings_and_Future_DB_Agent import EarningsAndFutureDatabaseStorage
from LLM_Call_Agent import LLMCallAgent
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('earnings_and_future_analyst.log')
    ]
)

@dataclass
class EarningsData:
    """Data class for earnings data information."""
    ticker: str
    transcript: str
    earning_date: str
    future_development: str
    last_update: str
    data_source: str

class EarningsAndFutureReadAgent:
    """
    Natural language interface for querying earnings and future development data from Redis database.
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, redis_username: str = "default", 
                 redis_password: str = None, collection_name: str = "Earnings_and_Future_INFOS",
                 openai_api_key: str = None):
        """
        Initialize the Earnings and Future Read Agent.
        
        Args:
            redis_host (str): Redis host
            redis_port (int): Redis port
            redis_username (str): Redis username
            redis_password (str): Redis password
            collection_name (str): Redis collection/namespace
            openai_api_key (str): OpenAI API key for LLM queries
        """
        if shared_clients:
            # Use shared Redis connection
            self.redis_client = shared_clients.get_stock_trend_redis()
            self.storage = EarningsAndFutureDatabaseStorage(
                db_type="redis",
                shared_clients=shared_clients
            )
            logging.info("✅ Using shared Redis connection")
        else:
            # Use individual Redis connection
            self.redis_host = redis_host
            self.redis_port = redis_port
            self.redis_username = redis_username
            self.redis_password = redis_password
            self.collection_name = collection_name
            self.openai_api_key = openai_api_key
            
            # Initialize database storage
            self.storage = EarningsAndFutureDatabaseStorage(
                db_type="redis",
                host=redis_host,
                port=redis_port,
                username=redis_username,
                password=redis_password
            )
            
            # Direct Redis connection for Read Agent
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                username=redis_username,
                password=redis_password,
                decode_responses=True
            )
        
        # Use shared clients for LLM operations
        if shared_clients:
            self.llm_agent = shared_clients.get_llm_agent()
            logging.info("✅ Using shared LLM client")
        else:
            try:
                from shared_clients import shared_clients
                self.llm_agent = shared_clients.get_llm_agent()
                logging.info("✅ Using shared LLM client")
            except ImportError:
                # Fallback to direct LLM agent if shared clients not available
                self.llm_agent = LLMCallAgent(
                    openai_api_key=openai_api_key,
                    deepseek_api_key=None,
                    default_provider="deepseek",
                    default_model="deepseek-chat"
                )
                logging.info("⚠️ Using direct LLM client (shared clients not available)")
        
        # Ensure LLM agent is properly initialized
        if not self.llm_agent:
            logging.warning("⚠️ LLM agent not initialized, creating fallback")
            self.llm_agent = LLMCallAgent(
                openai_api_key=openai_api_key,
                deepseek_api_key=None,
                default_provider="deepseek",
                default_model="deepseek-chat"
            )
        
        logging.info("🤖 Earnings and Future Read Agent initialized")
        logging.info(f"   - Redis: {redis_host}:{redis_port}")
        logging.info(f"   - Collection: {collection_name}")
        if self.llm_agent and hasattr(self.llm_agent, 'get_provider_status'):
            logging.info(f"   - LLM Provider: {self.llm_agent.get_provider_status()['deepseek']}")
    
    def get_earnings_data(self, ticker: str) -> Optional[Dict]:
        """
        Retrieve earnings and future development data for a given ticker using direct Redis access.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Optional[Dict]: Earnings data or None if not found
        """
        try:
            logging.info(f"📈 Retrieving earnings data for ticker: {ticker}")
            
            # Direct Redis access using the same logic as DB Agent
            redis_key = f"{self.collection_name}:{ticker.upper()}_earnings_and_future"
            data_str = self.redis_client.get(redis_key)
            
            if data_str:
                data = json.loads(data_str)
                logging.info(f"✅ Found earnings data for {ticker}")
                logging.info(f"   - Transcript length: {len(data.get('earnings_and_future', {}).get('transcript', ''))}")
                logging.info(f"   - Future development length: {len(data.get('earnings_and_future', {}).get('future_development', ''))}")
                logging.info(f"   - Last updated: {data.get('metadata', {}).get('last_update', 'Unknown')}")
                return data
            else:
                logging.warning(f"⚠️ No earnings data found for ticker: {ticker}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error retrieving earnings data for {ticker}: {e}")
            return None
    
    def list_available_tickers(self) -> List[str]:
        """
        List all available stock tickers in the database.
        
        Returns:
            List[str]: List of available ticker symbols
        """
        try:
            logging.info("📋 Listing available tickers...")
            tickers = self.storage.list_all_tickers(self.collection_name)
            
            if tickers:
                logging.info(f"✅ Found {len(tickers)} tickers: {', '.join(tickers)}")
            else:
                logging.info("ℹ️ No tickers found in database")
            
            return tickers
            
        except Exception as e:
            logging.error(f"❌ Error listing tickers: {e}")
            return []
    
    def _parse_earnings_data(self, earnings_data: Dict) -> EarningsData:
        """Parse earnings data into a structured format."""
        earnings_info = earnings_data.get('earnings_and_future', {})
        metadata = earnings_data.get('metadata', {})
        
        return EarningsData(
            ticker=earnings_data.get('ticker', ''),
            transcript=earnings_info.get('transcript', ''),
            earning_date=earnings_info.get('earning_date', ''),
            future_development=earnings_info.get('future_development', ''),
            last_update=metadata.get('last_update', ''),
            data_source=metadata.get('data_source', '')
        )
    
    async def analyze_query_with_llm(self, query: str, earnings_data: Dict) -> str:
        """
        Use LLM Call Agent to analyze the query and provide insights about the earnings data.
        
        Args:
            query (str): Natural language query
            earnings_data (Dict): Earnings and future development data
            
        Returns:
            str: LLM-generated analysis and response
        """
        if not self.llm_agent or not self.llm_agent.get_available_providers():
            return "❌ No LLM providers configured. Cannot provide LLM analysis."
        
        try:
            # Store earnings data for analysis
            self._current_earnings_data = earnings_data
            
            ticker = earnings_data.get('ticker', 'Unknown')
            earnings_info = earnings_data.get('earnings_and_future', {})
            metadata = earnings_data.get('metadata', {})
            
            # Create comprehensive prompt for earnings analysis
            prompt = f"""
Analyze this earnings and future development data to provide a comprehensive response to the user's query.

USER QUERY: "{query}"
TICKER: {ticker}

EARNINGS DATA SUMMARY:
- Transcript Length: {len(earnings_info.get('transcript', ''))} characters
- Future Development Length: {len(earnings_info.get('future_development', ''))} characters
- Earning Date: {earnings_info.get('earning_date', 'Not available')}
- Last Updated: {metadata.get('last_update', 'Unknown')}
- Data Source: {metadata.get('data_source', 'Unknown')}

EARNINGS TRANSCRIPT (First 3000 characters):
{earnings_info.get('transcript', '')[:3000]}...

FUTURE DEVELOPMENT (First 2000 characters):
{earnings_info.get('future_development', '')[:2000]}...

**REQUIRED OUTPUT FORMAT - EARNINGS AND FUTURE ANALYSIS:**

**PART 1: EARNINGS PERFORMANCE ANALYSIS**
Based on the earnings transcript, provide a detailed analysis of:
- Key financial performance metrics (revenue, profit, EPS, margins)
- Management commentary on business performance
- Key operational highlights and challenges
- Comparison to previous periods or expectations

**PART 2: FUTURE DEVELOPMENT STRATEGY**
Based on the future development data, analyze:
- Strategic initiatives and growth plans
- Market expansion opportunities
- Technology and innovation roadmap
- Risk factors and challenges mentioned
- Management guidance and outlook

**PART 3: QUERY-SPECIFIC INSIGHTS**
Directly address the user's query: "{query}"
- Provide specific insights relevant to their question
- Reference specific data points from the earnings information
- Offer actionable analysis based on the available data
- Highlight key takeaways for investment decision-making

**RULES:**
1. Use only the provided earnings data - do not make up information
2. Be specific and reference actual data points when possible
3. Structure your response clearly with the three parts above
4. If certain information is not available in the data, clearly state this
5. Focus on providing valuable insights for investment decision-making
6. Keep the analysis professional and data-driven
7. Use specific numbers and metrics when available

Analyze the earnings and future development data to provide comprehensive insights about {ticker}."""
            
            # Use shared clients semaphore-controlled async LLM call
            try:
                from shared_clients import shared_clients
                response = await shared_clients.call_deepseek(
                    prompt=prompt,
                    system_message="You are a specialized earnings and future development analyst. Provide evidence-based analysis using the provided earnings data.",
                    max_tokens=2000,
                    temperature=0.2
                )
            except Exception as e:
                # Fallback to direct LLM call if shared clients fail
                response = self.llm_agent.call_llm(
                    prompt=prompt,
                    system_message="You are a specialized earnings and future development analyst. Provide evidence-based analysis using the provided earnings data.",
                    max_tokens=2000,
                    temperature=0.2
                )
            
            logging.info(f"✅ LLM analysis completed for {ticker}")
            return response
            
        except Exception as e:
            logging.error(f"❌ Error in LLM analysis: {e}")
            return f"❌ Error analyzing earnings data: {e}"
    
    def check_database_status(self, ticker: str, force_update: bool = False) -> Dict:
        """
        Check database status for a ticker - data availability and freshness.
        
        Args:
            ticker (str): Stock ticker symbol
            force_update (bool): Force update even if recent data exists
            
        Returns:
            Dict: Status information including data availability and freshness
        """
        try:
            logging.info(f"🔍 Checking database status for ticker: {ticker}")
            
            # Get earnings data from database
            earnings_data = self.get_earnings_data(ticker)
            
            if not earnings_data:
                return {
                    "status": "not_found",
                    "message": f"No earnings data found for ticker {ticker}",
                    "recommendation": "run_analysis",
                    "ticker": ticker
                }
            
            # Check data freshness
            stored_at = earnings_data.get('metadata', {}).get('last_update')
            if stored_at:
                if isinstance(stored_at, str):
                    stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                else:
                    stored_datetime = stored_at
                
                current_time = datetime.now()
                hours_since_update = (current_time - stored_datetime).total_seconds() / 3600
                
                if hours_since_update < 24 and not force_update:
                    return {
                        "status": "fresh",
                        "message": f"Earnings data is fresh (updated {hours_since_update:.1f} hours ago)",
                        "hours_since_update": hours_since_update,
                        "recommendation": "use_existing",
                        "ticker": ticker,
                        "earnings_data": earnings_data
                    }
                else:
                    return {
                        "status": "stale",
                        "message": f"Earnings data is {hours_since_update:.1f} hours old",
                        "hours_since_update": hours_since_update,
                        "recommendation": "update_analysis",
                        "ticker": ticker,
                        "earnings_data": earnings_data
                    }
            else:
                return {
                    "status": "unknown_freshness",
                    "message": "Earnings data found but timestamp unknown",
                    "recommendation": "use_existing",
                    "ticker": ticker,
                    "earnings_data": earnings_data
                }
                
        except Exception as e:
            logging.error(f"❌ Error checking database status: {e}")
            return {
                "status": "error",
                "message": f"Error checking database: {e}",
                "recommendation": "run_analysis",
                "ticker": ticker
            }
    
    def run_earnings_analysis_if_needed(self, ticker: str, force_update: bool = False) -> Dict:
        """
        Check if earnings data is fresh and available.
        Only returns success if data is fresh (< 24 hours old).
        
        Args:
            ticker (str): Stock ticker symbol
            force_update (bool): Force update even if recent data exists
            
        Returns:
            Dict: Analysis result and status
        """
        try:
            logging.info(f"🔄 Checking earnings data freshness for ticker: {ticker}")
            
            # Check database status first
            db_status = self.check_database_status(ticker, force_update)
            
            if db_status["status"] == "fresh":
                logging.info(f"✅ Earnings data is fresh for {ticker}")
                return {
                    "status": "success",
                    "message": "Earnings data is fresh",
                    "earnings_data": db_status["earnings_data"],
                    "analysis_performed": False
                }
            
            else:
                logging.info(f"🔄 Earnings data is stale for {ticker}, triggering update with locking...")
                
                # Use the new update locking method
                update_result = self.storage.update_if_stale_with_lock(ticker, self.collection_name, force_update)
                
                if update_result == "data_fresh":
                    logging.info(f"✅ Earnings data became fresh during check for {ticker}")
                    # Get the fresh data
                    fresh_data = self.get_earnings_data(ticker)
                    return {
                        "status": "success",
                        "message": "Earnings data is fresh",
                        "earnings_data": fresh_data,
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                elif update_result == "updated":
                    logging.info(f"✅ Successfully updated earnings data for {ticker}")
                    # Get the updated data
                    updated_data = self.get_earnings_data(ticker)
                    return {
                        "status": "success",
                        "message": "Earnings data updated successfully",
                        "earnings_data": updated_data,
                        "analysis_performed": True,
                        "update_result": update_result
                    }
                elif update_result == "waited_for_update":
                    logging.info(f"✅ Waited for another user to update {ticker}")
                    # Get the data that was updated by another user
                    updated_data = self.get_earnings_data(ticker)
                    return {
                        "status": "success",
                        "message": "Earnings data updated by another user",
                        "earnings_data": updated_data,
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                elif update_result == "timeout":
                    logging.warning(f"⚠️ Timeout waiting for {ticker} update")
                    # Try to get whatever data is available
                    available_data = self.get_earnings_data(ticker)
                    return {
                        "status": "partial_success",
                        "message": "Timeout waiting for update, using available data",
                        "earnings_data": available_data,
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                else:
                    logging.error(f"❌ Update failed for {ticker}: {update_result}")
                    return {
                        "status": "error",
                        "message": f"Update failed: {update_result}",
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                    
        except Exception as e:
            logging.error(f"❌ Error in run_earnings_analysis_if_needed: {e}")
            return {
                "status": "error",
                "message": f"Error: {e}",
                "analysis_performed": False
            }
    
    async def process_natural_query(self, query: str, ticker: str = None, force_update: bool = False) -> str:
        """
        Process a natural language query about earnings data with LLM ticker extraction.
        Uses LLM to extract ticker first, then uses it as constant throughout logic.
        
        Args:
            query (str): Natural language query
            ticker (str): Optional ticker symbol (will be extracted from query if not provided)
            force_update (bool): Force update even if recent data exists
            
        Returns:
            str: Response to the query
        """
        try:
            # STEP 1: Extract ticker using LLM (most important)
            if not ticker:
                logging.info(f"🔍 Using LLM to extract ticker from query: '{query}'")
                query_analysis = self._extract_ticker_and_info_from_query(query)
                ticker = query_analysis.get("ticker")
                
                if not ticker:
                    return "❌ Could not identify a stock ticker in your query. Please specify a ticker symbol."
            
            ticker = ticker.upper()
            logging.info(f"✅ Extracted ticker: {ticker}")
            logging.info(f"🔍 Processing query: '{query}' for ticker: {ticker}")
            
            # STEP 2: Check database status with extracted ticker
            db_status = self.check_database_status(ticker, force_update)
            
            # STEP 3: Use ticker as constant variable throughout all if/else logic
            if db_status["status"] == "fresh":
                logging.info(f"✅ Earnings data is fresh for {ticker}, proceeding with analysis")
                earnings_data = db_status["earnings_data"]
                
                # Use LLM for analysis with fresh data
                try:
                    llm_response = await self.analyze_query_with_llm(query, earnings_data)
                    return f"✅ Using fresh earnings data for {ticker}. " + llm_response
                except Exception as e:
                    logging.warning(f"⚠️ LLM analysis failed: {e}")
                    # Provide dynamic response
                    dynamic_response = self._provide_dynamic_response(query, earnings_data, "all_data", "all")
                    return f"✅ Using fresh earnings data for {ticker}. " + dynamic_response
                    
            else:
                # Data is missing, stale, or unknown freshness - DIRECTLY CALL DB AGENT
                logging.info(f"📋 Earnings data not fresh for {ticker} - directly calling DB Agent")
                return await self._call_db_agent_and_retry(ticker, query)
                
        except Exception as e:
            logging.error(f"❌ Error processing query: {e}")
            return f"❌ Error processing query: {e}"
    
    async def _call_db_agent_and_retry(self, ticker: str, query: str) -> str:
        """
        Directly call DB Agent to download data and then retry the query.
        Uses ticker as constant variable throughout.
        
        Args:
            ticker (str): Stock ticker symbol (constant variable)
            query (str): Original query
            
        Returns:
            str: Response after DB Agent call
        """
        try:
            logging.info(f"📥 Directly calling DB Agent for {ticker}")
            
            # Import and call DB Agent directly
            from Earnings_and_Future_DB_Agent import EarningsAndFutureDatabaseStorage
            
            # Initialize DB Agent with same Redis config
            db_agent = EarningsAndFutureDatabaseStorage(
                db_type="redis",
                host=self.redis_host,
                port=self.redis_port,
                username=self.redis_username,
                password=self.redis_password
            )
            
            # Call DB Agent for {ticker}
            success = await db_agent.get_or_download_earnings_and_future(
                ticker=ticker,
                collection_name=self.collection_name
            )
            
            db_agent.close()
            
            if success:
                logging.info(f"✅ DB Agent successfully downloaded {ticker} earnings data")
                
                # Now retry the query with fresh data for {ticker}
                logging.info(f"🔄 Retrying query with fresh earnings data for {ticker}")
                return await self._process_query_with_fresh_data(query, ticker)
            else:
                logging.error(f"❌ DB Agent failed to download {ticker} earnings data")
                return f"❌ Failed to download earnings data for {ticker}. Please try again later."
                
        except Exception as e:
            logging.error(f"❌ Error calling DB Agent for {ticker}: {e}")
            return f"❌ Error updating earnings data for {ticker}: {e}"
    
    async def _process_query_with_fresh_data(self, query: str, ticker: str) -> str:
        """
        Process query with fresh data after DB Agent download.
        Uses ticker as constant variable throughout.
        
        Args:
            query (str): Original query
            ticker (str): Stock ticker symbol (constant variable)
            
        Returns:
            str: Response with fresh data
        """
        try:
            # Get fresh earnings data from database for {ticker}
            earnings_data = self.get_earnings_data(ticker)
            
            if earnings_data:
                logging.info(f"✅ Processing query with fresh earnings data for {ticker}")
                
                # Use LLM for analysis with fresh data for {ticker}
                try:
                    llm_response = await self.analyze_query_with_llm(query, earnings_data)
                    return f"🆕 Fresh earnings data downloaded for {ticker}. " + llm_response
                except Exception as e:
                    logging.warning(f"⚠️ LLM analysis failed for {ticker}: {e}")
                    # Provide dynamic response for {ticker}
                    dynamic_response = self._provide_dynamic_response(query, earnings_data, "all_data", "all")
                    return f"🆕 Fresh earnings data downloaded for {ticker}. " + dynamic_response
            else:
                return f"❌ Failed to retrieve fresh earnings data for {ticker}"
                
        except Exception as e:
            logging.error(f"❌ Error processing fresh earnings data for {ticker}: {e}")
            return f"❌ Error processing fresh earnings data for {ticker}: {e}"
    
    def _extract_ticker_and_info_from_query(self, query: str) -> Dict:
        """
        Extract ticker symbol and information type from natural language query using LLM.
        
        Args:
            query (str): Natural language query
            
        Returns:
            Dict: {"ticker": str, "info_type": str, "json_path": str}
        """
        logging.info(f"🔍 Extracting ticker and info from query: '{query}'")
        
        # Use LLM_Call_Agent's predefined function
        try:
            result = self.llm_agent.extract_ticker_and_info_from_query(query)
            return result
        except Exception as e:
            logging.warning(f"⚠️ LLM extraction failed: {e}")
            # Fallback to simple ticker extraction
            ticker = self._extract_ticker_with_regex(query)
            return {"ticker": ticker, "info_type": "all_data", "json_path": "all"}
    
    def _extract_ticker_with_regex(self, query: str) -> Optional[str]:
        """Fallback regex method for ticker extraction."""
        import re
        
        # Look for common ticker patterns - prioritize specific patterns first
        ticker_patterns = [
            r'ticker\s+([A-Z]{1,5})',  # "ticker AAPL"
            r'stock\s+([A-Z]{1,5})',   # "stock AAPL"
            r'([A-Z]{1,5})\s+stock',   # "AAPL stock"
            r'for\s+([A-Z]{1,5})',     # "for AAPL"
            r'about\s+([A-Z]{1,5})',   # "about AAPL"
            r'([A-Z]{1,5})\s+earnings', # "AAPL earnings"
            r'([A-Z]{1,5})\s+future',  # "AAPL future"
            r'\b([A-Z]{1,5})\b',       # Standalone tickers (last resort)
        ]
        
        for i, pattern in enumerate(ticker_patterns):
            match = re.search(pattern, query.upper())
            if match:
                ticker = match.group(1)
                logging.info(f"🔍 Regex pattern {i+1} matched: '{ticker}' from '{query.upper()}'")
                
                # Filter out common words that might be mistaken for tickers
                common_words = {'THE', 'AND', 'FOR', 'WITH', 'ABOUT', 'WHAT', 'HOW', 'WHY', 'WHEN', 'WHERE', 'IS', 'ARE', 'WAS', 'WERE', 'BEEN', 'BEING', 'HAVE', 'HAS', 'HAD', 'DO', 'DOES', 'DID', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'CAN', 'MAY', 'MIGHT', 'MUST', 'SHALL', 'ABOUT', 'ABOVE', 'ACROSS', 'AFTER', 'AGAINST', 'ALONG', 'AMONG', 'AROUND', 'BEFORE', 'BEHIND', 'BELOW', 'BENEATH', 'BESIDE', 'BETWEEN', 'BEYOND', 'DURING', 'EXCEPT', 'INSIDE', 'NEAR', 'OFF', 'OVER', 'PAST', 'SINCE', 'THROUGH', 'THROUGHOUT', 'TOWARD', 'UNDER', 'UNDERNEATH', 'UNTIL', 'UP', 'UPON', 'WITHIN', 'WITHOUT', 'EARNINGS', 'FUTURE', 'STOCK', 'STOCKS', 'SHARE', 'SHARES', 'PRICE', 'PRICES', 'MARKET', 'MARKETS', 'TRADING', 'TRADE', 'BUY', 'SELL', 'HOLD', 'RECENT', 'INSIGHT', 'FROM', 'CURRENT'}
                
                if ticker not in common_words:
                    logging.info(f"✅ Valid ticker found via regex: '{ticker}'")
                    return ticker
                else:
                    logging.info(f"❌ Ticker '{ticker}' filtered out as common word")
            else:
                logging.info(f"🔍 Regex pattern {i+1} did not match: '{pattern}'")
        
        logging.info(f"❌ No valid ticker found in query: '{query}'")
        return None
    
    def _provide_dynamic_response(self, query: str, earnings_data: Dict, info_type: str, json_path: str) -> str:
        """
        Provide a dynamic response based on the specific information requested.
        
        Args:
            query (str): User query
            earnings_data (Dict): Earnings and future development data
            info_type (str): Type of information requested
            json_path (str): JSON path to retrieve specific data
            
        Returns:
            str: Focused response based on user's request
        """
        ticker = earnings_data.get('ticker', 'Unknown')
        earnings_info = earnings_data.get('earnings_and_future', {})
        metadata = earnings_data.get('metadata', {})
        
        response = f"📊 **Earnings and Future Analysis for {ticker}**\n"
        response += "=" * 60 + "\n\n"
        
        # Metadata information
        response += f"**📅 Last Updated:** {metadata.get('last_update', 'Unknown')}\n"
        response += f"**📈 Data Source:** {metadata.get('data_source', 'Unknown')}\n"
        response += f"**🔍 Query:** {query}\n\n"
        
        # Earnings Transcript Summary
        transcript = earnings_info.get('transcript', '')
        if transcript:
            response += "📄 **EARNINGS TRANSCRIPT SUMMARY:**\n"
            response += "-" * 40 + "\n"
            response += f"**Length:** {len(transcript)} characters\n"
            response += f"**Preview:** {transcript[:500]}...\n\n"
        
        # Future Development Summary
        future_dev = earnings_info.get('future_development', '')
        if future_dev:
            response += "🚀 **FUTURE DEVELOPMENT SUMMARY:**\n"
            response += "-" * 40 + "\n"
            response += f"**Length:** {len(future_dev)} characters\n"
            response += f"**Preview:** {future_dev[:500]}...\n\n"
        
        # Earning Date Information
        earning_date = earnings_info.get('earning_date', '')
        if earning_date:
            response += f"📅 **NEXT EARNINGS DATE:** {earning_date}\n\n"
        else:
            response += "📅 **NEXT EARNINGS DATE:** Not available\n\n"
        
        # Query information
        response += f"🔍 **Query:** {query}\n"
        response += "💡 *For detailed LLM analysis with function calling, please configure OpenAI API key.*\n"
        
        return response
    
    def close(self):
        """Close the database connection."""
        self.storage.close()
        logging.info("🔚 Earnings and Future Read Agent closed")


def main():
    """Main function to handle command line arguments and execute queries."""
    parser = argparse.ArgumentParser(description='Earnings and Future Read Agent - Natural Language Query Interface')
    
    # Database arguments
    parser.add_argument('--redis-host', default='redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com',
                       help='Redis host')
    parser.add_argument('--redis-port', type=int, default=16376, help='Redis port')
    parser.add_argument('--redis-username', default='default', help='Redis username')
    parser.add_argument('--redis-password', default='rl8242B4UItBhFzgHW5APEqZnkYoaEZv', help='Redis password')
    parser.add_argument('--collection', default='Earnings_and_Future_INFOS', help='Redis collection name')
    
    # Query arguments
    parser.add_argument('--query', help='Natural language query about earnings and future development data')
    parser.add_argument('--ticker', help='Stock ticker symbol')
    parser.add_argument('--list-tickers', action='store_true', help='List all available tickers')
    parser.add_argument('--force-update', action='store_true', help='Force update even if recent data exists')
    
    # OpenAI arguments
    parser.add_argument('--openai-key', help='OpenAI API key for LLM analysis (optional, will auto-import from LLM_Call_Agent if not provided)')
    
    # Interactive mode
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    try:
        # Initialize agent
        agent = EarningsAndFutureReadAgent(
            redis_host=args.redis_host,
            redis_port=args.redis_port,
            redis_username=args.redis_username,
            redis_password=args.redis_password,
            collection_name=args.collection,
            openai_api_key=args.openai_key
        )
        
        # List tickers if requested
        if args.list_tickers:
            tickers = agent.list_available_tickers()
            if tickers:
                print(f"\n📋 Available tickers: {', '.join(tickers)}")
            else:
                print("\nℹ️ No tickers found in database")
            return
        
        # Process single query
        if args.query:
            response = agent.process_natural_query(args.query, args.ticker)
            print(f"\n🤖 Response:\n{response}")
            return
        
        # Interactive mode
        if args.interactive:
            print("\n🤖 Earnings and Future Read Agent - Interactive Mode")
            print("Type 'quit' to exit, 'list' to see available tickers")
            print("=" * 60)
            
            while True:
                try:
                    query = input("\n💬 Enter your query: ").strip()
                    
                    if query.lower() in ['quit', 'exit', 'q']:
                        break
                    elif query.lower() == 'list':
                        tickers = agent.list_available_tickers()
                        if tickers:
                            print(f"📋 Available tickers: {', '.join(tickers)}")
                        else:
                            print("ℹ️ No tickers found in database")
                        continue
                    elif not query:
                        continue
                    
                    response = agent.process_natural_query(query)
                    print(f"\n🤖 Response:\n{response}")
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
        
        # Default: show help
        if not any([args.query, args.list_tickers, args.interactive]):
            print("🤖 Earnings and Future Read Agent")
            print("Use --query to ask a question, --interactive for chat mode, or --list-tickers to see available data")
            print("\nExamples:")
            print("  python Earnings_and_Future_Read_Agent.py --query 'What are AAPL earnings and future plans?'")
            print("  python Earnings_and_Future_Read_Agent.py --interactive")
            print("  python Earnings_and_Future_Read_Agent.py --list-tickers")
    
    except Exception as e:
        logging.error(f"❌ Critical error: {e}")
        sys.exit(1)
    finally:
        if 'agent' in locals():
            agent.close()


if __name__ == "__main__":
    # Example usage
    # python Earnings_and_Future_Read_Agent.py --query "What are AAPL earnings and future plans?"
    # python Earnings_and_Future_Read_Agent.py --interactive
    # python Earnings_and_Future_Read_Agent.py --list-tickers
    # python Earnings_and_Future_Read_Agent.py --query "Analyze AAPL earnings" --ticker AAPL
    
    main()