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
    """
    
    def __init__(self, shared_clients=None, host: str = None, port: int = None, username: str = "default", password: str = None, decode_responses: bool = True):
        """
        Initialize Redis connection.
        
        Args:
            host (str): Redis host
            port (int): Redis port
            username (str): Redis username
            password (str): Redis password
            decode_responses (bool): Whether to decode responses
        """
        if shared_clients:
            # Use shared Redis connection
            self.client = shared_clients.get_stock_trend_redis()
            logging.info("✅ Using shared revenue segmentation Redis connection")
        else:
            # Use individual Redis connection
            self.host = host
            self.port = port
            self.username = username
            self.password = password
            self.decode_responses = decode_responses
            self.client = None
            self._connect()
    
    def _connect(self):
        """Establish connection to Redis."""
        if hasattr(self, 'client') and self.client is not None:
            return  # Already connected via shared clients
            
        # Check if we have valid connection parameters
        if self.host is None or self.port is None:
            logging.error("❌ Cannot connect to Redis: host or port is None")
            raise ValueError("Redis host and port must be provided when not using shared clients")
            
        try:
            logging.info(f"Attempting to connect to Redis...")
            logging.info(f"Host: {self.host}")
            logging.info(f"Port: {self.port}")
            logging.info(f"Username: {self.username}")
            
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                decode_responses=self.decode_responses,
                username=self.username,
                password=self.password,
            )
            
            # Test the connection
            logging.info("Testing connection with ping command...")
            self.client.ping()
            logging.info("✓ Ping successful - Redis server is reachable")
            logging.info("✓ Successfully connected to Redis")
            
        except redis.ConnectionError as e:
            logging.error("❌ REDIS CONNECTION ERROR:")
            logging.error(f"   - Cannot connect to Redis server")
            logging.error(f"   - Check if Redis server is running")
            logging.error(f"   - Check host, port, and credentials")
            logging.error(f"   - Error details: {e}")
            raise
        except Exception as e:
            logging.error("❌ UNEXPECTED REDIS CONNECTION ERROR:")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            raise
    
    async def store_revenue_segmentation_data(self, ticker: str, revenue_segmentation: Dict, upcoming_earnings: Dict, raw_source_data: Dict, collection_name: str = "revenue_segmentation") -> bool:
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
            document = {
                'ticker': ticker.upper(),
                'revenue_segmentation': revenue_segmentation,
                'metadata': {  # ✅ Clean metadata structure
                    'last_update': datetime.utcnow().isoformat(),
                    'next_earnings_date': upcoming_earnings.get('next_earnings_date'),
                    'earnings_source': upcoming_earnings.get('earnings_source', 'Unknown'),
                    'analysis_type': 'revenue_segmentation_analyzer',
                    'segment_count': len(revenue_segmentation.get('business_segments', []))
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
                
                # Store in Redis
                await self.client.set(redis_key, document_str)
                
                # Verify storage
                stored_data = await self.client.get(redis_key)
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
            
            # Retrieve data from Redis
            stored_data = await self.client.get(redis_key)
            
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
    
    def close(self):
        """Close Redis connection."""
        if self.client:
            try:
                # For aioredis connections, we don't need to close them manually
                # as they're managed by the shared client pool
                logging.info("🔌 Redis connection closed")
            except Exception as e:
                logging.warning(f"⚠️ Error closing Redis connection: {e}")


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
            document = {
                'ticker': ticker.upper(),
                'revenue_segmentation': revenue_segmentation,
                'metadata': {  # ✅ Clean metadata structure
                    'last_update': datetime.utcnow().isoformat(),
                    'next_earnings_date': upcoming_earnings.get('next_earnings_date'),
                    'earnings_source': upcoming_earnings.get('earnings_source', 'Unknown'),
                    'analysis_type': 'revenue_segmentation_analyzer',
                    'segment_count': len(revenue_segmentation.get('business_segments', []))
                }
            }
            
            # Store in Redis with consistent key format
            key = f"{collection_name}:{ticker.upper()}_revenue_segmentation"
            success = await self.storage.store_revenue_segmentation_data(ticker, revenue_segmentation, upcoming_earnings, {}, collection_name)
            
            if success:
                logging.info(f"✅ Successfully stored revenue segmentation data for {ticker}")
                return True
            else:
                logging.error(f"❌ Failed to store revenue segmentation data for {ticker}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error storing revenue segmentation data for {ticker}: {e}")
            return False
    
    async def get_revenue_segmentation_data(self, ticker: str, collection_name: str = "revenue_segmentation") -> Optional[Dict]:
        """Get revenue segmentation data."""
        return await self.storage.get_revenue_segmentation_data(ticker, collection_name)
    
    def list_revenue_segmentation_tickers(self, collection_name: str = "revenue_segmentation") -> List[str]:
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
            
            # Store the fresh data in database
            success = await self.store_revenue_segmentation_data(
                ticker=ticker,
                revenue_segmentation=result['revenue_segmentation'],
                upcoming_earnings=result.get('metadata', {}),
                raw_source_data={},
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
    
    async def get_or_download_revenue_segmentation(self, ticker: str, collection_name: str = "Revenue_Segmentation_INFOS") -> Optional[Dict]:
        """
        Get revenue segmentation data from database, download if not exists or earnings date has passed.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection
            
        Returns:
            Optional[Dict]: Revenue segmentation data or None if failed
        """
        try:
            logging.info(f"🔍 Getting revenue segmentation data for ticker: {ticker}")
            
            # Check if data exists in database
            existing_data = await self.get_revenue_segmentation_data(ticker, collection_name)
            
            if existing_data:
                # ✅ Data exists - check metadata for earnings date (same as stock trend pattern)
                metadata = existing_data.get('metadata', {})
                next_earnings_date = metadata.get('next_earnings_date')
                
                if next_earnings_date:
                    try:
                        # Check if earnings date has passed
                        current_date = datetime.now().date()
                        earnings_date = datetime.strptime(next_earnings_date, '%Y-%m-%d').date()
                        
                        if current_date >= earnings_date:
                            # 🔄 Earnings date passed - need fresh data
                            logging.info(f"🔄 Earnings date {next_earnings_date} has passed for {ticker}, downloading fresh data")
                            success = await self.download_and_store_ticker(ticker, collection_name)
                            
                            if success:
                                return await self.get_revenue_segmentation_data(ticker, collection_name)
                            else:
                                logging.error(f"❌ Failed to download fresh data for {ticker} after earnings date passed")
                                return existing_data  # Return old data if fresh download fails
                        else:
                            # ✅ Data is fresh (earnings date hasn't passed) - use existing data
                            logging.info(f"✅ Data is fresh for {ticker}, earnings date {next_earnings_date} hasn't passed yet")
                            return existing_data
                            
                    except (ValueError, TypeError) as e:
                        logging.warning(f"⚠️ Could not parse earnings date '{next_earnings_date}' for {ticker}: {e}")
                        logging.info(f"✅ Using existing data for {ticker} (earnings date parsing failed)")
                        return existing_data
                else:
                    # No earnings date in metadata - need fresh data with complete metadata
                    logging.info(f"🔄 No earnings date found in metadata for {ticker}, downloading fresh data to get complete metadata")
                    success = await self.download_and_store_ticker(ticker, collection_name)
                    
                    if success:
                        return await self.get_revenue_segmentation_data(ticker, collection_name)
                    else:
                        logging.error(f"❌ Failed to download fresh data for {ticker} to get complete metadata")
                        return existing_data  # Return old data if fresh download fails
            
            # 📥 No data exists - download fresh data
            logging.info(f"📭 No existing data found for {ticker}, downloading...")
            success = await self.download_and_store_ticker(ticker, collection_name)
            
            if success:
                # Retrieve the newly stored data
                return await self.get_revenue_segmentation_data(ticker, collection_name)
            else:
                logging.error(f"❌ Failed to download revenue segmentation data for {ticker}")
                return None
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR IN GET_OR_DOWNLOAD:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return None
    
    def close(self):
        """Close database connection."""
        if hasattr(self, 'storage'):
            self.storage.close()
    
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


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('revenue_segmentation_db_agent.log')
        ]
    )


def main():
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
            storage.close()
            logging.info("🔚 Database connection closed")


if __name__ == "__main__":
    # Example usage:
    # python Revenue_Segmentation_DB_Agent.py AAPL
    # python Revenue_Segmentation_DB_Agent.py TSLA
    # python Revenue_Segmentation_DB_Agent.py --list-tickers
    # python Revenue_Segmentation_DB_Agent.py AAPL --get-data
    main()
