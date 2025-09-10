#!/usr/bin/env python3
"""
MongoDB Database Storage Script
Handles storing files and data to MongoDB collections with flexible input options.
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
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, WriteError, OperationFailure, BulkWriteError
import traceback
import redis


class RedisDatabaseStorage:
    """
    A class to handle Redis storage operations with flexible input options.
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
            logging.info("✅ Using shared stock trend Redis connection")
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
    
    def store_stock_trend_data(self, ticker: str, current_json: Dict, historical_json: Dict, metadata: Dict, collection_name: str = "stock_trends") -> bool:
        """
        Store stock trend data in Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            current_json (Dict): Current trend data
            historical_json (Dict): Historical trend data
            metadata (Dict): Metadata information
            collection_name (str): Name of the collection/namespace to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Processing stock trend data for ticker: {ticker}")
            logging.info(f"   - Redis namespace: {collection_name}")
            logging.info(f"   - Current trends: {len(current_json)} segments")
            logging.info(f"   - Historical trends: {len(historical_json)} segments")
            
            # Validate input data
            if not isinstance(current_json, dict):
                logging.error("❌ INVALID CURRENT JSON TYPE:")
                logging.error(f"   - Expected dict, got {type(current_json).__name__}")
                return False
            
            if not isinstance(historical_json, dict):
                logging.error("❌ INVALID HISTORICAL JSON TYPE:")
                logging.error(f"   - Expected dict, got {type(historical_json).__name__}")
                return False
            
            if not isinstance(metadata, dict):
                logging.error("❌ INVALID METADATA TYPE:")
                logging.error(f"   - Expected dict, got {type(metadata).__name__}")
                return False
            
            # Prepare comprehensive document
            document = {
                'ticker': ticker.upper(),
                'current_trends': current_json,
                'historical_trends': historical_json,
                'metadata': metadata,
                'stored_at': datetime.utcnow().isoformat(),
                'data_version': '1.0',
                'trend_count': {
                    'current': len(current_json),
                    'historical': len(historical_json)
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
                redis_key = f"{collection_name}:{ticker.upper()}_trends"
                logging.info(f"   - Attempting to store in Redis key: {redis_key}")
                
                # Store in Redis
                result = self.client.set(redis_key, document_str)
                
                if result:
                    logging.info(f"✓ Successfully stored stock trend data for {ticker}")
                    logging.info(f"   - Redis key: {redis_key}")
                    logging.info(f"   - Current trends: {len(current_json)}")
                    logging.info(f"   - Historical trends: {len(historical_json)}")
                    return True
                else:
                    logging.error("❌ REDIS WRITE ERROR:")
                    logging.error(f"   - Failed to write stock trend data to Redis")
                    return False
                
            except redis.RedisError as e:
                logging.error("❌ REDIS ERROR:")
                logging.error(f"   - Failed to write stock trend data to Redis")
                logging.error(f"   - Error details: {e}")
                return False
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR STORING STOCK TREND DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    def get_stock_trend_data(self, ticker: str, collection_name: str = "stock_trends") -> Optional[Dict]:
        """
        Retrieve stock trend data from Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection/namespace to query
            
        Returns:
            Optional[Dict]: Stock trend data or None if not found
        """
        try:
            logging.info(f"📈 Retrieving stock trend data for ticker: {ticker}")
            logging.info(f"   - Redis namespace: {collection_name}")
            
            redis_key = f"{collection_name}:{ticker.upper()}_trends"
            data_str = self.client.get(redis_key)
            
            if data_str:
                data = json.loads(data_str)
                logging.info(f"✓ Successfully retrieved stock trend data for {ticker}")
                logging.info(f"   - Current trends: {len(data.get('current_trends', {}))}")
                logging.info(f"   - Historical trends: {len(data.get('historical_trends', {}))}")
                return data
            else:
                logging.warning(f"⚠️ No stock trend data found for ticker: {ticker}")
                return None
                
        except Exception as e:
            logging.error("❌ ERROR RETRIEVING STOCK TREND DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return None
    
    def list_stock_tickers(self, collection_name: str = "stock_trends") -> List[str]:
        """
        List all stock tickers stored in the Redis namespace.
        
        Args:
            collection_name (str): Name of the collection/namespace to query
            
        Returns:
            List[str]: List of ticker symbols
        """
        try:
            logging.info(f"📋 Listing stock tickers in Redis namespace: {collection_name}")
            
            # Get all keys matching the pattern
            pattern = f"{collection_name}:*_trends"
            keys = self.client.keys(pattern)
            
            tickers = []
            for key in keys:
                # Extract ticker from key (e.g., "Stock_Trend_INFOS:AAPL_trends" -> "AAPL")
                ticker = key.split(":")[-1].replace("_trends", "")
                tickers.append(ticker)
            
            logging.info(f"   - Found {len(tickers)} tickers")
            if tickers:
                for i, ticker in enumerate(tickers, 1):
                    logging.info(f"   - [{i}] {ticker}")
            else:
                logging.info("   - No tickers found in Redis")
            
            return tickers
            
        except Exception as e:
            logging.error("❌ ERROR LISTING STOCK TICKERS:")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return []
    
    def close(self):
        """Close the Redis connection."""
        if self.client:
            self.client.close()
            logging.info("🔚 Redis connection closed")
    
    async def update_if_stale_with_lock(self, ticker: str, collection_name: str = "stock_trends", force_update: bool = False) -> str:
        """
        Update shared data with locking to prevent duplicate expensive API calls.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Collection name
            force_update (bool): Force update regardless of staleness
            
        Returns:
            str: "data_fresh", "updated", or "waited_for_update"
        """
        import time
        from datetime import datetime, timedelta
        
        try:
            # Check if data exists and is fresh
            existing_data = self.get_stock_trend_data(ticker, collection_name)
            
            if existing_data and not force_update:
                # Check if data is fresh (within 24 hours)
                stored_at = existing_data.get('stored_at')
                if stored_at:
                    try:
                        if isinstance(stored_at, str):
                            stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                        else:
                            stored_datetime = stored_at
                        
                        hours_since_update = (datetime.now() - stored_datetime).total_seconds() / 3600
                        
                        if hours_since_update < 24:
                            logging.info(f"✅ Data for {ticker} is fresh ({hours_since_update:.1f} hours old)")
                            return "data_fresh"
                    except Exception as e:
                        logging.warning(f"⚠️ Could not parse stored_at timestamp: {e}")
            
            # Data is stale or force update requested
            lock_key = f"update_lock:{ticker.upper()}"
            
            # Try to acquire update lock (5 minute timeout)
            if self.client.set(lock_key, "locked", ex=300, nx=True):
                try:
                    logging.info(f"🔒 Acquired update lock for {ticker}, starting update...")
                    
                    # Import and call Stock_Trend_Storage_Agent to generate fresh data
                    from Stock_Trend_Storage_Agent import analyze_stock_trends
                    
                    logging.info(f"🔄 Calling Stock_Trend_Storage_Agent to analyze {ticker}...")
                    
                    # Call the storage agent to generate fresh data
                    historical_json, current_json, metadata = await analyze_stock_trends(
                        ticker=ticker,
                        force_update=force_update,
                        use_multiprocessing=True
                    )
                    
                    logging.info(f"✅ Successfully generated data for {ticker}")
                    logging.info(f"   - Historical trends: {len(historical_json)} segments")
                    logging.info(f"   - Current trends: {len(current_json)} segments")
                    
                    # Store the fresh data
                    success = self.store_stock_trend_data(ticker, current_json, historical_json, metadata, collection_name)
                    
                    if success:
                        logging.info(f"✅ Successfully updated shared data for {ticker}")
                        return "updated"
                    else:
                        logging.error(f"❌ Failed to store updated data for {ticker}")
                        return "update_failed"
                        
                finally:
                    # Always release the lock
                    self.client.delete(lock_key)
                    logging.info(f"🔓 Released update lock for {ticker}")
            else:
                # Another user is already updating, wait for completion
                logging.info(f"⏳ Another user is updating {ticker}, waiting for completion...")
                
                # Wait for lock to be released (max 5 minutes)
                max_wait_time = 300  # 5 minutes
                wait_interval = 2  # Check every 2 seconds
                
                for _ in range(max_wait_time // wait_interval):
                    if not self.client.exists(lock_key):
                        logging.info(f"✅ Update completed by another user for {ticker}")
                        return "waited_for_update"
                    time.sleep(wait_interval)
                
                logging.warning(f"⚠️ Timeout waiting for {ticker} update, proceeding with stale data")
                return "timeout"
                
        except Exception as e:
            logging.error(f"❌ Error in update_if_stale_with_lock for {ticker}: {e}")
            return "error"


class MongoDatabaseStorage:
    """
    A class to handle MongoDB storage operations with flexible input options.
    """
    
    def __init__(self, uri: str, database_name: str):
        """
        Initialize MongoDB connection.
        
        Args:
            uri (str): MongoDB connection URI
            database_name (str): Name of the database to use
        """
        self.uri = uri
        self.database_name = database_name
        self.client = None
        self.db = None
        self._connect()
    
    def _connect(self):
        """Establish connection to MongoDB."""
        try:
            logging.info(f"Attempting to connect to MongoDB...")
            logging.info(f"Database name: {self.database_name}")
            logging.info(f"URI (masked): {self.uri.split('@')[1] if '@' in self.uri else 'URI format error'}")
            
            self.client = MongoClient(self.uri)
            
            # Test the connection with timeout
            logging.info("Testing connection with ping command...")
            self.client.admin.command('ping')
            logging.info("✓ Ping successful - MongoDB server is reachable")
            
            # Check if database exists or can be created
            self.db = self.client[self.database_name]
            logging.info(f"✓ Successfully connected to database: {self.database_name}")
            
            # Test write permissions
            test_collection = self.db['_test_write_permission']
            test_doc = {'test': True, 'timestamp': datetime.utcnow()}
            test_result = test_collection.insert_one(test_doc)
            test_collection.delete_one({'_id': test_result.inserted_id})
            logging.info("✓ Write permissions verified")
            
        except ConnectionFailure as e:
            logging.error("❌ CONNECTION FAILURE:")
            logging.error(f"   - Cannot connect to MongoDB server")
            logging.error(f"   - Check if MongoDB server is running")
            logging.error(f"   - Check if URI is correct")
            logging.error(f"   - Check network connectivity")
            logging.error(f"   - Error details: {e}")
            raise
        except ServerSelectionTimeoutError as e:
            logging.error("❌ SERVER SELECTION TIMEOUT:")
            logging.error(f"   - MongoDB server is not responding")
            logging.error(f"   - Check if server is running and accessible")
            logging.error(f"   - Check firewall settings")
            logging.error(f"   - Error details: {e}")
            raise
        except OperationFailure as e:
            logging.error("❌ OPERATION FAILURE:")
            logging.error(f"   - Database operation failed")
            logging.error(f"   - Check database permissions")
            logging.error(f"   - Check if database exists")
            logging.error(f"   - Error details: {e}")
            raise
        except Exception as e:
            logging.error("❌ UNEXPECTED CONNECTION ERROR:")
            logging.error(f"   - Unexpected error during connection")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            raise
    
    def store_file(self, file_path: str, collection_name: str, metadata: Optional[Dict] = None) -> bool:
        """
        Store a file's content to MongoDB collection.
        
        Args:
            file_path (str): Path to the file to store
            collection_name (str): Name of the collection to store in
            metadata (Optional[Dict]): Additional metadata to store with the file
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📁 Processing file: {file_path}")
            
            # Validate file path
            file_path = Path(file_path)
            logging.info(f"   - Resolved path: {file_path.absolute()}")
            
            # Check if file exists
            if not file_path.exists():
                logging.error("❌ FILE NOT FOUND:")
                logging.error(f"   - File does not exist: {file_path}")
                logging.error(f"   - Current working directory: {os.getcwd()}")
                logging.error(f"   - Check if file path is correct")
                return False
            
            # Check file permissions
            if not os.access(file_path, os.R_OK):
                logging.error("❌ FILE PERMISSION ERROR:")
                logging.error(f"   - Cannot read file: {file_path}")
                logging.error(f"   - Check file permissions")
                return False
            
            # Check file size
            file_size = file_path.stat().st_size
            logging.info(f"   - File size: {file_size} bytes")
            
            # Check if file is too large (MongoDB document limit is 16MB)
            if file_size > 16 * 1024 * 1024:  # 16MB
                logging.error("❌ FILE TOO LARGE:")
                logging.error(f"   - File size: {file_size} bytes")
                logging.error(f"   - MongoDB document limit: 16MB")
                logging.error(f"   - Consider splitting the file or using GridFS")
                return False
            
            # Check file type and encoding
            file_extension = file_path.suffix.lower()
            logging.info(f"   - File type: {file_extension}")
            
            # Try to read file content with different encodings
            content = None
            encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logging.info(f"   - Successfully read with encoding: {encoding}")
                    break
                except UnicodeDecodeError:
                    logging.warning(f"   - Failed to read with encoding: {encoding}")
                    continue
            
            if content is None:
                logging.error("❌ FILE ENCODING ERROR:")
                logging.error(f"   - Cannot read file with any supported encoding")
                logging.error(f"   - Tried encodings: {encodings_to_try}")
                return False
            
            # Validate collection name
            if not collection_name or not collection_name.strip():
                logging.error("❌ INVALID COLLECTION NAME:")
                logging.error(f"   - Collection name is empty or invalid")
                return False
            
            logging.info(f"   - Target collection: {collection_name}")
            
            # Prepare document
            document = {
                'filename': file_path.name,
                'file_path': str(file_path),
                'content': content,
                'file_size': file_size,
                'file_type': file_extension,
                'uploaded_at': datetime.utcnow(),
                'metadata': metadata or {}
            }
            
            logging.info(f"   - Document prepared, size: {len(str(document))} characters")
            
            # Store in MongoDB
            try:
                collection = self.db[collection_name]
                logging.info(f"   - Attempting to insert into collection: {collection_name}")
                
                result = collection.insert_one(document)
                
                logging.info(f"✓ Successfully stored file '{file_path.name}' in collection '{collection_name}'")
                logging.info(f"   - Document ID: {result.inserted_id}")
                logging.info(f"   - Collection: {collection_name}")
                logging.info(f"   - Database: {self.database_name}")
                return True
                
            except WriteError as e:
                logging.error("❌ MONGODB WRITE ERROR:")
                logging.error(f"   - Failed to write to MongoDB")
                logging.error(f"   - Error code: {e.code}")
                logging.error(f"   - Error details: {e}")
                if "duplicate key" in str(e).lower():
                    logging.error(f"   - Possible duplicate document")
                elif "document too large" in str(e).lower():
                    logging.error(f"   - Document exceeds MongoDB size limit")
                return False
                
            except OperationFailure as e:
                logging.error("❌ MONGODB OPERATION FAILURE:")
                logging.error(f"   - Database operation failed")
                logging.error(f"   - Error code: {e.code}")
                logging.error(f"   - Error details: {e}")
                return False
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR STORING FILE:")
            logging.error(f"   - File: {file_path}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    def store_json_data(self, data: Dict[str, Any], collection_name: str, document_id: Optional[str] = None) -> bool:
        """
        Store JSON data to MongoDB collection.
        
        Args:
            data (Dict[str, Any]): Data to store
            collection_name (str): Name of the collection to store in
            document_id (Optional[str]): Custom document ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📊 Processing JSON data for collection: {collection_name}")
            
            # Validate input data
            if not isinstance(data, dict):
                logging.error("❌ INVALID DATA TYPE:")
                logging.error(f"   - Expected dict, got {type(data).__name__}")
                return False
            
            # Validate collection name
            if not collection_name or not collection_name.strip():
                logging.error("❌ INVALID COLLECTION NAME:")
                logging.error(f"   - Collection name is empty or invalid")
                return False
            
            logging.info(f"   - Data type: {type(data).__name__}")
            logging.info(f"   - Data keys: {list(data.keys())}")
            logging.info(f"   - Document ID: {document_id if document_id else 'Auto-generated'}")
            
            # Check data size
            data_str = json.dumps(data)
            data_size = len(data_str)
            logging.info(f"   - Data size: {data_size} characters")
            
            # Check if data is too large (MongoDB document limit is 16MB)
            if data_size > 16 * 1024 * 1024:  # 16MB
                logging.error("❌ DATA TOO LARGE:")
                logging.error(f"   - Data size: {data_size} characters")
                logging.error(f"   - MongoDB document limit: 16MB")
                logging.error(f"   - Consider splitting the data")
                return False
            
            # Add timestamp
            data['stored_at'] = datetime.utcnow()
            
            try:
                collection = self.db[collection_name]
                logging.info(f"   - Attempting to store in collection: {collection_name}")
                
                if document_id:
                    # Use custom ID
                    data['_id'] = document_id
                    logging.info(f"   - Using custom document ID: {document_id}")
                    result = collection.replace_one({'_id': document_id}, data, upsert=True)
                    operation = "upserted" if result.upserted_id else "updated"
                else:
                    # Let MongoDB generate ID
                    logging.info(f"   - Using auto-generated document ID")
                    result = collection.insert_one(data)
                    operation = "inserted"
                
                document_id_result = result.upserted_id or result.inserted_id
                logging.info(f"✓ Successfully {operation} data in collection '{collection_name}'")
                logging.info(f"   - Document ID: {document_id_result}")
                logging.info(f"   - Collection: {collection_name}")
                logging.info(f"   - Database: {self.database_name}")
                return True
                
            except WriteError as e:
                logging.error("❌ MONGODB WRITE ERROR:")
                logging.error(f"   - Failed to write JSON data to MongoDB")
                logging.error(f"   - Error code: {e.code}")
                logging.error(f"   - Error details: {e}")
                if "duplicate key" in str(e).lower():
                    logging.error(f"   - Possible duplicate document ID")
                elif "document too large" in str(e).lower():
                    logging.error(f"   - Document exceeds MongoDB size limit")
                return False
                
            except OperationFailure as e:
                logging.error("❌ MONGODB OPERATION FAILURE:")
                logging.error(f"   - Database operation failed")
                logging.error(f"   - Error code: {e.code}")
                logging.error(f"   - Error details: {e}")
                return False
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR STORING JSON DATA:")
            logging.error(f"   - Collection: {collection_name}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    def store_multiple_files(self, file_paths: List[str], collection_name: str, metadata: Optional[Dict] = None) -> Dict[str, bool]:
        """
        Store multiple files to MongoDB collection.
        
        Args:
            file_paths (List[str]): List of file paths to store
            collection_name (str): Name of the collection to store in
            metadata (Optional[Dict]): Additional metadata to store with files
            
        Returns:
            Dict[str, bool]: Dictionary mapping file paths to success status
        """
        logging.info(f"📦 Processing multiple files: {len(file_paths)} files")
        logging.info(f"   - Collection: {collection_name}")
        logging.info(f"   - Metadata: {metadata}")
        
        # Validate input
        if not file_paths:
            logging.error("❌ NO FILES PROVIDED:")
            logging.error(f"   - Empty file list provided")
            return {}
        
        if not isinstance(file_paths, list):
            logging.error("❌ INVALID FILE PATHS TYPE:")
            logging.error(f"   - Expected list, got {type(file_paths).__name__}")
            return {}
        
        # Check for duplicate files
        unique_files = list(set(file_paths))
        if len(unique_files) != len(file_paths):
            logging.warning(f"⚠️  DUPLICATE FILES DETECTED:")
            logging.warning(f"   - Original count: {len(file_paths)}")
            logging.warning(f"   - Unique count: {len(unique_files)}")
            logging.warning(f"   - Duplicates removed")
        
        results = {}
        successful = 0
        failed = 0
        
        for i, file_path in enumerate(file_paths, 1):
            logging.info(f"   [{i}/{len(file_paths)}] Processing: {file_path}")
            success = self.store_file(file_path, collection_name, metadata)
            results[file_path] = success
            
            if success:
                successful += 1
            else:
                failed += 1
        
        logging.info(f"📊 BATCH PROCESSING SUMMARY:")
        logging.info(f"   - Total files: {len(file_paths)}")
        logging.info(f"   - Successful: {successful}")
        logging.info(f"   - Failed: {failed}")
        logging.info(f"   - Success rate: {(successful/len(file_paths)*100):.1f}%")
        
        if failed > 0:
            logging.warning(f"⚠️  SOME FILES FAILED TO STORE:")
            for file_path, success in results.items():
                if not success:
                    logging.warning(f"   - Failed: {file_path}")
        
        return results
    
    def store_directory(self, directory_path: str, collection_name: str, file_extensions: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Store all files in a directory to MongoDB collection.
        
        Args:
            directory_path (str): Path to the directory
            collection_name (str): Name of the collection to store in
            file_extensions (Optional[List[str]]): List of file extensions to include (e.g., ['.txt', '.json'])
            
        Returns:
            Dict[str, bool]: Dictionary mapping file paths to success status
        """
        logging.info(f"📁 Processing directory: {directory_path}")
        logging.info(f"   - Collection: {collection_name}")
        logging.info(f"   - File extensions: {file_extensions if file_extensions else 'All files'}")
        
        # Validate directory path
        directory = Path(directory_path)
        logging.info(f"   - Resolved path: {directory.absolute()}")
        
        # Check if directory exists
        if not directory.exists():
            logging.error("❌ DIRECTORY NOT FOUND:")
            logging.error(f"   - Directory does not exist: {directory_path}")
            logging.error(f"   - Current working directory: {os.getcwd()}")
            logging.error(f"   - Check if directory path is correct")
            return {}
        
        # Check if it's actually a directory
        if not directory.is_dir():
            logging.error("❌ NOT A DIRECTORY:")
            logging.error(f"   - Path exists but is not a directory: {directory_path}")
            logging.error(f"   - Check if path points to a file instead of directory")
            return {}
        
        # Check directory permissions
        if not os.access(directory, os.R_OK):
            logging.error("❌ DIRECTORY PERMISSION ERROR:")
            logging.error(f"   - Cannot read directory: {directory_path}")
            logging.error(f"   - Check directory permissions")
            return {}
        
        # Scan for files
        logging.info(f"   - Scanning directory for files...")
        file_paths = []
        total_files_found = 0
        skipped_files = 0
        
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                total_files_found += 1
                
                # Check file extensions filter
                if file_extensions is None or file_path.suffix.lower() in [ext.lower() for ext in file_extensions]:
                    file_paths.append(str(file_path))
                else:
                    skipped_files += 1
                    logging.debug(f"   - Skipped (extension filter): {file_path.name}")
        
        logging.info(f"   - Total files found: {total_files_found}")
        logging.info(f"   - Files matching filter: {len(file_paths)}")
        logging.info(f"   - Files skipped: {skipped_files}")
        
        if not file_paths:
            logging.warning("⚠️  NO FILES FOUND:")
            logging.warning(f"   - No files match the specified extensions")
            logging.warning(f"   - Available extensions in directory:")
            extensions_found = set()
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    extensions_found.add(file_path.suffix.lower())
            for ext in sorted(extensions_found):
                logging.warning(f"     - {ext}")
            return {}
        
        # Process files
        return self.store_multiple_files(file_paths, collection_name)
    
    def list_collections(self) -> List[str]:
        """List all collections in the database."""
        try:
            logging.info(f"📋 Listing collections in database: {self.database_name}")
            
            collections = self.db.list_collection_names()
            logging.info(f"   - Found {len(collections)} collections")
            
            if collections:
                for i, collection in enumerate(collections, 1):
                    logging.info(f"   - [{i}] {collection}")
            else:
                logging.warning(f"   - No collections found in database")
            
            return collections
            
        except OperationFailure as e:
            logging.error("❌ ERROR LISTING COLLECTIONS:")
            logging.error(f"   - Error code: {e.code}")
            logging.error(f"   - Error details: {e}")
            return []
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR LISTING COLLECTIONS:")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return []
    
    def get_collection_stats(self, collection_name: str) -> Dict[str, Any]:
        """Get statistics for a collection."""
        try:
            logging.info(f"📊 Getting statistics for collection: {collection_name}")
            
            # Validate collection name
            if not collection_name or not collection_name.strip():
                logging.error("❌ INVALID COLLECTION NAME:")
                logging.error(f"   - Collection name is empty or invalid")
                return {"count": 0, "total_size": 0, "error": "Invalid collection name"}
            
            collection = self.db[collection_name]
            
            # Check if collection exists
            if collection_name not in self.db.list_collection_names():
                logging.warning(f"⚠️  COLLECTION DOES NOT EXIST:")
                logging.warning(f"   - Collection '{collection_name}' not found")
                logging.warning(f"   - Available collections: {self.db.list_collection_names()}")
                return {"count": 0, "total_size": 0, "error": "Collection not found"}
            
            # Get basic stats
            count = collection.count_documents({})
            logging.info(f"   - Document count: {count}")
            
            # Get size stats (only for documents with 'content' field)
            try:
                stats = collection.aggregate([
                    {"$match": {"content": {"$exists": True}}},
                    {"$group": {
                        "_id": None,
                        "count": {"$sum": 1},
                        "total_size": {"$sum": {"$strLenCP": "$content"}},
                        "avg_size": {"$avg": {"$strLenCP": "$content"}}
                    }}
                ])
                result = list(stats)
                if result:
                    stats_data = result[0]
                    logging.info(f"   - Documents with content: {stats_data.get('count', 0)}")
                    logging.info(f"   - Total content size: {stats_data.get('total_size', 0)} characters")
                    logging.info(f"   - Average content size: {stats_data.get('avg_size', 0):.1f} characters")
                    return stats_data
                else:
                    logging.info(f"   - No documents with content field found")
                    return {"count": 0, "total_size": 0, "avg_size": 0}
                    
            except OperationFailure as e:
                logging.error("❌ ERROR GETTING COLLECTION STATS:")
                logging.error(f"   - Error code: {e.code}")
                logging.error(f"   - Error details: {e}")
                return {"count": count, "total_size": 0, "error": str(e)}
                
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR GETTING STATS:")
            logging.error(f"   - Collection: {collection_name}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return {"count": 0, "total_size": 0, "error": str(e)}
    
    def close(self):
        """Close the MongoDB connection."""
        if self.client:
            self.client.close()
            logging.info("MongoDB connection closed")


class DatabaseStorage:
    """
    Unified database storage class that can switch between MongoDB and Redis.
    """
    
    def __init__(self, db_type: str = "redis", shared_clients=None, **kwargs):
        """
        Initialize database storage.
        
        Args:
            db_type (str): "mongodb" or "redis"
            shared_clients: Shared clients instance for Redis connections
            **kwargs: Database-specific connection parameters
        """
        self.db_type = db_type.lower()
        
        if self.db_type == "mongodb":
            self.storage = MongoDatabaseStorage(
                uri=kwargs.get('uri'),
                database_name=kwargs.get('database_name')
            )
        elif self.db_type == "redis":
            if shared_clients:
                # Use shared Redis connection
                self.storage = RedisDatabaseStorage(
                    shared_clients=shared_clients
                )
            else:
                self.storage = RedisDatabaseStorage(
                    host=kwargs.get('host'),
                    port=kwargs.get('port'),
                    username=kwargs.get('username', 'default'),
                    password=kwargs.get('password'),
                    decode_responses=kwargs.get('decode_responses', True)
                )
        else:
            raise ValueError(f"Unsupported database type: {db_type}. Use 'mongodb' or 'redis'")
    
    def store_stock_trend_data(self, ticker: str, current_json: Dict, historical_json: Dict, metadata: Dict, collection_name: str = "stock_trends") -> bool:
        """Store stock trend data using the configured database."""
        return self.storage.store_stock_trend_data(ticker, current_json, historical_json, metadata, collection_name)
    
    def get_stock_trend_data(self, ticker: str, collection_name: str = "stock_trends") -> Optional[Dict]:
        """Retrieve stock trend data using the configured database."""
        return self.storage.get_stock_trend_data(ticker, collection_name)
    
    async def update_if_stale_with_lock(self, ticker: str, collection_name: str = "stock_trends", force_update: bool = False) -> str:
        """Update shared data with locking to prevent duplicate expensive API calls."""
        if hasattr(self.storage, 'update_if_stale_with_lock'):
            return self.storage.update_if_stale_with_lock(ticker, collection_name, force_update)
        else:
            # Fallback for MongoDB (not implemented yet)
            logging.warning(f"⚠️ Update locking not implemented for {self.db_type}")
            return "not_implemented"
    
    def list_stock_tickers(self, collection_name: str = "stock_trends") -> List[str]:
        """List stock tickers using the configured database."""
        return self.storage.list_stock_tickers(collection_name)
    
    def get_collection_stats(self, collection_name: str = "stock_trends") -> Dict:
        """Get collection statistics using the configured database."""
        if hasattr(self.storage, 'get_collection_stats'):
            return self.storage.get_collection_stats(collection_name)
        else:
            # For Redis, return basic stats
            tickers = self.list_stock_tickers(collection_name)
            return {
                'total_documents': len(tickers),
                'tickers': tickers,
                'database_type': self.db_type
            }
    
    def close(self):
        """Close the database connection."""
        self.storage.close()


    
    async def download_and_store_ticker(self, ticker: str, collection_name: str = "stock_trends", force_update: bool = False) -> bool:
        """
        Download and store ticker data with just the ticker symbol.
        Uses Stock_Trend_Storage_Agent to generate fresh data and stores in Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            collection_name (str): Name of the collection to store in
            force_update (bool): Force fresh analysis even if recent data exists
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📈 Downloading and storing data for ticker: {ticker}")
            logging.info(f"   - Collection: {collection_name}")
            logging.info(f"   - Force update: {force_update}")
            
            # Import and call Stock_Trend_Storage_Agent to generate fresh data
            from Stock_Trend_Storage_Agent import analyze_stock_trends
            
            logging.info(f"🔄 Calling Stock_Trend_Storage_Agent to analyze {ticker}...")
            
            # Call the storage agent to generate fresh data
            historical_json, current_json, metadata = await analyze_stock_trends(
                ticker=ticker,
                force_update=force_update,  # Use the force_update parameter
                use_multiprocessing=True
            )
            
            logging.info(f"✅ Successfully generated data for {ticker}")
            logging.info(f"   - Historical trends: {len(historical_json)} segments")
            logging.info(f"   - Current trends: {len(current_json)} segments")
            
            # Store the fresh data in Redis database
            success = self.store_stock_trend_data(ticker, current_json, historical_json, metadata, collection_name)
            
            if success:
                logging.info(f"✅ Successfully downloaded and stored {ticker} data in Redis")
            else:
                logging.error(f"❌ Failed to store {ticker} data in Redis database")
            
            return success
            
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR DOWNLOADING TICKER DATA:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    def store_stock_trend_files(self, ticker: str, current_file: str, historical_file: str, metadata_file: str, collection_name: str = "stock_trends") -> bool:
        """
        Store stock trend data from files to MongoDB.
        
        Args:
            ticker (str): Stock ticker symbol
            current_file (str): Path to current trend JSON file
            historical_file (str): Path to historical trend JSON file
            metadata_file (str): Path to metadata JSON file
            collection_name (str): Name of the collection to store in
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logging.info(f"📁 Processing stock trend files for ticker: {ticker}")
            logging.info(f"   - Current file: {current_file}")
            logging.info(f"   - Historical file: {historical_file}")
            logging.info(f"   - Metadata file: {metadata_file}")
            logging.info(f"   - Collection: {collection_name}")
            
            # Load JSON data from files
            current_json = self._load_json_file(current_file, "current trends")
            historical_json = self._load_json_file(historical_file, "historical trends")
            metadata = self._load_json_file(metadata_file, "metadata")
            
            if current_json is None or historical_json is None or metadata is None:
                return False
            
            # Store the data
            return self.store_stock_trend_data(ticker, current_json, historical_json, metadata, collection_name)
            
        except Exception as e:
            logging.error("❌ UNEXPECTED ERROR STORING STOCK TREND FILES:")
            logging.error(f"   - Ticker: {ticker}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            logging.error(f"   - Full traceback:")
            logging.error(traceback.format_exc())
            return False
    
    def _load_json_file(self, file_path: str, file_type: str) -> Optional[Dict]:
        """
        Load JSON data from file with error handling.
        
        Args:
            file_path (str): Path to JSON file
            file_type (str): Type of file for logging
            
        Returns:
            Optional[Dict]: Loaded JSON data or None if failed
        """
        try:
            file_path_obj = Path(file_path)
            
            # Check if file exists
            if not file_path_obj.exists():
                logging.error(f"❌ {file_type.upper()} FILE NOT FOUND:")
                logging.error(f"   - File does not exist: {file_path}")
                return None
            
            # Check file permissions
            if not os.access(file_path_obj, os.R_OK):
                logging.error(f"❌ {file_type.upper()} FILE PERMISSION ERROR:")
                logging.error(f"   - Cannot read file: {file_path}")
                return None
            
            # Read and parse JSON
            with open(file_path_obj, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logging.info(f"✓ Successfully loaded {file_type}: {file_path}")
            logging.info(f"   - Data type: {type(data).__name__}")
            if isinstance(data, dict):
                logging.info(f"   - Keys: {list(data.keys())}")
            
            return data
            
        except json.JSONDecodeError as e:
            logging.error(f"❌ {file_type.upper()} JSON DECODE ERROR:")
            logging.error(f"   - File: {file_path}")
            logging.error(f"   - Error details: {e}")
            return None
        except Exception as e:
            logging.error(f"❌ UNEXPECTED ERROR LOADING {file_type.upper()}:")
            logging.error(f"   - File: {file_path}")
            logging.error(f"   - Error type: {type(e).__name__}")
            logging.error(f"   - Error details: {e}")
            return None
    



def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Create handlers
    file_handler = logging.FileHandler('mongo_storage.log', encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Log startup message
    logging.info("🚀 MongoDB Storage Debug Logger Started")
    logging.info(f"   - Log level: {level.upper()}")
    logging.info(f"   - Log file: mongo_storage.log")
    logging.info(f"   - Console output: Enabled")


def main():
    """Main function to handle command line arguments and execute storage operations."""
    parser = argparse.ArgumentParser(description='Stock Trend DB Agent - Simple ticker download tool')
    
    # Simple ticker input
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., AAPL, TSLA, PLTR)')
    
    # Optional arguments
    parser.add_argument('--force-update', action='store_true', help='Force fresh analysis even if recent data exists')
    parser.add_argument('--list-tickers', action='store_true', help='List all stored stock tickers')
    parser.add_argument('--get-data', action='store_true', help='Retrieve stored data for the ticker')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # PREDEFINED DATABASE CONFIGURATION
    DB_TYPE = "redis"  # Using Redis as default
    DB_COLLECTION = "Stock_Trend_INFOS"
    
    # Redis configuration (predefined)
    REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
    REDIS_PORT = 16376
    REDIS_USERNAME = "default"
    REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    
    try:
        logging.info(f"🔧 INITIALIZING {DB_TYPE.upper()} STORAGE")
        logging.info(f"   - Database type: {DB_TYPE}")
        logging.info(f"   - Collection/Namespace: {DB_COLLECTION}")
        logging.info(f"   - Ticker: {args.ticker.upper()}")
        logging.info(f"   - Log level: {args.log_level}")
        
        # Initialize storage with predefined configuration
        storage = DatabaseStorage(
            db_type=DB_TYPE,
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD
        )
        
        # List stock tickers
        if args.list_tickers:
            logging.info(f"📋 LISTING STOCK TICKERS")
            try:
                tickers = storage.list_stock_tickers(DB_COLLECTION)
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
            logging.info(f"📈 RETRIEVING STOCK TREND DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            
            data = storage.get_stock_trend_data(args.ticker.upper(), DB_COLLECTION)
            if data:
                logging.info("✅ STOCK TREND DATA RETRIEVED SUCCESSFULLY")
                logging.info(f"   - Current trends: {len(data.get('current_trends', {}))}")
                logging.info(f"   - Historical trends: {len(data.get('historical_trends', {}))}")
                logging.info(f"   - Last updated: {data.get('stored_at', 'Unknown')}")
            else:
                logging.warning(f"⚠️ No data found for ticker: {args.ticker.upper()}")
        
        # Download and store ticker data (DEFAULT ACTION)
        else:
            logging.info(f"📥 DOWNLOADING AND STORING TICKER DATA")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            logging.info(f"   - Collection: {DB_COLLECTION}")
            if args.force_update:
                logging.info(f"   - Force update: Enabled")
            
            success = storage.download_and_store_ticker(args.ticker.upper(), DB_COLLECTION, args.force_update)
            if success:
                logging.info("✅ TICKER DATA DOWNLOADED AND STORED SUCCESSFULLY")
            else:
                logging.error("❌ FAILED TO DOWNLOAD AND STORE TICKER DATA")
                sys.exit(1)
        
        # Show collection stats
        logging.info(f"📊 COLLECTION STATISTICS")
        stats = storage.get_collection_stats(DB_COLLECTION)
        logging.info(f"   - Total documents: {stats.get('total_documents', 0)}")
        logging.info(f"   - Database type: {stats.get('database_type', 'Unknown')}")
        if stats.get('tickers'):
            logging.info(f"   - Tickers: {', '.join(stats.get('tickers', []))}")
        
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


def test_update_locking():
    """Test the update locking functionality."""
    import time
    import threading
    
    # Initialize DB storage
    storage = DatabaseStorage(
        db_type="redis",
        host="redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
        port=16376,
        username="default",
        password="rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    )
    
    def simulate_user_request(user_id, ticker):
        """Simulate a user request."""
        print(f"👤 User {user_id} requesting {ticker}...")
        result = storage.update_if_stale_with_lock(ticker, force_update=True)
        print(f"✅ User {user_id} got result: {result}")
        return result
    
    # Test concurrent requests
    print("🧪 Testing concurrent update locking...")
    
    # Simulate two users requesting the same ticker simultaneously
    thread1 = threading.Thread(target=simulate_user_request, args=("user_a", "AAPL"))
    thread2 = threading.Thread(target=simulate_user_request, args=("user_b", "AAPL"))
    
    thread1.start()
    time.sleep(1)  # Small delay to ensure thread1 starts first
    thread2.start()
    
    thread1.join()
    thread2.join()
    
    print("✅ Update locking test completed!")
    storage.close()

if __name__ == "__main__":
    # Example usage:
    # python Stock_Trend_DB_Agent.py --test-locking
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test-locking":
        test_update_locking()
    else:
        main()
    