#!/usr/bin/env python3
"""
Revenue Segmentation Database Storage Script
Handles storing revenue segmentation data to Redis collections.
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
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path
import argparse
# MongoDB imports removed - using Redis only
import traceback
import redis


class RedisRevenueSegmentationStorage:
    """
    A class to handle Redis storage operations for revenue segmentation data.
    Uses centralized database_connection module for connection management.
    """
    
    def __init__(self, shared_clients=None, host: str = None, port: int = None, username: str = "default", password: str = None, decode_responses: bool = True):
        """
        Initialize Redis connection using database_connection module.
        
        Args:
            host (str): Redis host (deprecated - use shared_clients or config.py)
            port (int): Redis port (deprecated - use shared_clients or config.py)
            username (str): Redis username (deprecated - use shared_clients or config.py)
            password (str): Redis password (deprecated - use shared_clients or config.py)
            decode_responses (bool): Whether to decode responses
        """
        # Import centralized database connection
        import sys
        import os
        backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        
        from Source_File.database_connection import RedisDatabaseStorage as CentralizedStorage
        
        # Use centralized storage for connection
        if shared_clients:
            self.db_storage = CentralizedStorage(db_type="stock_trend", shared_clients=shared_clients)
            logging.info("✅ Using shared revenue segmentation Redis connection via database_connection")
        else:
            # Fallback to direct connection (but still use database_connection)
            self.db_storage = CentralizedStorage(db_type="stock_trend", shared_clients=None)
            logging.info("✅ Using direct revenue segmentation Redis connection via database_connection")
        
        # Expose client for backward compatibility
        self.client = self.db_storage.redis_client
    
    async def store_revenue_segmentation_data(self, ticker: str, revenue_segmentation: Dict, upcoming_earnings: Dict, raw_source_data: Dict, collection_name: str = "Revenue_Segmentation_INFOS") -> bool:
        """
        Store revenue segmentation data in Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            revenue_segmentation (Dict): Revenue segmentation data
            upcoming_earnings (Dict): Upcoming earnings data
            raw_source_data (Dict): Raw source data
            collection_name (str): Name of the collection/namespace to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Processing revenue segmentation data for ticker: {ticker}")
            logging.info(f"   - Redis namespace: {collection_name}")
            logging.info(f"   - Revenue segments: {len(revenue_segmentation.get('business_segments', []))} segments")
            
            # Validate input data
            if not isinstance(revenue_segmentation, dict):
                logging.error("❌ INVALID REVENUE SEGMENTATION TYPE:")
                logging.error(f"   - Expected dict, got {type(revenue_segmentation).__name__}")
                return False
            
            if not isinstance(upcoming_earnings, dict):
                logging.error("❌ INVALID UPCOMING EARNINGS TYPE:")
                logging.error(f"   - Expected dict, got {type(upcoming_earnings).__name__}")
                return False
            
            if not isinstance(raw_source_data, dict):
                logging.error("❌ INVALID RAW SOURCE DATA TYPE:")
                logging.error(f"   - Expected dict, got {type(raw_source_data).__name__}")
                return False
            
            # Prepare clean document (matching Storage Agent output)
            # ✅ FIXED: Now includes cost_supply_segmentation
            document = {
                'ticker': ticker.upper(),
                'stored_at': datetime.utcnow().isoformat(),  # ✅ Add stored_at for cache freshness
                'revenue_segmentation': revenue_segmentation,
                'cost_supply_segmentation': raw_source_data.get('cost_supply_segmentation', {}),  # ✅ NEW: Store cost/supplier data
                'metadata': {  # ✅ Clean metadata structure
                    'last_update': datetime.utcnow().isoformat(),
                    'next_earnings_date': upcoming_earnings.get('next_earnings_date'),
                    'earnings_source': upcoming_earnings.get('earnings_source', 'Unknown'),
                    'analysis_type': 'revenue_and_cost_supply_segmentation_analyzer',  # ✅ UPDATED
                    'segment_count': len(revenue_segmentation.get('business_segments', [])),
                    'cost_segment_count': len(raw_source_data.get('cost_supply_segmentation', {}).get('cost_segments', [])),  # ✅ NEW
                    'supplier_segment_count': len(raw_source_data.get('cost_supply_segmentation', {}).get('supplier_segments', []))  # ✅ NEW
                }
            }
            
            # Check document size
            document_str = json.dumps(document, default=str)
            document_size = len(document_str)
            logging.info(f"   - Document size: {document_size} characters")
            
            # Redis has a 512MB limit per key, but we'll use a more conservative limit
            if document_size > 50 * 1024 * 1024:  # 50MB
                logging.error("❌ DOCUMENT TOO LARGE:")
                logging.error(f"   - Document size: {document_size} characters")
                logging.error(f"   - Redis recommended limit: 50MB")
                logging.error(f"   - Consider splitting the data")
                return False
            
            try:
                # Create Redis key
                redis_key = f"{collection_name}:{ticker.upper()}_revenue_segmentation"
                logging.info(f"   - Attempting to store in Redis key: {redis_key}")
                
                # Store in Redis - handle both sync and async
                is_async = hasattr(self.client, '__class__') and 'aioredis' in str(type(self.client))
                if is_async:
                    await self.client.set(redis_key, document_str)
                    stored_data = await self.client.get(redis_key)
                else:
                    self.client.set(redis_key, document_str)
                    stored_data = self.client.get(redis_key)
                if stored_data:
                    logging.info(f"✅ Successfully stored revenue segmentation data for {ticker}")
                    logging.info(f"   - Redis key: {redis_key}")
                    logging.info(f"   - Data size: {len(stored_data)} characters")
                    return True
                else:
                    logging.error(f"❌ Failed to store data for {ticker} - data not found after storage")
                    return False
                    
            except redis.RedisError as e:
                logging.error(f"❌ REDIS STORAGE ERROR for {ticker}:")
                logging.error(f"   - Error type: {type(e).__name__}")
                logging.error(f"   - Error details: {e}")
                return False
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR STORING REVENUE SEGMENTATION DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    async def get_revenue_segmentation_data(self, ticker: str, collection_name: str = "Revenue_Segmentation_INFOS") -> Optional[Dict]:
        """
        Retrieve revenue segmentation data from Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection/namespace
            
        Returns:
            Optional[Dict]: Revenue segmentation data or None if not found
        """
        try:
            logging.info(f"📈 Retrieving revenue segmentation data for ticker: {ticker}")
            logging.info(f"   - Redis namespace: {collection_name}")
            
            # Create Redis key
            redis_key = f"{collection_name}:{ticker.upper()}_revenue_segmentation"
            logging.info(f"   - Redis key: {redis_key}")
            
            # Retrieve data from Redis - handle both sync and async
            is_async = hasattr(self.client, '__class__') and 'aioredis' in str(type(self.client))
            if is_async:
                stored_data = await self.client.get(redis_key)
            else:
                stored_data = self.client.get(redis_key)
            
            if stored_data:
                # Parse JSON data
                document = json.loads(stored_data)
                logging.info(f"✅ Successfully retrieved revenue segmentation data for {ticker}")
                logging.info(f"   - Revenue segments: {len(document.get('revenue_segmentation', {}).get('business_segments', []))} segments")
                logging.info(f"   - Stored at: {document.get('stored_at', 'Unknown')}")
                return document
            else:
                logging.info(f"📭 No revenue segmentation data found for {ticker}")
                return None
                
        except json.JSONDecodeError as e:
            logging.error(f"❌ JSON DECODE ERROR for {ticker}:")
            logging.error(f"   - Error details: {e}")
            return None
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR RETRIEVING REVENUE SEGMENTATION DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return None
    
    def list_revenue_segmentation_tickers(self, collection_name: str = "Revenue_Segmentation_INFOS") -> List[str]:
        """
        List all tickers with revenue segmentation data.
        
        Args:
            collection_name (str): Name of the collection/namespace
            
        Returns:
            List[str]: List of ticker symbols
        """
        try:
            logging.info(f"📋 Listing revenue segmentation tickers")
            logging.info(f"   - Redis namespace: {collection_name}")
            
            # Get all keys matching the pattern
            pattern = f"{collection_name}:*_revenue_segmentation"
            keys = self.client.keys(pattern)
            
            # Extract ticker symbols from keys
            tickers = []
            for key in keys:
                # Extract ticker from key (format: collection_name:TICKER_revenue_segmentation)
                ticker = key.split(':')[1].replace('_revenue_segmentation', '')
                tickers.append(ticker)
            
            logging.info(f"✅ Found {len(tickers)} tickers with revenue segmentation data")
            return sorted(tickers)
            
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR LISTING TICKERS:")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return []
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            try:
                # For aioredis connections, we don't need to close them manually
                # as they're managed by the shared client pool
                logging.info("🔌 Redis connection closed")
            except Exception as e:
                logging.warning(f"⚠️ Error closing Redis connection: {e}")
    
    async def store_document(self, key: str, document: Dict) -> bool:
        """
        Store a complete document directly to Redis.
        
        Args:
            key (str): Redis key
            document (Dict): Complete document to store
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Storing document to Redis key: {key}")
            
            # Store document as JSON
            json_data = json.dumps(document, default=str)
            # Handle both sync and async Redis clients
            is_async = hasattr(self.client, '__class__') and 'aioredis' in str(type(self.client))
            if is_async:
                await self.client.set(key, json_data)
            else:
                self.client.set(key, json_data)
            
            logging.info(f"✅ Successfully stored document for key: {key}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error storing document for key {key}: {e}")
            return False


class RevenueSegmentationDatabaseStorage:
    """
    Main database storage class for revenue segmentation data.
    """
    
    def __init__(self, db_type: str = "redis", shared_clients=None, **kwargs):
        """
        Initialize database storage.
        
        Args:
            db_type (str): Database type (currently only "redis" supported)
            shared_clients: Shared clients instance for Redis connections
            **kwargs: Database-specific parameters
        """
        self.db_type = db_type.lower()
        
        if self.db_type == "redis":
            if shared_clients:
                # Use shared Redis connection
                self.storage = RedisRevenueSegmentationStorage(
                    shared_clients=shared_clients
                )
            else:
                # Default Redis configuration
                host = kwargs.get('host', 'localhost')
                port = kwargs.get('port', 6379)
                username = kwargs.get('username', 'default')
                password = kwargs.get('password', None)
                
                self.storage = RedisRevenueSegmentationStorage(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                )
            logging.info(f"📊 Initialized Redis storage for revenue segmentation")
            
        else:
            raise ValueError(f"Unsupported database type: {db_type}. Use 'redis'")
    
    async def store_revenue_segmentation_data(self, ticker: str, revenue_segmentation: Dict, upcoming_earnings: Dict, raw_source_data: Dict = None, collection_name: str = "Revenue_Segmentation_INFOS") -> bool:
        """
        Store revenue segmentation data in the database.
        
        Args:
            ticker (str): Stock ticker symbol
            revenue_segmentation (Dict): Revenue segmentation analysis
            upcoming_earnings (Dict): Upcoming earnings data (now part of metadata)
            raw_source_data (Dict): Raw source data (optional, not stored)
            collection_name (str): Name of the collection
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create document with CORRECT structure (matching stock trend pattern)
            # ✅ FIXED: Now includes cost_supply_segmentation
            cost_supply_data = raw_source_data.get('cost_supply_segmentation', {}) if raw_source_data else {}
            document = {
                'ticker': ticker.upper(),
                'stored_at': datetime.utcnow().isoformat(),  # ✅ Add stored_at for cache freshness
                'revenue_segmentation': revenue_segmentation,
                'cost_supply_segmentation': cost_supply_data,  # ✅ NEW: Store cost/supplier data
                'metadata': {  # ✅ Clean metadata structure
                    'last_update': datetime.utcnow().isoformat(),
                    'next_earnings_date': upcoming_earnings.get('next_earnings_date'),
                    'earnings_source': upcoming_earnings.get('earnings_source', 'Unknown'),
                    'analysis_type': 'revenue_and_cost_supply_segmentation_analyzer',  # ✅ UPDATED
                    'segment_count': len(revenue_segmentation.get('business_segments', [])),
                    'cost_segment_count': len(cost_supply_data.get('cost_segments', [])),  # ✅ NEW
                    'supplier_segment_count': len(cost_supply_data.get('supplier_segments', []))  # ✅ NEW
                }
            }
            
            # Store in Redis with consistent key format
            key = f"{collection_name}:{ticker.upper()}_revenue_segmentation"
            success = await self.storage.store_document(key, document)
            
            if success:
                logging.info(f"✅ Successfully stored revenue segmentation data for {ticker}")
                return True
            else:
                logging.error(f"❌ Failed to store revenue segmentation data for {ticker}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error storing revenue segmentation data for {ticker}: {e}")
            return False
    
    async def get_revenue_segmentation_data(self, ticker: str, collection_name: str = "Revenue_Segmentation_INFOS") -> Optional[Dict]:
        """Get revenue segmentation data."""
        return await self.storage.get_revenue_segmentation_data(ticker, collection_name)
    
    def list_revenue_segmentation_tickers(self, collection_name: str = "Revenue_Segmentation_INFOS") -> List[str]:
        """List all tickers with revenue segmentation data."""
        return self.storage.list_revenue_segmentation_tickers(collection_name)
    
    async def download_and_store_ticker(self, ticker: str, collection_name: str = "Revenue_Segmentation_INFOS") -> bool:
        """
        Download and store ticker revenue segmentation data.
        Uses Revenue_Segmentation_Storage_Agent to generate fresh data and stores in database.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Downloading and storing revenue segmentation data for ticker: {ticker}")
            logging.info(f"   - Collection: {collection_name}")
            
            # Import and call Revenue_Segmentation_Storage_Agent to generate fresh data
            from Revenue_Segmentation_Storage_Agent import RevenueSegmentationStorageAgent
            
            logging.info(f"🔄 Calling Revenue_Segmentation_Storage_Agent to analyze {ticker}...")
            
            # Initialize storage agent
            storage_agent = RevenueSegmentationStorageAgent()
            
            # Call the storage agent to generate fresh data
            result = await storage_agent.process_ticker(ticker)
            
            if not result or 'error' in result:
                logging.error(f"❌ Revenue_Segmentation_Storage_Agent failed for {ticker}")
                logging.error(f"   - Result: {result}")
                return False
            
            logging.info(f"✅ Successfully generated revenue segmentation data for {ticker}")
            logging.info(f"   - Revenue segments: {len(result.get('revenue_segmentation', {}).get('business_segments', []))} segments")
            logging.info(f"   - Cost segments: {len(result.get('cost_supply_segmentation', {}).get('cost_segments', []))} segments")  # ✅ NEW
            logging.info(f"   - Supplier segments: {len(result.get('cost_supply_segmentation', {}).get('supplier_segments', []))} segments")  # ✅ NEW
            
            # Store the fresh data in database
            # ✅ FIXED: Pass full result as raw_source_data so cost_supply_segmentation is included
            success = await self.store_revenue_segmentation_data(
                ticker=ticker,
                revenue_segmentation=result['revenue_segmentation'],
                upcoming_earnings=result.get('metadata', {}),
                raw_source_data=result,  # ✅ FIXED: Pass full result instead of empty dict
                collection_name=collection_name
            )
            
            if success:
                logging.info(f"✅ Successfully downloaded and stored {ticker} revenue segmentation data")
            else:
                logging.error(f"❌ Failed to store {ticker} revenue segmentation data in database")
            
            return success
            
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR DOWNLOADING REVENUE SEGMENTATION DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    async def update_if_stale_with_lock(self, ticker: str, collection_name: str = "Revenue_Segmentation_INFOS", force_update: bool = False) -> str:
        """
        Update revenue segmentation data with locking to prevent duplicate expensive API calls.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Collection name
            force_update (bool): Force update regardless of staleness
            
        Returns:
            str: "data_fresh", "updated", "waited_for_update", or "error"
        """
        import time
        import asyncio
        
        try:
            # Check if data exists and is fresh
            existing_data = await self.get_revenue_segmentation_data(ticker, collection_name)
            
            if existing_data and not force_update:
                # PRIORITY 1: Check earnings date (primary update trigger)
                metadata = existing_data.get('metadata', {})
                next_earnings_date = metadata.get('next_earnings_date')
                
                if next_earnings_date:
                    try:
                        current_date = datetime.now().date()
                        earnings_date = datetime.strptime(next_earnings_date, '%Y-%m-%d').date()
                        
                        if current_date < earnings_date:
                            # ✅ Earnings date hasn't passed - data is fresh
                            logging.info(f"✅ Data for {ticker} is fresh (earnings date {next_earnings_date} hasn't passed)")
                            return "data_fresh"
                    except Exception as e:
                        logging.warning(f"⚠️ Could not parse earnings date '{next_earnings_date}': {e}")
                
                # PRIORITY 2: Check stored_at timestamp (24-hour fallback)
                stored_at = existing_data.get('stored_at')
                if stored_at:
                    try:
                        stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                        hours_since_update = (datetime.now() - stored_datetime).total_seconds() / 3600
                        
                        if hours_since_update < 24:  # 24-hour threshold
                            logging.info(f"✅ Data for {ticker} is fresh ({hours_since_update:.1f} hours old)")
                            return "data_fresh"
                    except Exception as e:
                        logging.warning(f"⚠️ Could not parse stored_at timestamp: {e}")
            
            # Data is stale or force update requested - acquire lock
            lock_key = f"update_lock:revenue_segmentation:{ticker.upper()}"
            
            # Try to acquire update lock (5 minute timeout)
            # Handle both sync and async Redis clients
            is_async = hasattr(self.storage.client, '__class__') and 'aioredis' in str(type(self.storage.client))
            
            if is_async:
                lock_acquired = await self.storage.client.set(lock_key, "locked", ex=300, nx=True)
            else:
                lock_acquired = self.storage.client.set(lock_key, "locked", ex=300, nx=True)
            
            if lock_acquired:
                try:
                    logging.info(f"🔒 Acquired update lock for {ticker}, starting update...")
                    
                    # Import and call storage agent to generate fresh data
                    from Revenue_Segmentation_Storage_Agent import RevenueSegmentationStorageAgent
                    
                    logging.info(f"🔄 Calling Revenue_Segmentation_Storage_Agent to analyze {ticker}...")
                    
                    # Initialize storage agent
                    storage_agent = RevenueSegmentationStorageAgent()
                    
                    # Call the storage agent to generate fresh data
                    result = await storage_agent.process_ticker(ticker)
                    
                    if result and 'revenue_segmentation' in result:
                        logging.info(f"✅ Successfully generated data for {ticker}")
                        
                        # Store the fresh data
                        # Extract upcoming_earnings from metadata or result
                        upcoming_earnings = result.get('upcoming_earnings', {})
                        if not upcoming_earnings and 'metadata' in result:
                            # If upcoming_earnings not directly in result, construct from metadata
                            upcoming_earnings = {
                                'next_earnings_date': result.get('metadata', {}).get('next_earnings_date'),
                                'earnings_source': result.get('metadata', {}).get('earnings_source', 'Unknown')
                            }
                        
                        success = await self.store_revenue_segmentation_data(
                            ticker=ticker,
                            revenue_segmentation=result.get('revenue_segmentation', {}),
                            upcoming_earnings=upcoming_earnings,
                            raw_source_data=result,
                            collection_name=collection_name
                        )
                        
                        if success:
                            logging.info(f"✅ Successfully updated shared data for {ticker}")
                            return "updated"
                        else:
                            logging.error(f"❌ Failed to store updated data for {ticker}")
                            return "update_failed"
                    else:
                        logging.error(f"❌ Failed to generate data for {ticker}")
                        return "update_failed"
                        
                finally:
                    # Always release the lock
                    if is_async:
                        await self.storage.client.delete(lock_key)
                    else:
                        self.storage.client.delete(lock_key)
                    logging.info(f"🔓 Released update lock for {ticker}")
            else:
                # Another user is already updating, wait for completion
                logging.info(f"⏳ Another user is updating {ticker}, waiting for completion...")
                
                # Wait for lock to be released (max 5 minutes)
                max_wait_time = 300  # 5 minutes
                wait_interval = 2  # Check every 2 seconds
                
                for _ in range(max_wait_time // wait_interval):
                    if is_async:
                        lock_exists = await self.storage.client.exists(lock_key)
                    else:
                        lock_exists = self.storage.client.exists(lock_key)
                    
                    if not lock_exists:
                        logging.info(f"✅ Update completed by another user for {ticker}")
                        return "waited_for_update"
                    
                    await asyncio.sleep(wait_interval)
                
                logging.warning(f"⚠️ Timeout waiting for {ticker} update, proceeding with stale data")
                return "timeout"
                
        except Exception as e:
            logging.error(f"❌ Error in update_if_stale_with_lock for {ticker}: {e}")
            return "error"
    
    async def get_or_download_revenue_segmentation(self, ticker: str, force_update: bool = False, collection_name: str = "Revenue_Segmentation_INFOS") -> Optional[Dict]:
        """
        Get revenue segmentation data from database, using update_if_stale_with_lock for smart updates.
        
        Args:
            ticker (str): Stock ticker symbol
            force_update (bool): Force update regardless of staleness
            collection_name (str): Name of the collection
            
        Returns:
            Optional[Dict]: Revenue segmentation data or None if failed
        """
        try:
            logging.info(f"🔍 Getting revenue segmentation data for ticker: {ticker}")
            
            # Use update_if_stale_with_lock to handle freshness and locking
            update_result = await self.update_if_stale_with_lock(ticker, collection_name, force_update=force_update)
            
            # After update check, retrieve the data
            data = await self.get_revenue_segmentation_data(ticker, collection_name)
            
            if data:
                logging.info(f"✅ Revenue segmentation data retrieved for {ticker} (status: {update_result})")
                return data
            else:
                logging.error(f"❌ Failed to retrieve revenue segmentation data for {ticker}")
                return None
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR IN GET_OR_DOWNLOAD:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return None
    
    async def close(self):
        """Close database connection."""
        if hasattr(self, 'storage'):
            await self.storage.close()
    
    def test_database_connection(self, ticker: str = "COIN") -> bool:
        """
        Test database connectivity and data retrieval for debugging.
        
        Args:
            ticker (str): Ticker to test
            
        Returns:
            bool: True if connection and data retrieval works
        """
        try:
            logging.info(f"🧪 Testing database connection for {ticker}")
            
            # Test 1: Check if we can connect to Redis
            if not self.storage or not self.storage.client:
                logging.error("❌ No Redis client available")
                return False
            
            # Test 2: Test Redis ping
            try:
                self.storage.client.ping()
                logging.info("✅ Redis ping successful")
            except Exception as e:
                logging.error(f"❌ Redis ping failed: {e}")
                return False
            
            # Test 3: Check if data exists
            existing_data = self.get_revenue_segmentation_data(ticker, "Revenue_Segmentation_INFOS")
            if existing_data:
                logging.info(f"✅ Found existing data for {ticker}")
                logging.info(f"   - Revenue segments: {len(existing_data.get('revenue_segmentation', {}).get('business_segments', []))}")
                logging.info(f"   - Last update: {existing_data.get('metadata', {}).get('last_update', 'Unknown')}")
            else:
                logging.info(f"📭 No existing data found for {ticker}")
            
            # Test 4: List available tickers
            available_tickers = self.list_revenue_segmentation_tickers("Revenue_Segmentation_INFOS")
            logging.info(f"📋 Available tickers: {available_tickers}")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Database connection test failed: {e}")
            return False


def setup_logging(level: str = "WARNING"):  # Changed default to WARNING
    """Setup logging configuration (file logging disabled)."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
            # FileHandler removed - no more log files
        ]
    )


async def main():
    """Main function to handle command line arguments and execute revenue segmentation operations."""
    parser = argparse.ArgumentParser(description='Revenue Segmentation DB Agent - Simple ticker download tool')
    
    # Simple ticker input
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., AAPL, TSLA, PLTR)')
    
    # Optional arguments
    parser.add_argument('--list-tickers', action='store_true', help='List all stored revenue segmentation tickers')
    parser.add_argument('--get-data', action='store_true', help='Retrieve stored data for the ticker')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # PREDEFINED DATABASE CONFIGURATION (same as Stock_Trend_DB_Agent)
    DB_TYPE = "redis"  # Using Redis as default
    DB_COLLECTION = "Revenue_Segmentation_INFOS"
    
    # Redis configuration (predefined - same as Stock_Trend_DB_Agent)
    REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
    REDIS_PORT = 16376
    REDIS_USERNAME = "default"
    REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    
    try:
        logging.info(f"🔧 INITIALIZING {DB_TYPE.upper()} STORAGE FOR REVENUE SEGMENTATION")
        logging.info(f"   - Database type: {DB_TYPE}")
        logging.info(f"   - Collection/Namespace: {DB_COLLECTION}")
        logging.info(f"   - Ticker: {args.ticker.upper()}")
        logging.info(f"   - Log level: {args.log_level}")
        
        # Initialize storage with predefined configuration
        storage = RevenueSegmentationDatabaseStorage(
            db_type=DB_TYPE,
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD
        )
        
        # List revenue segmentation tickers
        if args.list_tickers:
            logging.info(f"📋 LISTING REVENUE SEGMENTATION TICKERS")
            try:
                tickers = storage.list_revenue_segmentation_tickers(DB_COLLECTION)
                if tickers:
                    logging.info(f"✅ Found {len(tickers)} tickers")
                    for ticker in tickers:
                        logging.info(f"   - {ticker}")
                else:
                    logging.info("ℹ️ No tickers found in collection")
            except Exception as e:
                logging.error(f"❌ ERROR LISTING TICKERS: {e}")
        
        # Get stored data for the ticker
        elif args.get_data:
            logging.info(f"📈 RETRIEVING REVENUE SEGMENTATION DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            
            data = storage.get_revenue_segmentation_data(args.ticker.upper(), DB_COLLECTION)
            if data:
                logging.info("✅ REVENUE SEGMENTATION DATA RETRIEVED SUCCESSFULLY")
                logging.info(f"   - Revenue segments: {len(data.get('revenue_segmentation', {}).get('business_segments', []))}")
                logging.info(f"   - Metadata: {data.get('metadata', {})}")
                logging.info(f"   - Last updated: {data.get('stored_at', 'Unknown')}")
            else:
                logging.warning(f"⚠️ No data found for ticker: {args.ticker.upper()}")
        
        # Download and store ticker data (DEFAULT ACTION)
        else:
            logging.info(f"📥 CHECKING AND UPDATING REVENUE SEGMENTATION DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            logging.info(f"   - Collection: {DB_COLLECTION}")
            
            # Use the update logic instead of always downloading
            data = storage.get_or_download_revenue_segmentation(args.ticker.upper(), DB_COLLECTION)
            if data:
                logging.info("✅ REVENUE SEGMENTATION DATA AVAILABLE (fresh or existing)")
                logging.info(f"   - Revenue segments: {len(data.get('revenue_segmentation', {}).get('business_segments', []))}")
                logging.info(f"   - Metadata: {data.get('metadata', {})}")
            else:
                logging.error("❌ FAILED TO GET REVENUE SEGMENTATION DATA")
                sys.exit(1)
        
        # Show collection stats
        logging.info(f"📊 COLLECTION STATISTICS")
        tickers = storage.list_revenue_segmentation_tickers(DB_COLLECTION)
        logging.info(f"   - Total tickers: {len(tickers)}")
        logging.info(f"   - Database type: {DB_TYPE}")
        if tickers:
            logging.info(f"   - Tickers: {', '.join(tickers)}")
        
    except KeyboardInterrupt:
        logging.warning("⚠️  OPERATION CANCELLED BY USER")
    except Exception as e:
        logging.error("❌ CRITICAL ERROR IN MAIN EXECUTION:")
        logging.error(f"   - Error type: {type(e).__name__}")
        logging.error(f"   - Error details: {e}")
        logging.error(f"   - Full traceback:")
        logging.error(traceback.format_exc())
        sys.exit(1)
    finally:
        if 'storage' in locals():
            await storage.close()
            logging.info("🔚 Database connection closed")


if __name__ == "__main__":
    # Example usage:
    # python Revenue_Segmentation_DB_Agent.py AAPL
    # python Revenue_Segmentation_DB_Agent.py TSLA
    # python Revenue_Segmentation_DB_Agent.py --list-tickers
    # python Revenue_Segmentation_DB_Agent.py AAPL --get-data
    import asyncio
    asyncio.run(main())
