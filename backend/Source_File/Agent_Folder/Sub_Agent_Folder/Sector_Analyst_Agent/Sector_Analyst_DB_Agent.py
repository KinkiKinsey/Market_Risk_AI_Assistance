#!/usr/bin/env python3
"""
Sector Analyst DB Agent
Manages database operations for sector analysis data.
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
from Sector_Analyst_Storage import SectorAnalystStorage

# COMPLETELY SILENT - No logging output
logging.basicConfig(
    level=logging.CRITICAL,  # Only show critical errors
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.NullHandler()  # No output at all
    ]
)

class SectorAnalystDBAgent:
    """
    Sector Analyst DB Agent - Manages database operations for sector analysis
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None):
        """Initialize Sector Analyst DB Agent"""
        self.shared_clients = shared_clients
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_username = redis_username
        self.redis_password = redis_password
        
        # Initialize Sector Analyst Storage
        self.storage_agent = SectorAnalystStorage(
            shared_clients=shared_clients,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_username=redis_username,
            redis_password=redis_password
        )
        
        logging.info("🤖 Sector Analyst DB Agent initialized")
        logging.info(f"📊 Frontend Redis: {redis_host}:{redis_port}")
        logging.info(f"🗄️ Stock Trend Redis: {redis_host}:{redis_port}")
        logging.info(f"🔑 Database keys: Sector_Analyst_INFOS:Sector_Analyst, Sector_Analyst_INFOS:Sector_Data")
        logging.info(f"✅ Connected to databases!")
    
    async def get_sector_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Get sector analysis data for a ticker from database.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Optional[Dict[str, Any]]: Sector analysis data or None if not found
        """
        try:
            logging.info(f"📈 Retrieving sector data for ticker: {ticker}")
            
            # Use storage agent to get data
            data = await self.storage_agent.get_sector_data(ticker)
            
            if data:
                logging.info(f"✅ Found sector data for {ticker}")
                logging.info(f"   - Asset relative: {data.get('asset_relative', 'N/A')}")
                logging.info(f"   - Last update: {data.get('last_update', 'N/A')}")
                return data
            else:
                logging.info(f"📈 No sector data found for {ticker}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error retrieving sector data for {ticker}: {e}")
            return None
    
    async def update_sector_data(self, ticker: str) -> Dict[str, Any]:
        """
        Update sector analysis data for a ticker by calling storage agent.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict[str, Any]: Updated sector analysis data
        """
        try:
            logging.info(f"📈 Updating sector data for ticker: {ticker}")
            
            # Call storage agent to download and store data
            result = await self.storage_agent.download_and_store_sector_data(ticker)
            
            if result.get("status") == "success":
                logging.info(f"✅ Sector data updated successfully for {ticker}")
                return result
            else:
                logging.error(f"❌ Failed to update sector data for {ticker}")
                return result
                
        except Exception as e:
            logging.error(f"❌ Error updating sector data for {ticker}: {e}")
            return {
                "ticker": ticker,
                "asset_relative": "",
                "answer_collection": {},
                "url_collection": {},
                "error": str(e),
                "status": "failed"
            }
    
    async def store_sector_data(self, ticker: str, asset_relative: str, 
                              answer_collection: Dict[str, str], 
                              url_collection: Dict[str, List[str]]) -> bool:
        """
        Store sector analysis data in database.
        
        Args:
            ticker (str): Stock ticker symbol
            asset_relative (str): Asset/product/service the company is relative to
            answer_collection (Dict[str, str]): Sector trend and competitor answers
            url_collection (Dict[str, List[str]]): URLs for further research
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"💾 Storing sector data for {ticker}")
            
            # Prepare data
            sector_data = {
                "ticker": ticker,
                "asset_relative": asset_relative,
                "answer_collection": answer_collection,
                "url_collection": url_collection,
                "last_update": datetime.now().isoformat(),
                "data_source": "Sector_Analyst_Agent"
            }
            
            # Use storage agent to store data
            success = await self.storage_agent.store_sector_data(ticker, sector_data)
            
            if success:
                logging.info(f"✅ Sector data stored successfully for {ticker}")
                return True
            else:
                logging.error(f"❌ Failed to store sector data for {ticker}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error storing sector data for {ticker}: {e}")
            return False
    
    async def delete_sector_data(self, ticker: str) -> bool:
        """
        Delete sector analysis data for a ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"🗑️ Deleting sector data for {ticker}")
            
            # Use storage agent to delete data
            success = await self.storage_agent.delete_sector_data(ticker)
            
            if success:
                logging.info(f"✅ Sector data deleted successfully for {ticker}")
                return True
            else:
                logging.error(f"❌ Failed to delete sector data for {ticker}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error deleting sector data for {ticker}: {e}")
            return False
    
    async def get_or_download_sector_data(self, ticker: str, force_update: bool = False) -> Optional[Dict[str, Any]]:
        """
        Get sector data from database, download if not exists or data is stale.
        Update logic: 30-day freshness threshold (consistent with Read Agent).
        
        Args:
            ticker (str): Stock ticker symbol
            force_update (bool): Force update regardless of staleness
            
        Returns:
            Optional[Dict[str, Any]]: Sector analysis data or None if failed
        """
        try:
            logging.info(f"🔍 Getting sector data for ticker: {ticker}")
            
            # Check if data exists in database
            existing_data = await self.get_sector_data(ticker)
            
            if existing_data and not force_update:
                # ✅ Data exists - check if it's fresh (within 30 days)
                last_update = existing_data.get('last_update') or existing_data.get('stored_at')
                if last_update:
                    try:
                        if isinstance(last_update, str):
                            last_update_datetime = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        else:
                            last_update_datetime = last_update
                        
                        current_time = datetime.now()
                        current_date = current_time.date()
                        update_date = last_update_datetime.date()
                        
                        days_since_update = (current_date - update_date).days
                        
                        if days_since_update < 30:  # Sector Analyst: 30 days
                            # ✅ Data is fresh (within 30 days) - use existing data
                            logging.info(f"✅ Data is fresh for {ticker} ({days_since_update} days old, threshold: 30 days)")
                            return existing_data
                        else:
                            # 🔄 Data is stale (30+ days old) - need fresh data
                            logging.info(f"🔄 Data is stale for {ticker} ({days_since_update} days old, threshold: 30 days) - updating")
                            result = await self.update_sector_data(ticker)
                            
                            if result.get("status") == "success":
                                return await self.get_sector_data(ticker)
                            else:
                                logging.error(f"❌ Failed to download fresh data for {ticker} after staleness check")
                                return existing_data  # Return old data if fresh download fails
                                
                    except (ValueError, TypeError) as e:
                        logging.warning(f"⚠️ Could not parse update time for {ticker}, returning existing data: {e}")
                        return existing_data
                else:
                    # No timestamp - need fresh data with complete metadata
                    logging.info(f"🔄 No timestamp found for {ticker}, downloading fresh data to get complete metadata")
                    result = await self.update_sector_data(ticker)
                    
                    if result.get("status") == "success":
                        return await self.get_sector_data(ticker)
                    else:
                        logging.error(f"❌ Failed to download fresh data for {ticker} to get complete metadata")
                        return existing_data  # Return old data if fresh download fails
            
            # 📥 No data exists - download fresh data
            logging.info(f"📭 No existing data found for {ticker}, downloading...")
            result = await self.update_sector_data(ticker)
            
            if result.get("status") == "success":
                # Retrieve the newly stored data
                return await self.get_sector_data(ticker)
            else:
                logging.error(f"❌ Failed to download initial data for {ticker}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error in get_or_download_sector_data for {ticker}: {e}")
            return None

# Example usage
async def main():
    """Example usage of the Sector Analyst DB Agent."""
    
    # Initialize the agent
    agent = SectorAnalystDBAgent()
    
    # Test with a ticker
    ticker = "TEST"  # Default test ticker
    
    # Get data
    data = await agent.get_sector_data(ticker)
    print(f"Sector data for {ticker}: {data}")
    
    # Update data
    result = await agent.update_sector_data(ticker)
    print(f"Update result for {ticker}: {result}")

if __name__ == "__main__":
    asyncio.run(main())
