#!/usr/bin/env python3
"""
Sector Analyst Read Agent
Reads and analyzes sector data using LLM and database.
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
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import redis
from dataclasses import dataclass
from pathlib import Path
import asyncio
import re

# Import existing agents
import sys
import os
# Add parent directory to path for root imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)
from LLM_Call_Agent import LLMCallAgent
from Sector_Analyst_DB_Agent import SectorAnalystDBAgent

# COMPLETELY SILENT - No logging output
logging.basicConfig(
    level=logging.CRITICAL,  # Only show critical errors
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.NullHandler()  # No output at all
    ]
)

@dataclass
class SectorAnalysisData:
    """Data class for sector analysis information."""
    ticker: str
    asset_relative: str
    answer_collection: Dict[str, str]
    url_collection: Dict[str, List[str]]
    last_update: str
    data_source: str

class SectorAnalystReadAgent:
    """
    Sector Analyst Read Agent - Reads queries and provides sector analysis answers
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None):
        """Initialize Sector Analyst Read Agent"""
        self.sector_analyst_key = "Sector_Analyst_INFOS:Sector_Analyst"
        self.sector_data_key = "Sector_Analyst_INFOS:Sector_Data"
        self.monthly_threshold = 30  # 30 days
        
        # Initialize Sector Analyst DB Agent
        self.sector_db_agent = SectorAnalystDBAgent(
            shared_clients=shared_clients,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_username=redis_username,
            redis_password=redis_password
        )
        
        # Use shared clients for LLM operations (EXACT same pattern as Stock Trend Read Agent)
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
                from LLM_Call_Agent import LLMCallAgent
                self.llm_agent = LLMCallAgent(
                    openai_api_key=openai_api_key,
                    deepseek_api_key=None,
                    default_provider="deepseek",
                    default_model="deepseek-chat"
                )
                logging.info("⚠️ Using direct LLM client (shared clients not available)")
        
        logging.info(f"📊 Will read from: {self.sector_analyst_key}")
        logging.info(f"📈 Data source: {self.sector_data_key}")
        logging.info(f"🔄 Monthly update threshold: {self.monthly_threshold} days")
        logging.info(f"🧠 LLM Integration: DeepSeek (via {'Shared Clients' if hasattr(self, 'llm_agent') and self.llm_agent else 'LLM_Call_Agent'})")
        
        # Check API keys availability (EXACT same pattern as Stock Trend Read Agent)
        if hasattr(self.llm_agent, 'get_provider_status'):
            logging.info(f"   - LLM Provider: {self.llm_agent.get_provider_status()['deepseek']}")
    
    async def process_sector_query(self, ticker: str) -> Dict[str, Any]:
        """
        Process sector analysis query for a ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict[str, Any]: Sector analysis results
        """
        try:
            logging.info(f"🔍 Processing sector query for {ticker}")
            
            # Check if data is fresh (within 30 days)
            is_fresh = await self._check_data_freshness(ticker)
            
            if is_fresh:
                logging.info(f"✅ Data is fresh for {ticker}, proceeding with analysis")
                # Read existing data and provide analysis
                return await self._read_and_analyze_existing_data(ticker)
            else:
                logging.info(f"📋 Data not fresh for {ticker} - directly calling DB Agent")
                logging.info(f"📥 Directly calling DB Agent for {ticker}")
                # Call DB Agent to update data
                return await self.sector_db_agent.update_sector_data(ticker)
                
        except Exception as e:
            logging.error(f"❌ Sector query processing failed for {ticker}: {e}")
            return {
                "ticker": ticker,
                "asset_relative": "",
                "answer_collection": {},
                "url_collection": {},
                "error": str(e),
                "status": "failed"
            }
    
    async def _check_data_freshness(self, ticker: str) -> bool:
        """
        Check if sector data is fresh (within 30 days).
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            bool: True if data is fresh, False otherwise
        """
        try:
            # Get data from Redis
            data = await self.sector_db_agent.get_sector_data(ticker)
            
            if not data:
                logging.info(f"📈 No data found for {ticker}")
                return False
            
            # Check last update time
            last_update_str = data.get('last_update', '')
            if not last_update_str:
                logging.info(f"📈 No last update time for {ticker}")
                return False
            
            try:
                last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                days_since_update = (datetime.now() - last_update.replace(tzinfo=None)).days
                
                logging.info(f"📈 Data freshness check for {ticker}:")
                logging.info(f"   - Last updated: {last_update_str}")
                logging.info(f"   - Days since update: {days_since_update}")
                
                is_fresh = days_since_update < self.monthly_threshold
                logging.info(f"✅ Data is fresh for {days_since_update} more days" if is_fresh else f"❌ Data not fresh for {ticker} - directly calling DB Agent")
                
                return is_fresh
                
            except Exception as e:
                logging.error(f"❌ Error parsing last update time for {ticker}: {e}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error checking data freshness for {ticker}: {e}")
            return False
    
    async def _read_and_analyze_existing_data(self, ticker: str) -> Dict[str, Any]:
        """
        Read existing data and provide LLM analysis.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        try:
            # Get existing data
            data = await self.sector_db_agent.get_sector_data(ticker)
            
            if not data:
                logging.error(f"❌ No data found for {ticker}")
                return {
                    "ticker": ticker,
                    "asset_relative": "",
                    "answer_collection": {},
                    "url_collection": {},
                    "error": "No data found",
                    "status": "failed"
                }
            
            logging.info(f"✅ Found sector data for {ticker}")
            logging.info(f"   - Asset relative: {data.get('asset_relative', 'N/A')}")
            logging.info(f"   - Answer collection keys: {list(data.get('answer_collection', {}).keys())}")
            logging.info(f"   - URL collection keys: {list(data.get('url_collection', {}).keys())}")
            
            # Return the existing data
            return {
                "ticker": ticker,
                "asset_relative": data.get('asset_relative', ''),
                "answer_collection": data.get('answer_collection', {}),
                "url_collection": data.get('url_collection', {}),
                "last_update": data.get('last_update', ''),
                "status": "success"
            }
            
        except Exception as e:
            logging.error(f"❌ Error reading existing data for {ticker}: {e}")
            return {
                "ticker": ticker,
                "asset_relative": "",
                "answer_collection": {},
                "url_collection": {},
                "error": str(e),
                "status": "failed"
            }

# Example usage
async def main():
    """Example usage of the Sector Analyst Read Agent."""
    
    # Initialize the agent
    agent = SectorAnalystReadAgent()
    
    # Test with a ticker
    ticker = "TEST"  # Default test ticker
    result = await agent.process_sector_query(ticker)
    
    print(f"Sector Analysis for {ticker}:")
    print(f"Asset Relative: {result.get('asset_relative', 'N/A')}")
    print(f"Answer Collection: {result.get('answer_collection', {})}")
    print(f"URL Collection: {result.get('url_collection', {})}")

if __name__ == "__main__":
    asyncio.run(main())
