#!/usr/bin/env python3
"""
Financial Metrics Database Storage Script
Handles storing financial metrics data to Redis collections.
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


class RedisFinancialMetricsStorage:
    """
    A class to handle Redis storage operations for financial metrics data.
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
            logging.info("✅ Using shared financial metrics Redis connection")
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
    
    def store_financial_metrics_data(self, ticker: str, financial_metrics: Dict, metadata: Dict, collection_name: str = "financial_metrics") -> bool:
        """
        Store financial metrics data in Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            financial_metrics (Dict): Financial metrics data
            metadata (Dict): Metadata information
            collection_name (str): Name of the collection/namespace to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create Redis key with collection namespace
            redis_key = f"{collection_name}:{ticker.upper()}"
            
            # Prepare data for storage
            data_to_store = {
                "ticker": ticker.upper(),
                "financial_metrics": financial_metrics,
                "metadata": metadata,
                "stored_at": datetime.now().isoformat(),
                "collection": collection_name
            }
            
            # Store in Redis
            self.client.set(redis_key, json.dumps(data_to_store))
            
            # Set expiry (30 days)
            self.client.expire(redis_key, 30 * 24 * 60 * 60)
            
            logging.info(f"✅ Successfully stored financial metrics data for {ticker}")
            logging.info(f"   - Redis key: {redis_key}")
            logging.info(f"   - Collection: {collection_name}")
            logging.info(f"   - Expiry: 30 days")
            
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to store financial metrics data for {ticker}: {e}")
            return False
    
    def get_financial_metrics_data(self, ticker: str, collection_name: str = "financial_metrics") -> Optional[Dict]:
        """
        Retrieve financial metrics data from Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection
            
        Returns:
            Optional[Dict]: Financial metrics data or None if not found
        """
        try:
            redis_key = f"{collection_name}:{ticker.upper()}"
            
            # Get data from Redis
            stored_data = self.client.get(redis_key)
            
            if stored_data:
                data = json.loads(stored_data)
                logging.info(f"✅ Retrieved financial metrics data for {ticker}")
                return data
            else:
                logging.info(f"ℹ️ No financial metrics data found for {ticker}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error retrieving financial metrics data for {ticker}: {e}")
            return None
    
    def list_financial_metrics_tickers(self, collection_name: str = "financial_metrics") -> List[str]:
        """
        List all tickers with financial metrics data.
        
        Args:
            collection_name (str): Name of the collection
            
        Returns:
            List[str]: List of ticker symbols
        """
        try:
            # Get all keys in the collection namespace
            pattern = f"{collection_name}:*"
            keys = self.client.keys(pattern)
            
            # Extract ticker symbols from keys
            tickers = [key.split(":")[1] for key in keys if ":" in key]
            
            logging.info(f"✅ Found {len(tickers)} tickers with financial metrics data")
            return tickers
            
        except Exception as e:
            logging.error(f"❌ Error listing financial metrics tickers: {e}")
            return []
    
    def delete_financial_metrics_data(self, ticker: str, collection_name: str = "financial_metrics") -> bool:
        """
        Delete financial metrics data for a ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            redis_key = f"{collection_name}:{ticker.upper()}"
            
            # Delete from Redis
            result = self.client.delete(redis_key)
            
            if result > 0:
                logging.info(f"✅ Successfully deleted financial metrics data for {ticker}")
                return True
            else:
                logging.info(f"ℹ️ No financial metrics data found to delete for {ticker}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Error deleting financial metrics data for {ticker}: {e}")
            return False
    
    def close(self):
        """Close Redis connection."""
        if self.client:
            self.client.close()
            logging.info("🔚 Redis connection closed")


class FinancialMetricsDatabaseStorage:
    """
    Main class for managing financial metrics database operations.
    """
    
    def __init__(self, db_type: str = "redis", shared_clients=None, host: str = None, port: int = None, 
                 username: str = "default", password: str = None):
        """
        Initialize Financial Metrics Database Storage.
        
        Args:
            db_type (str): Database type (currently only "redis" supported)
            shared_clients: Shared clients instance for Redis connections
            host (str): Redis host
            port (int): Redis port
            username (str): Redis username
            password (str): Redis password
        """
        self.db_type = db_type.lower()
        
        if self.db_type == "redis":
            if shared_clients:
                # Use shared Redis connection
                self.storage = RedisFinancialMetricsStorage(
                    shared_clients=shared_clients
                )
            else:
                self.storage = RedisFinancialMetricsStorage(
                    host=host,
                    port=port,
                    username=username,
                    password=password
                )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
        logging.info(f"✅ Financial Metrics Database Storage initialized with {self.db_type}")
    
    def store_financial_metrics_data(self, ticker: str, financial_metrics: Dict, metadata: Dict, collection_name: str = "Financial_Metrics_INFOS") -> bool:
        """
        Store financial metrics data in the database.
        
        Args:
            ticker (str): Stock ticker symbol
            financial_metrics (Dict): Financial metrics data
            metadata (Dict): Metadata information
            collection_name (str): Name of the collection
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.storage.store_financial_metrics_data(
            ticker=ticker,
            financial_metrics=financial_metrics,
            metadata=metadata,
            collection_name=collection_name
        )
    
    def get_financial_metrics_data(self, ticker: str, collection_name: str = "Financial_Metrics_INFOS") -> Optional[Dict]:
        """
        Get financial metrics data from database.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection
            
        Returns:
            Optional[Dict]: Financial metrics data or None if not found
        """
        return self.storage.get_financial_metrics_data(ticker, collection_name)
    
    def list_financial_metrics_tickers(self, collection_name: str = "Financial_Metrics_INFOS") -> List[str]:
        """List all tickers with financial metrics data."""
        return self.storage.list_financial_metrics_tickers(collection_name)
    
    async def download_and_store_ticker(self, ticker: str, collection_name: str = "Financial_Metrics_INFOS") -> bool:
        """
        Download and store ticker financial metrics data.
        Uses Financial_Metrics_Storage_Agent to generate fresh data and stores in database.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Downloading and storing financial metrics data for ticker: {ticker}")
            logging.info(f"   - Collection: {collection_name}")
            
            # Import and call Financial_Metrics_Storage_Agent functions to generate fresh data
            from Financial_Metrics_Storage_Agent import process_financial_metrics
            
            logging.info(f"🔄 Calling Financial_Metrics_Storage_Agent functions to analyze {ticker}...")
            
            # Call the storage agent function to generate fresh data
            result = await process_financial_metrics(ticker)
            
            if not result:
                logging.error(f"❌ Financial_Metrics_Storage_Agent failed for {ticker}")
                return False
            
            logging.info(f"✅ Successfully generated financial metrics data for {ticker}")
            logging.info(f"   - Financial metrics: {'✅' if result.get('financial_metrics', {}).get('financial_metrics') else '❌'}")
            logging.info(f"   - DCF data: {'✅' if result.get('financial_metrics', {}).get('dcf', {}).get('best_estimate') else '❌'}")
            logging.info(f"   - Price data: {'✅' if result.get('financial_metrics', {}).get('price', {}).get('latest_price') else '❌'}")
            
            # Store the fresh data in database
            success = self.store_financial_metrics_data(
                ticker=ticker,
                financial_metrics=result['financial_metrics'],
                metadata=result['metadata'],
                collection_name=collection_name
            )
            
            if success:
                logging.info(f"✅ Successfully downloaded and stored {ticker} financial metrics data")
            else:
                logging.error(f"❌ Failed to store {ticker} financial metrics data in database")
            
            return success
            
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR DOWNLOADING FINANCIAL METRICS DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    async def get_or_download_financial_metrics(self, ticker: str, collection_name: str = "Financial_Metrics_INFOS") -> Optional[Dict]:
        """
        Get financial metrics data from database, download if not exists or data is stale.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection
            
        Returns:
            Optional[Dict]: Financial metrics data or None if failed
        """
        try:
            logging.info(f"🔍 Getting financial metrics data for ticker: {ticker}")
            
            # Check if data exists in database
            existing_data = self.get_financial_metrics_data(ticker, collection_name)
            
            if existing_data:
                # ✅ Data exists - check metadata for update time
                metadata = existing_data.get('metadata', {})
                last_update = metadata.get('latest_update_time')
                
                if last_update:
                    try:
                        # Check if data is older than 24 hours
                        current_time = datetime.now()
                        update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                        time_diff = current_time - update_time.replace(tzinfo=None)
                        
                        if time_diff.days > 0:  # Data is older than 1 day
                            # 🔄 Data is stale - need fresh data
                            logging.info(f"🔄 Data for {ticker} is older than 1 day, downloading fresh data")
                            success = await self.download_and_store_ticker(ticker, collection_name)
                            
                            if success:
                                return self.get_financial_metrics_data(ticker, collection_name)
                            else:
                                logging.error(f"❌ Failed to download fresh data for {ticker}")
                                return existing_data  # Return old data if fresh download fails
                        else:
                            # ✅ Data is fresh
                            logging.info(f"✅ Data for {ticker} is fresh (updated within 24 hours)")
                            return existing_data
                            
                    except Exception as e:
                        logging.warning(f"⚠️ Could not parse update time for {ticker}, returning existing data: {e}")
                        return existing_data
                else:
                    # No update time in metadata, return existing data
                    logging.info(f"ℹ️ No update time found in metadata for {ticker}, returning existing data")
                    return existing_data
            else:
                # ❌ No data exists - download fresh data
                logging.info(f"📥 No financial metrics data found for {ticker}, downloading fresh data")
                success = await self.download_and_store_ticker(ticker, collection_name)
                
                if success:
                    return self.get_financial_metrics_data(ticker, collection_name)
                else:
                    logging.error(f"❌ Failed to download fresh data for {ticker}")
                    return None
                    
        except Exception as e:
            logging.error(f"❌ Error in get_or_download_financial_metrics for {ticker}: {e}")
            return None
    
    def close(self):
        """Close database connections."""
        if hasattr(self, 'storage'):
            self.storage.close()


def main():
    """Main function for testing the Financial Metrics Database Storage."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('financial_metrics_db_agent.log')
        ]
    )
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Financial Metrics Database Storage Agent')
    parser.add_argument('ticker', nargs='?', help='Stock ticker symbol to process')
    parser.add_argument('--list-tickers', action='store_true', help='List all tickers in collection')
    parser.add_argument('--get-data', action='store_true', help='Get stored data for ticker')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Configuration
    DB_TYPE = "redis"  # Using Redis as default
    DB_COLLECTION = "Financial_Metrics_INFOS"
    
    # Redis configuration (predefined - same as other agents)
    REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
    REDIS_PORT = 16376
    REDIS_USERNAME = "default"
    REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    
    try:
        logging.info(f"🔧 INITIALIZING {DB_TYPE.upper()} STORAGE FOR FINANCIAL METRICS")
        logging.info(f"   - Database type: {DB_TYPE}")
        logging.info(f"   - Collection/Namespace: {DB_COLLECTION}")
        logging.info(f"   - Ticker: {args.ticker.upper() if args.ticker else 'N/A (list-tickers mode)'}")
        logging.info(f"   - Log level: {args.log_level}")
        
        # Initialize storage with predefined configuration
        storage = FinancialMetricsDatabaseStorage(
            db_type=DB_TYPE,
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD
        )
        
        # List financial metrics tickers
        if args.list_tickers:
            logging.info(f"📋 LISTING FINANCIAL METRICS TICKERS")
            try:
                tickers = storage.list_financial_metrics_tickers(DB_COLLECTION)
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
            logging.info(f"📈 RETRIEVING FINANCIAL METRICS DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            
            data = storage.get_financial_metrics_data(args.ticker.upper(), DB_COLLECTION)
            if data:
                logging.info("✅ FINANCIAL METRICS DATA RETRIEVED SUCCESSFULLY")
                logging.info(f"   - Financial metrics: {'✅' if data.get('financial_metrics', {}).get('financial_metrics') else '❌'}")
                logging.info(f"   - DCF data: {'✅' if data.get('financial_metrics', {}).get('dcf', {}).get('best_estimate') else '❌'}")
                logging.info(f"   - Price data: {'✅' if data.get('financial_metrics', {}).get('price', {}).get('latest_price') else '❌'}")
                logging.info(f"   - Metadata: {data.get('metadata', {})}")
                logging.info(f"   - Last updated: {data.get('stored_at', 'Unknown')}")
            else:
                logging.warning(f"⚠️ No data found for ticker: {args.ticker.upper()}")
        
        # Download and store ticker data (DEFAULT ACTION)
        else:
            logging.info(f"📥 CHECKING AND UPDATING FINANCIAL METRICS DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            logging.info(f"   - Collection: {DB_COLLECTION}")
            
            # Use the update logic instead of always downloading
            data = storage.get_or_download_financial_metrics(args.ticker.upper(), DB_COLLECTION)
            if data:
                logging.info("✅ FINANCIAL METRICS DATA AVAILABLE (fresh or existing)")
                logging.info(f"   - Financial metrics: {'✅' if data.get('financial_metrics', {}).get('financial_metrics') else '❌'}")
                logging.info(f"   - DCF data: {'✅' if data.get('financial_metrics', {}).get('dcf', {}).get('best_estimate') else '❌'}")
                logging.info(f"   - Price data: {'✅' if data.get('financial_metrics', {}).get('price', {}).get('latest_price') else '❌'}")
                logging.info(f"   - Metadata: {data.get('metadata', {})}")
            else:
                logging.error("❌ FAILED TO GET FINANCIAL METRICS DATA")
                sys.exit(1)
        
        # Show collection stats
        logging.info(f"📊 COLLECTION STATISTICS")
        tickers = storage.list_financial_metrics_tickers(DB_COLLECTION)
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
    # python Financial_Metrics_DB_Agent.py AAPL
    # python Financial_Metrics_DB_Agent.py TSLA
    # python Financial_Metrics_DB_Agent.py --list-tickers
    # python Financial_Metrics_DB_Agent.py AAPL --get-data
    main()
