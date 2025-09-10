#!/usr/bin/env python3
"""
Earnings and Future Database Storage Script
Handles storing earnings and future data to Redis collections.
Follows the same pattern as other DB Agents (Stock_Trend_DB_Agent, Revenue_Segmentation_DB_Agent).
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
import traceback
import redis

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('earnings_and_future_db_agent.log')
    ]
)

class RedisEarningsAndFutureStorage:
    """
    A class to handle Redis storage operations for earnings and future data.
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
            logging.info("✅ Using shared earnings and future Redis connection")
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
    
    def store_earnings_and_future_data(self, ticker: str, earnings_and_future: Dict, metadata: Dict, collection_name: str = "earnings_and_future") -> bool:
        """
        Store earnings and future data in Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            earnings_and_future (Dict): Earnings and future data
            metadata (Dict): Metadata information
            collection_name (str): Name of the collection/namespace to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Processing earnings and future data for ticker: {ticker}")
            logging.info(f"   - Redis namespace: {collection_name}")
            logging.info(f"   - Transcript length: {len(earnings_and_future.get('transcript', ''))}")
            logging.info(f"   - Future development length: {len(earnings_and_future.get('future_development', ''))}")
            
            # Validate input data
            if not isinstance(earnings_and_future, dict):
                logging.error("❌ INVALID EARNINGS AND FUTURE TYPE:")
                logging.error(f"   - Expected dict, got {type(earnings_and_future).__name__}")
                return False
            
            if not isinstance(metadata, dict):
                logging.error("❌ INVALID METADATA TYPE:")
                logging.error(f"   - Expected dict, got {type(metadata).__name__}")
                return False
            
            # Prepare comprehensive document
            document = {
                'ticker': ticker.upper(),
                'earnings_and_future': earnings_and_future,
                'metadata': metadata,
                'stored_at': datetime.utcnow().isoformat(),
                'data_version': '1.0'
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
                redis_key = f"{collection_name}:{ticker.upper()}_earnings_and_future"
                logging.info(f"   - Attempting to store in Redis key: {redis_key}")
                
                # Store in Redis
                result = self.client.set(redis_key, document_str)
                
                if result:
                    logging.info(f"✓ Successfully stored earnings and future data for {ticker}")
                    logging.info(f"   - Redis key: {redis_key}")
                    logging.info(f"   - Transcript length: {len(earnings_and_future.get('transcript', ''))}")
                    logging.info(f"   - Future development length: {len(earnings_and_future.get('future_development', ''))}")
                    return True
                else:
                    logging.error("❌ REDIS WRITE ERROR:")
                    logging.error(f"   - Failed to write earnings and future data to Redis")
                    return False
                
            except redis.RedisError as e:
                logging.error("❌ REDIS ERROR:")
                logging.error(f"   - Failed to write earnings and future data to Redis")
                logging.error(f"   - Error details: {e}")
                return False
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR STORING EARNINGS AND FUTURE DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    def get_earnings_and_future_data(self, ticker: str, collection_name: str = "Earnings_and_Future_INFOS") -> Optional[Dict]:
        """
        Retrieve earnings and future data from Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection/namespace
            
        Returns:
            Optional[Dict]: Earnings and future data or None if not found
        """
        try:
            logging.info(f"📈 Retrieving earnings and future data for ticker: {ticker}")
            logging.info(f"   - Redis namespace: {collection_name}")
            
            redis_key = f"{collection_name}:{ticker.upper()}_earnings_and_future"
            data_str = self.client.get(redis_key)
            
            if data_str:
                data = json.loads(data_str)
                logging.info(f"✓ Successfully retrieved earnings and future data for {ticker}")
                logging.info(f"   - Transcript length: {len(data.get('earnings_and_future', {}).get('transcript', ''))}")
                logging.info(f"   - Future development length: {len(data.get('earnings_and_future', {}).get('future_development', ''))}")
                return data
            else:
                logging.warning(f"⚠️ No earnings and future data found for ticker: {ticker}")
                return None
                
        except Exception as e:
            logging.error("❌ ERROR RETRIEVING EARNINGS AND FUTURE DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return None
    
    def list_earnings_and_future_tickers(self, collection_name: str = "Earnings_and_Future_INFOS") -> List[str]:
        """
        List all tickers with earnings and future data.
        
        Args:
            collection_name (str): Name of the collection/namespace
            
        Returns:
            List[str]: List of ticker symbols
        """
        try:
            logging.info(f"📋 Listing earnings and future tickers")
            logging.info(f"   - Redis namespace: {collection_name}")
            
            # Get all keys matching the pattern
            pattern = f"{collection_name}:*_earnings_and_future"
            keys = self.client.keys(pattern)
            
            # Extract ticker symbols from keys
            tickers = []
            for key in keys:
                # Extract ticker from key (format: collection_name:TICKER_earnings_and_future)
                ticker = key.split(':')[1].replace('_earnings_and_future', '')
                tickers.append(ticker)
            
            logging.info(f"✅ Found {len(tickers)} tickers with earnings and future data")
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
                # For shared Redis connections, we don't need to close them manually
                # as they're managed by the shared client pool
                logging.info("🔌 Redis connection closed")
            except Exception as e:
                logging.warning(f"⚠️ Error closing Redis connection: {e}")


class EarningsAndFutureDatabaseStorage:
    """
    Main database storage class for earnings and future data.
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
                self.storage = RedisEarningsAndFutureStorage(
                    shared_clients=shared_clients
                )
            else:
                # Default Redis configuration
                host = kwargs.get('host', 'localhost')
                port = kwargs.get('port', 6379)
                username = kwargs.get('username', 'default')
                password = kwargs.get('password', None)
                
                self.storage = RedisEarningsAndFutureStorage(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                )
            logging.info(f"📊 Initialized Redis storage for earnings and future")
            
        else:
            raise ValueError(f"Unsupported database type: {db_type}. Use 'redis'")
    
    def store_earnings_and_future_data(self, ticker: str, earnings_and_future: Dict, metadata: Dict, collection_name: str = "Earnings_and_Future_INFOS") -> bool:
        """
        Store earnings and future data in the database.
        
        Args:
            ticker (str): Stock ticker symbol
            earnings_and_future (Dict): Earnings and future analysis
            metadata (Dict): Metadata information
            collection_name (str): Name of the collection
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            success = self.storage.store_earnings_and_future_data(ticker, earnings_and_future, metadata, collection_name)
            
            if success:
                logging.info(f"✅ Successfully stored earnings and future data for {ticker}")
                return True
            else:
                logging.error(f"❌ Failed to store earnings and future data for {ticker}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error storing earnings and future data for {ticker}: {e}")
            return False
    
    def get_earnings_and_future_data(self, ticker: str, collection_name: str = "Earnings_and_Future_INFOS") -> Optional[Dict]:
        """Get earnings and future data."""
        return self.storage.get_earnings_and_future_data(ticker, collection_name)
    
    def list_earnings_and_future_tickers(self, collection_name: str = "Earnings_and_Future_INFOS") -> List[str]:
        """List all tickers with earnings and future data."""
        return self.storage.list_earnings_and_future_tickers(collection_name)
    
    async def download_and_store_ticker(self, ticker: str, collection_name: str = "Earnings_and_Future_INFOS") -> bool:
        """
        Download and store ticker earnings and future data.
        Uses Earnings_and_Future_Storage_Agent to generate fresh data and stores in database.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Downloading and storing earnings and future data for ticker: {ticker}")
            logging.info(f"   - Collection: {collection_name}")
            
            # Import and call Earnings_and_Future_Storage_Agent to generate fresh data
            from Earnings_and_Future_Storage_Agent import EarningsAndFutureStorageAgent
            
            logging.info(f"🔄 Calling Earnings_and_Future_Storage_Agent to analyze {ticker}...")
            
            # Initialize storage agent
            storage_agent = EarningsAndFutureStorageAgent()
            
            # Call the storage agent to generate fresh data
            result = await storage_agent.process_ticker(ticker)
            
            if not result or 'error' in result:
                logging.error(f"❌ Earnings_and_Future_Storage_Agent failed for {ticker}")
                logging.error(f"   - Result: {result}")
                return False
            
            logging.info(f"✅ Successfully generated earnings and future data for {ticker}")
            logging.info(f"   - Transcript length: {len(result.get('earnings_and_future', {}).get('transcript', ''))}")
            logging.info(f"   - Future development length: {len(result.get('earnings_and_future', {}).get('future_development', ''))}")
            
            # Store the fresh data in database
            success = self.store_earnings_and_future_data(
                ticker=ticker,
                earnings_and_future=result['earnings_and_future'],
                metadata=result.get('metadata', {}),
                collection_name=collection_name
            )
            
            if success:
                logging.info(f"✅ Successfully downloaded and stored {ticker} earnings and future data")
            else:
                logging.error(f"❌ Failed to store {ticker} earnings and future data in database")
            
            return success
            
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR DOWNLOADING EARNINGS AND FUTURE DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    async def get_or_download_earnings_and_future(self, ticker: str, collection_name: str = "Earnings_and_Future_INFOS") -> Optional[Dict]:
        """
        Get earnings and future data from database, download if not exists or data is stale (24 hours).
        Follows the same pattern as other DB Agents with 24-hour update logic.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection
            
        Returns:
            Optional[Dict]: Earnings and future data or None if failed
        """
        try:
            logging.info(f"🔍 Getting earnings and future data for ticker: {ticker}")
            
            # Check if data exists in database
            existing_data = self.get_earnings_and_future_data(ticker, collection_name)
            
            if existing_data:
                # ✅ Data exists - check if it's fresh (within 24 hours)
                stored_at = existing_data.get('stored_at')
                if stored_at:
                    try:
                        if isinstance(stored_at, str):
                            stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                        else:
                            stored_datetime = stored_at
                        
                        hours_since_update = (datetime.now() - stored_datetime).total_seconds() / 3600
                        
                        if hours_since_update < 24:
                            # ✅ Data is fresh (within 24 hours) - use existing data
                            logging.info(f"✅ Data is fresh for {ticker} ({hours_since_update:.1f} hours old)")
                            return existing_data
                        else:
                            # 🔄 Data is stale (24+ hours old) - need fresh data
                            logging.info(f"🔄 Data is stale for {ticker} ({hours_since_update:.1f} hours old), downloading fresh data")
                            success = await self.download_and_store_ticker(ticker, collection_name)
                            
                            if success:
                                return self.get_earnings_and_future_data(ticker, collection_name)
                            else:
                                logging.error(f"❌ Failed to download fresh data for {ticker} after staleness check")
                                return existing_data  # Return old data if fresh download fails
                                
                    except (ValueError, TypeError) as e:
                        logging.warning(f"⚠️ Could not parse stored_at timestamp '{stored_at}' for {ticker}: {e}")
                        logging.info(f"✅ Using existing data for {ticker} (timestamp parsing failed)")
                        return existing_data
                else:
                    # No timestamp in metadata - need fresh data with complete metadata
                    logging.info(f"🔄 No timestamp found in metadata for {ticker}, downloading fresh data to get complete metadata")
                    success = await self.download_and_store_ticker(ticker, collection_name)
                    
                    if success:
                        return self.get_earnings_and_future_data(ticker, collection_name)
                    else:
                        logging.error(f"❌ Failed to download fresh data for {ticker} to get complete metadata")
                        return existing_data  # Return old data if fresh download fails
            
            # 📥 No data exists - download fresh data
            logging.info(f"📭 No existing data found for {ticker}, downloading...")
            success = await self.download_and_store_ticker(ticker, collection_name)
            
            if success:
                # Retrieve the newly stored data
                return self.get_earnings_and_future_data(ticker, collection_name)
            else:
                logging.error(f"❌ Failed to download earnings and future data for {ticker}")
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


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('earnings_and_future_db_agent.log')
        ]
    )


def main():
    """Main function to handle command line arguments and execute earnings and future operations."""
    parser = argparse.ArgumentParser(description='Earnings and Future DB Agent - Simple ticker download tool')
    
    # Simple ticker input
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., AAPL, TSLA, PLTR)')
    
    # Optional arguments
    parser.add_argument('--list-tickers', action='store_true', help='List all stored earnings and future tickers')
    parser.add_argument('--get-data', action='store_true', help='Retrieve stored data for the ticker')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # PREDEFINED DATABASE CONFIGURATION (same as other DB Agents)
    DB_TYPE = "redis"  # Using Redis as default
    DB_COLLECTION = "Earnings_and_Future_INFOS"
    
    # Redis configuration (predefined - same as other DB Agents)
    REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
    REDIS_PORT = 16376
    REDIS_USERNAME = "default"
    REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    
    try:
        logging.info(f"🔧 INITIALIZING {DB_TYPE.upper()} STORAGE FOR EARNINGS AND FUTURE")
        logging.info(f"   - Database type: {DB_TYPE}")
        logging.info(f"   - Collection/Namespace: {DB_COLLECTION}")
        logging.info(f"   - Ticker: {args.ticker.upper()}")
        logging.info(f"   - Log level: {args.log_level}")
        
        # Initialize storage with predefined configuration
        storage = EarningsAndFutureDatabaseStorage(
            db_type=DB_TYPE,
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD
        )
        
        # List earnings and future tickers
        if args.list_tickers:
            logging.info(f"📋 LISTING EARNINGS AND FUTURE TICKERS")
            try:
                tickers = storage.list_earnings_and_future_tickers(DB_COLLECTION)
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
            logging.info(f"📈 RETRIEVING EARNINGS AND FUTURE DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            
            data = storage.get_earnings_and_future_data(args.ticker.upper(), DB_COLLECTION)
            if data:
                logging.info("✅ EARNINGS AND FUTURE DATA RETRIEVED SUCCESSFULLY")
                logging.info(f"   - Transcript length: {len(data.get('earnings_and_future', {}).get('transcript', ''))}")
                logging.info(f"   - Future development length: {len(data.get('earnings_and_future', {}).get('future_development', ''))}")
                logging.info(f"   - Metadata: {data.get('metadata', {})}")
                logging.info(f"   - Last updated: {data.get('stored_at', 'Unknown')}")
            else:
                logging.warning(f"⚠️ No data found for ticker: {args.ticker.upper()}")
        
        # Download and store ticker data (DEFAULT ACTION)
        else:
            logging.info(f"📥 CHECKING AND UPDATING EARNINGS AND FUTURE DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            logging.info(f"   - Collection: {DB_COLLECTION}")
            
            # Use the update logic instead of always downloading
            import asyncio
            data = asyncio.run(storage.get_or_download_earnings_and_future(args.ticker.upper(), DB_COLLECTION))
            if data:
                logging.info("✅ EARNINGS AND FUTURE DATA AVAILABLE (fresh or existing)")
                logging.info(f"   - Transcript length: {len(data.get('earnings_and_future', {}).get('transcript', ''))}")
                logging.info(f"   - Future development length: {len(data.get('earnings_and_future', {}).get('future_development', ''))}")
                logging.info(f"   - Metadata: {data.get('metadata', {})}")
            else:
                logging.error("❌ FAILED TO GET EARNINGS AND FUTURE DATA")
                sys.exit(1)
        
        # Show collection stats
        logging.info(f"📊 COLLECTION STATISTICS")
        tickers = storage.list_earnings_and_future_tickers(DB_COLLECTION)
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
    # python Earnings_and_Future_DB_Agent.py AAPL
    # python Earnings_and_Future_DB_Agent.py TSLA
    # python Earnings_and_Future_DB_Agent.py --list-tickers
    # python Earnings_and_Future_DB_Agent.py AAPL --get-data
    main()