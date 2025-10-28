#!/usr/bin/env python3
"""
Macro DB Agent
Calls Macro Storage Agent to download data and handles all database operations.
Separates storage logic from database logic completely.
"""

import os
import json
import logging
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union
import redis
import traceback
from pathlib import Path

# Fix import paths for multiprocessing in Streamlit
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# ============================================================================
# CONFIGURATION - Using centralized database_connection module
# ============================================================================

# Import centralized config
try:
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import (
        FRONTEND_REDIS_HOST, FRONTEND_REDIS_PORT, FRONTEND_REDIS_USERNAME, FRONTEND_REDIS_PASSWORD,
        STOCK_TREND_REDIS_HOST, STOCK_TREND_REDIS_PORT, STOCK_TREND_REDIS_USERNAME, STOCK_TREND_REDIS_PASSWORD
    )
except ImportError:
    raise ImportError("config.py is required. Please ensure it exists in the backend directory.")

# ============================================================================
# Import the storage agent (without database code)
# ============================================================================

from Macro_Storage import (
    download_all_indicators,
    prepare_economic_summary,
    generate_llm_prompt,
    deepseek_api_call
)

# COMPLETELY SILENT - No logging output
logging.basicConfig(
    level=logging.CRITICAL,  # Only show critical errors
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.NullHandler()  # No output at all
    ]
)

class MacroDBAgent:
    """
    Macro DB Agent - Handles all database operations and calls storage agent
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = None, redis_password: str = None):
        """
        Initialize Macro DB Agent using centralized database_connection module
        
        Args:
            shared_clients: Shared clients instance for Redis connections (preferred)
            redis_host: Redis host (deprecated - use shared_clients)
            redis_port: Redis port (deprecated - use shared_clients)
            redis_username: Redis username (deprecated - use shared_clients)
            redis_password: Redis password (deprecated - use shared_clients)
        """
        # Import centralized database connection
        from Source_File.database_connection import RedisDatabaseStorage as CentralizedStorage
        
        # Use centralized storage for connection management
        if shared_clients:
            # Use shared connection pool (preferred)
            self.frontend_storage = CentralizedStorage(db_type="frontend", shared_clients=shared_clients)
            self.stock_trend_storage = CentralizedStorage(db_type="stock_trend", shared_clients=shared_clients)
            logging.info("✅ Using shared Redis connections via database_connection")
        else:
            # Fallback to direct connection (but still use database_connection)
            self.frontend_storage = CentralizedStorage(db_type="frontend", shared_clients=None)
            self.stock_trend_storage = CentralizedStorage(db_type="stock_trend", shared_clients=None)
            logging.info("✅ Using direct Redis connections via database_connection")
        
        # Expose clients for backward compatibility
        self.frontend_redis = self.frontend_storage.redis_client
        self.stock_trend_redis = self.stock_trend_storage.redis_client
        
        # Storage keys - PRESERVE EXACT KEY NAMES
        # Frontend Redis keys (user data)
        self.frontend_progress_key = "macro:frontend_progress"
        self.frontend_metadata_key = "macro:frontend_metadata"
        
        # Stock Trend Redis keys - WITH Macro_INFOS PREFIX (preserved)
        self.stock_trend_macro_key = "Macro_INFOS:Macro_Data"
        self.stock_trend_analysis_key = "Macro_INFOS:Macro_Analyst"
        
        print(f"🤖 Macro DB Agent initialized")
        print(f"📊 Frontend Redis: Connected via database_connection")
        print(f"🗄️ Stock Trend Redis: Connected via database_connection")
        print(f"🔑 Database keys: {self.stock_trend_macro_key}, {self.stock_trend_analysis_key}")
        print(f"✅ Connected to both databases!")
    
    def _is_async_redis(self, client) -> bool:
        """Check if Redis client is async (aioredis)"""
        return hasattr(client, '__class__') and 'aioredis' in str(type(client))
    
    async def check_if_update_needed(self, hours_threshold: int = 168) -> bool:  # Macro: 1 week (168 hours)
        """
        Check if macro data update is needed by checking metadata embedded in macro_data
        
        Args:
            hours_threshold: Hours threshold for update (default: 168 = 1 week)
            
        Returns:
            bool: True if update is needed, False otherwise
        """
        try:
            if not self.stock_trend_redis:
                print("⚠️ Stock Trend Redis not connected. Update needed.")
                return True
            
            # Check if macro_data exists and has embedded metadata
            print("🔍 Checking if macro data exists in database...")
            
            # Handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            if is_async:
                data_json = await self.stock_trend_redis.get(self.stock_trend_macro_key)
            else:
                data_json = self.stock_trend_redis.get(self.stock_trend_macro_key)
            if not data_json:
                print("⚠️ No macro data found in database. Update REQUIRED.")
                return True
            
            # Parse data and check embedded metadata
            try:
                data = json.loads(data_json)
                if 'meta_data' not in data:
                    print("⚠️ No metadata found in macro data. Update REQUIRED.")
                    return True
                
                metadata = data['meta_data']
                last_update_time = metadata.get('last_update_time')
                
                if not last_update_time:
                    print("⚠️ No last update time found. Update REQUIRED.")
                    return True
                
                print(f"✅ Macro data exists in database.")
                print(f"📊 Last update: {last_update_time}")
                
                # Check timing rules
                current_time = datetime.now()
                last_update = datetime.fromisoformat(last_update_time)
                hours_since_update = (current_time - last_update).total_seconds() / 3600
                
                print(f"⏰ Hours since update: {hours_since_update:.1f}")
                print(f"⏰ Update threshold: {hours_threshold} hours")
                
                if hours_since_update >= hours_threshold:
                    print(f"⚠️ Update threshold exceeded. Update needed.")
                    return True
                else:
                    print(f"✅ Update not needed yet (threshold: {hours_threshold} hours)")
                    return False
                    
            except json.JSONDecodeError:
                print("⚠️ Invalid JSON in macro data. Update REQUIRED.")
                return True
                
        except Exception as e:
            print(f"⚠️ Error checking update status: {e}. Update needed.")
            return True
    
    async def get_macro_update_status(self) -> Dict[str, Any]:
        """
        Get current status of macro data updates
        
        Returns:
            Dict containing update status information
        """
        try:
            if not self.stock_trend_redis:
                return {
                    'status': 'redis_error',
                    'message': 'Stock Trend Redis connection failed',
                    'last_update': None,
                    'data_range': None,
                    'indicators': None
                }
            
            # Metadata is now embedded in the data file, not separate
            is_async = self._is_async_redis(self.stock_trend_redis)
            if is_async:
                data_json = await self.stock_trend_redis.get(self.stock_trend_macro_key)
            else:
                data_json = self.stock_trend_redis.get(self.stock_trend_macro_key)
            if data_json:
                data = json.loads(data_json)
                metadata_json = json.dumps(data.get('meta_data', {}))
            else:
                metadata_json = None
            
            if not metadata_json:
                return {
                    'status': 'no_data',
                    'message': 'No macro data has been collected yet',
                    'last_update': None,
                    'data_range': None,
                    'indicators': None
                }
            
            metadata = json.loads(metadata_json)
            current_time = datetime.now()
            last_update = datetime.fromisoformat(metadata['last_update_time'])
            hours_since_update = (current_time - last_update).total_seconds() / 3600
            
            status_info = {
                'status': 'up_to_date' if hours_since_update < 24 else 'needs_update',
                'last_update': metadata['last_update_time'],
                'hours_since_update': round(hours_since_update, 1),
                'data_range': metadata['data_range'],
                'indicators': metadata['indicators_downloaded'],
                'total_indicators': metadata['total_indicators'],
                'analysis_storage_key': metadata['analysis_storage_key'],
                'data_quality': metadata['data_quality']
            }
            
            return status_info
            
        except Exception as e:
            return {
                'status': 'error',
                'message': f'Error retrieving update status: {str(e)}',
                'last_update': None,
                'data_range': None,
                'indicators': None
            }
    
    async def store_macro_data(self, all_dfs: Dict, from_date: str, to_date: str, 
                        analysis_result: str) -> bool:
        """
        Store macro data and metadata in Redis database
        
        Args:
            all_dfs: Dictionary of economic indicator dataframes
            from_date: Start date of data range
            to_date: End date of data range
            analysis_result: LLM analysis result
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print(f"🔍 DEBUG: Starting storage process...")
            print(f"🔍 DEBUG: Stock Trend Redis connected: {self.stock_trend_redis is not None}")
            print(f"🔍 DEBUG: Number of dataframes: {len(all_dfs)}")
            print(f"🔍 DEBUG: Analysis length: {len(analysis_result)}")
            
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected. Cannot store data.")
                return False
            
            current_time = datetime.now()
            timestamp = current_time.strftime("%Y%m%d_%H%M%S")
            
            # Use fixed keys - always overwrite previous data
            data_key = self.stock_trend_macro_key
            analysis_key = self.stock_trend_analysis_key
            
            print(f"🔍 DEBUG: Data key: {data_key}")
            print(f"🔍 DEBUG: Analysis key: {analysis_key}")
            
            # Prepare data for storage with embedded metadata
            data_for_storage = {}
            for indicator, df in all_dfs.items():
                # Check if df is a DataFrame or other data type
                if hasattr(df, 'empty') and not df.empty:
                    # Convert dataframe to JSON-serializable format
                    data_for_storage[indicator] = {
                        'data': df.to_dict('records'),
                        'shape': df.shape,
                        'date_range': {
                            'start': df['date'].min().strftime('%Y-%m-%d'),
                            'end': df['date'].max().strftime('%Y-%m-%d')
                        }
                    }
                elif hasattr(df, 'empty') and df.empty:
                    # Empty DataFrame - store as empty
                    data_for_storage[indicator] = {
                        'data': [],
                        'shape': (0, 0),
                        'date_range': {
                            'start': from_date,
                            'end': to_date
                        }
                    }
                else:
                    # Non-DataFrame data (string, dict, etc.) - store as-is
                    data_for_storage[indicator] = {
                        'data': df,
                        'shape': 'N/A',
                        'date_range': {
                            'start': from_date,
                            'end': to_date
                        }
                    }
            
            # Create metadata that will be embedded in both files
            metadata = {
                'last_update_time': current_time.isoformat(),
                'data_range': {
                    'start_date': from_date,
                    'end_date': to_date
                },
                'indicators_downloaded': list(all_dfs.keys()),
                'total_indicators': len(all_dfs),
                'analysis_length': len(analysis_result),
                'update_timestamp': timestamp,
                'data_quality': {
                    'indicators_with_data': len([df for df in all_dfs.values() if hasattr(df, 'empty') and not df.empty]),
                    'total_data_points': sum([len(df) for df in all_dfs.values() if hasattr(df, 'empty') and not df.empty])
                }
            }
            
            # Add metadata to data storage
            data_for_storage['meta_data'] = metadata
            
            print(f"🔍 DEBUG: Data prepared for storage: {len(data_for_storage)} indicators")
            
            # Store economic data
            print(f"🔍 DEBUG: Storing data to Redis...")
            data_json = json.dumps(data_for_storage, default=str)
            print(f"🔍 DEBUG: Data JSON length: {len(data_json)} characters")
            
            # Handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            if is_async:
                result1 = await self.stock_trend_redis.set(data_key, data_json)
                await self.stock_trend_redis.expire(data_key, 30 * 24 * 60 * 60)  # 30 days
            else:
                result1 = self.stock_trend_redis.set(data_key, data_json)
                self.stock_trend_redis.expire(data_key, 30 * 24 * 60 * 60)  # 30 days
            print(f"🔍 DEBUG: Data storage result: {result1}")
            
            # Store LLM analysis with embedded metadata
            print(f"🔍 DEBUG: Storing analysis to Redis...")
            analysis_with_metadata = {
                'analysis': analysis_result,
                'meta_data': metadata  # Same metadata as in data
            }
            analysis_json = json.dumps(analysis_with_metadata, default=str)
            if is_async:
                result2 = await self.stock_trend_redis.set(analysis_key, analysis_json)
                await self.stock_trend_redis.expire(analysis_key, 30 * 24 * 60 * 60)  # 30 days
            else:
                result2 = self.stock_trend_redis.set(analysis_key, analysis_json)
                self.stock_trend_redis.expire(analysis_key, 30 * 24 * 60 * 60)  # 30 days
            print(f"🔍 DEBUG: Analysis storage result: {result2}")
            
            # Metadata is now embedded in both data and analysis files
            print(f"🔍 DEBUG: Metadata embedded in both files")
            
            # Verify storage
            print(f"🔍 DEBUG: Verifying storage...")
            if is_async:
                stored_data = await self.stock_trend_redis.get(data_key)
                stored_analysis = await self.stock_trend_redis.get(analysis_key)
            else:
                stored_data = self.stock_trend_redis.get(data_key)
                stored_analysis = self.stock_trend_redis.get(analysis_key)
            
            print(f"🔍 DEBUG: Stored data exists: {stored_data is not None}")
            print(f"🔍 DEBUG: Stored analysis exists: {stored_analysis is not None}")
            
            # Verify metadata is embedded in both files
            if stored_data and stored_analysis:
                try:
                    data_parsed = json.loads(stored_data)
                    analysis_parsed = json.loads(stored_analysis)
                    
                    data_has_metadata = 'meta_data' in data_parsed
                    analysis_has_metadata = 'meta_data' in analysis_parsed
                    
                    print(f"🔍 DEBUG: Data has embedded metadata: {data_has_metadata}")
                    print(f"🔍 DEBUG: Analysis has embedded metadata: {analysis_has_metadata}")
                    
                    if data_has_metadata and analysis_has_metadata:
                        print(f"✅ Both files have embedded metadata")
                    else:
                        print(f"⚠️ Missing embedded metadata in one or both files")
                        
                except json.JSONDecodeError:
                    print(f"⚠️ Error parsing stored data for metadata verification")
            
            # Clean up any old timestamped keys to maintain clean database
            await self._cleanup_old_keys()
            
            print(f"✅ Macro data stored successfully")
            print(f"📊 Data key: {data_key}")
            print(f"🤖 Analysis key: {analysis_key}")
            print(f"📋 Metadata updated")
            print(f"🧹 Database cleaned - only 2 main keys remain")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to store macro data: {e}")
            logging.error(f"Store macro data error: {traceback.format_exc()}")
            return False
    
    async def retrieve_macro_data(self, data_key: str = None) -> Dict[str, Any]:
        """
        Retrieve macro data from database
        
        Args:
            data_key: Specific data key to retrieve (if None, gets latest)
            
        Returns:
            Dict containing macro data
        """
        try:
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected. Cannot retrieve data.")
                return {}
            
            if not data_key:
                # Use the default data key
                data_key = self.stock_trend_macro_key
            
            # Retrieve data - handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            if is_async:
                data_json = await self.stock_trend_redis.get(data_key)
            else:
                data_json = self.stock_trend_redis.get(data_key)
            if data_json:
                data = json.loads(data_json)
                print(f"✅ Macro data retrieved: {data_key}")
                return data
            else:
                print(f"❌ No data found for key: {data_key}")
                return {}
                
        except Exception as e:
            print(f"❌ Failed to retrieve macro data: {e}")
            logging.error(f"Retrieve macro data error: {traceback.format_exc()}")
            return {}
    
    async def retrieve_macro_analysis(self, analysis_key: str = None) -> str:
        """
        Retrieve LLM analysis from database
        
        Args:
            analysis_key: Specific analysis key to retrieve (if None, gets latest)
            
        Returns:
            str: LLM analysis text
        """
        try:
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected. Cannot retrieve analysis.")
                return ""
            
            if not analysis_key:
                # Use the default analysis key
                analysis_key = self.stock_trend_analysis_key
            
            # Retrieve analysis - handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            if is_async:
                analysis = await self.stock_trend_redis.get(analysis_key)
            else:
                analysis = self.stock_trend_redis.get(analysis_key)
            if analysis:
                print(f"✅ Macro analysis retrieved: {analysis_key}")
                return analysis
            else:
                print(f"❌ No analysis found for key: {analysis_key}")
                return ""
                
        except Exception as e:
            print(f"❌ Failed to retrieve macro analysis: {e}")
            logging.error(f"Retrieve macro analysis error: {traceback.format_exc()}")
            return ""
    
    async def run_macro_update(self) -> bool:
        """
        Main function to run macro data update
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("🚀 MACRO DB AGENT STARTING UPDATE PROCESS...")
        print("=" * 60)
        
        try:
            # Check if update is needed (use 7-day threshold like other macro modules)
            if not await self.check_if_update_needed(hours_threshold=168):
                print("⏳ Update not needed at this time. Exiting.")
                return True
            
            print("✅ Update needed. Proceeding with data collection...")
            
            # Step 1: Call storage agent to download data (NO DATABASE CODE)
            print("📡 Calling Macro Storage Agent to download data...")
            all_dfs, from_date, to_date = download_all_indicators()
            
            if not all_dfs:
                print("❌ No data was downloaded. Exiting.")
                return False
            
            # Step 2: Prepare economic summary (NO DATABASE CODE)
            print("📊 Preparing economic summary...")
            economic_summary = prepare_economic_summary(all_dfs)
            
            # Step 3: Generate LLM prompt (NO DATABASE CODE)
            print("📝 Generating LLM prompt...")
            prompt = generate_llm_prompt(economic_summary)
            
            # Step 4: Call LLM API (NO DATABASE CODE)
            print("🤖 Calling LLM API...")
            analysis_result = deepseek_api_call(prompt)
            
            if not analysis_result:
                print("❌ LLM analysis failed. Exiting.")
                return False
            
            print("✅ LLM analysis completed!")
            
            # Step 5: Store everything in database (DB AGENT ONLY)
            print("💾 Storing data in database...")
            success = await self.store_macro_data(all_dfs, from_date, to_date, analysis_result)
            
            if success:
                print(f"\n🎉 MACRO UPDATE COMPLETE!")
                print(f"📊 Data range: {from_date} to {to_date}")
                print(f"📈 Analysis length: {len(analysis_result)} characters")
                return True
            else:
                print("❌ Database storage failed!")
                return False
                
        except Exception as e:
            print(f"❌ Error in macro update: {e}")
            logging.error(f"Macro update error: {traceback.format_exc()}")
            return False
    
    async def force_macro_update(self) -> bool:
        """
        Force macro data update regardless of timing
        
        Returns:
            bool: True if successful, False otherwise
        """
        print("🔄 FORCING MACRO DATA UPDATE...")
        print("=" * 50)
        
        try:
            # Temporarily override the update check
            print("🚀 MACRO DB AGENT STARTING FORCED UPDATE...")
            print("=" * 60)
            
            # Call storage agent to download data
            print("📡 Calling Macro Storage Agent to download data...")
            all_dfs, from_date, to_date = await download_all_indicators()
            
            if not all_dfs:
                print("❌ No data was downloaded. Exiting.")
                return False
            
            # Prepare economic summary
            print("📊 Preparing economic summary...")
            economic_summary = prepare_economic_summary(all_dfs)
            
            # Generate LLM prompt
            print("📝 Generating LLM prompt...")
            prompt = generate_llm_prompt(economic_summary)
            
            # Call LLM API
            print("🤖 Calling LLM API...")
            analysis_result = deepseek_api_call(prompt)
            
            if not analysis_result:
                print("❌ LLM analysis failed. Exiting.")
                return False
            
            print("✅ LLM analysis completed!")
            
            # Store in database
            print("💾 Storing data in database...")
            success = await self.store_macro_data(all_dfs, from_date, to_date, analysis_result)
            
            if success:
                print(f"\n🎉 FORCED MACRO UPDATE COMPLETE!")
                print(f"📊 Data range: {from_date} to {to_date}")
                print(f"📈 Analysis length: {len(analysis_result)} characters")
                return True
            else:
                print("❌ Database storage failed!")
                return False
                
        except Exception as e:
            print(f"❌ Error in forced update: {e}")
            logging.error(f"Forced update error: {traceback.format_exc()}")
            return False
    
    async def _cleanup_old_keys(self):
        """
        Clean up old keys to maintain clean database
        Only keeps the 2 main keys: Macro_INFOS:Macro_Data and Macro_INFOS:Macro_Analyst
        """
        try:
            if not self.stock_trend_redis:
                return
            
            print("🧹 Cleaning up old keys...")
            
            # Handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            
            # Get all keys that match our patterns
            if is_async:
                all_keys = await self.stock_trend_redis.keys("*macro*")
                macro_infos_keys = await self.stock_trend_redis.keys("*Macro_INFOS*")
            else:
                all_keys = self.stock_trend_redis.keys("*macro*")
                macro_infos_keys = self.stock_trend_redis.keys("*Macro_INFOS*")
            
            # Define the keys we want to keep
            keep_keys = [
                self.stock_trend_macro_key,      # Macro_INFOS:Macro_Data
                self.stock_trend_analysis_key    # Macro_INFOS:Macro_Analyst
            ]
            
            deleted_count = 0
            
            # Delete any keys that don't match our Macro_INFOS format
            for key in all_keys + macro_infos_keys:
                if key not in keep_keys:
                    print(f"🗑️ Deleting old key: {key}")
                    if is_async:
                        await self.stock_trend_redis.delete(key)
                    else:
                        self.stock_trend_redis.delete(key)
                    deleted_count += 1
            
            if deleted_count > 0:
                print(f"✅ Cleaned up {deleted_count} old keys")
            else:
                print("✅ No old keys to clean up")
                
            # Verify only our 2 main keys remain
            if is_async:
                remaining_keys = await self.stock_trend_redis.keys("*Macro_INFOS*")
            else:
                remaining_keys = self.stock_trend_redis.keys("*Macro_INFOS*")
            print(f"📋 Remaining keys: {remaining_keys}")
            
        except Exception as e:
            print(f"⚠️ Error during cleanup: {e}")
            logging.error(f"Cleanup error: {traceback.format_exc()}")
    
    async def verify_database_structure(self):
        """
        Verify that the database contains exactly the expected structure
        """
        try:
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected.")
                return False
            
            print("\n🔍 VERIFYING DATABASE STRUCTURE")
            print("=" * 50)
            
            # Handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            
            # Check for our 2 main keys
            if is_async:
                data_exists = await self.stock_trend_redis.exists(self.stock_trend_macro_key)
                analysis_exists = await self.stock_trend_redis.exists(self.stock_trend_analysis_key)
            else:
                data_exists = self.stock_trend_redis.exists(self.stock_trend_macro_key)
                analysis_exists = self.stock_trend_redis.exists(self.stock_trend_analysis_key)
            
            print(f"📊 {self.stock_trend_macro_key}: {'✅' if data_exists else '❌'}")
            print(f"🤖 {self.stock_trend_analysis_key}: {'✅' if analysis_exists else '❌'}")
            
            # Check for embedded metadata in both files
            if data_exists and analysis_exists:
                try:
                    if is_async:
                        data_json = await self.stock_trend_redis.get(self.stock_trend_macro_key)
                        analysis_json = await self.stock_trend_redis.get(self.stock_trend_analysis_key)
                    else:
                        data_json = self.stock_trend_redis.get(self.stock_trend_macro_key)
                        analysis_json = self.stock_trend_redis.get(self.stock_trend_analysis_key)
                    
                    data_parsed = json.loads(data_json)
                    analysis_parsed = json.loads(analysis_json)
                    
                    data_has_metadata = 'meta_data' in data_parsed
                    analysis_has_metadata = 'meta_data' in analysis_parsed
                    
                    print(f"📊 {self.stock_trend_macro_key} has metadata: {'✅' if data_has_metadata else '❌'}")
                    print(f"🤖 {self.stock_trend_analysis_key} has metadata: {'✅' if analysis_has_metadata else '❌'}")
                    
                    if data_has_metadata and analysis_has_metadata:
                        print(f"✅ Both files have embedded metadata")
                    else:
                        print(f"⚠️ Missing embedded metadata in one or both files")
                        
                except json.JSONDecodeError:
                    print(f"⚠️ Error parsing files for metadata verification")
            
            # Check for any other macro keys
            # Note: verify_database_structure is async, so we can use await
            is_async = self._is_async_redis(self.stock_trend_redis)
            if is_async:
                all_macro_keys = await self.stock_trend_redis.keys("*macro*")
                all_macro_infos_keys = await self.stock_trend_redis.keys("*Macro_INFOS*")
            else:
                all_macro_keys = self.stock_trend_redis.keys("*macro*")
                all_macro_infos_keys = self.stock_trend_redis.keys("*Macro_INFOS*")
            
            unexpected_keys = []
            for key in all_macro_keys + all_macro_infos_keys:
                if key not in [self.stock_trend_macro_key, self.stock_trend_analysis_key]:
                    unexpected_keys.append(key)
            
            if unexpected_keys:
                print(f"\n⚠️ Unexpected keys found:")
                for key in unexpected_keys:
                    print(f"   - {key}")
                print(f"\n🧹 Run cleanup to remove these keys")
                return False
            else:
                print(f"\n✅ Database structure is clean - only expected keys exist")
                return True
                
        except Exception as e:
            print(f"❌ Error verifying database structure: {e}")
            return False
    
    def force_database_cleanup(self):
        """
        Force cleanup of database to remove all old keys and ensure clean structure
        """
        try:
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected.")
                return False
            
            print("\n🧹 FORCING DATABASE CLEANUP")
            print("=" * 50)
            
            # Get all keys that might be old
            all_keys = self.stock_trend_redis.keys("*macro*")
            all_macro_infos_keys = self.stock_trend_redis.keys("*Macro_INFOS*")
            
            print(f"🔍 Found {len(all_keys)} keys with 'macro' in name")
            print(f"🔍 Found {len(all_macro_infos_keys)} keys with 'Macro_INFOS' in name")
            
            # Define the keys we want to keep
            keep_keys = [
                self.stock_trend_macro_key,      # Macro_INFOS:Macro_Data
                self.stock_trend_analysis_key    # Macro_INFOS:Macro_Analyst
            ]
            
            deleted_count = 0
            
            # Delete ALL keys except our 2 main ones
            for key in all_keys + all_macro_infos_keys:
                if key not in keep_keys:
                    print(f"🗑️ Deleting key: {key}")
                    self.stock_trend_redis.delete(key)
                    deleted_count += 1
            
            print(f"✅ Cleaned up {deleted_count} keys")
            
            # Verify structure
            return self.verify_database_structure()
            
        except Exception as e:
            print(f"❌ Error during force cleanup: {e}")
            logging.error(f"Force cleanup error: {traceback.format_exc()}")
            return False

    def list_all_macro_keys(self) -> List[str]:
        """
        List all macro-related keys in the Stock Trend Redis database
        
        Returns:
            List of all macro keys found
        """
        try:
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected. Cannot list keys.")
                return []
            
            print("🔍 Searching for macro data keys in database...")
            
            # Get all keys that match our macro patterns
            all_keys = self.stock_trend_redis.keys("*macro*")
            macro_infos_keys = self.stock_trend_redis.keys("*Macro_INFOS*")
            
            print(f"🔍 Found {len(all_keys)} keys with 'macro' in name")
            print(f"🔍 Found {len(macro_infos_keys)} keys with 'Macro_INFOS' in name")
            
            # List all macro keys
            if all_keys:
                print("\n📋 Macro keys found:")
                for key in sorted(all_keys):
                    print(f"   - {key}")
            else:
                print("❌ No macro keys found!")
            
            # List all Macro_INFOS keys
            if macro_infos_keys:
                print("\n📋 Macro_INFOS keys found:")
                for key in sorted(macro_infos_keys):
                    print(f"   - {key}")
            else:
                print("❌ No Macro_INFOS keys found!")
            
            return all_keys
            
        except Exception as e:
            print(f"❌ Error listing macro keys: {e}")
            return []
    
    async def check_database_contents(self):
        """
        Debug function to check what's actually in the database
        """
        print("\n🔍 DATABASE CONTENTS CHECK")
        print("=" * 50)
        
        try:
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected.")
                return
            
            # Handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            
            # Check embedded metadata in macro_data
            print("📋 Checking embedded metadata...")
            if is_async:
                data_json = await self.stock_trend_redis.get(self.stock_trend_macro_key)
            else:
                data_json = self.stock_trend_redis.get(self.stock_trend_macro_key)
            if data_json:
                try:
                    data = json.loads(data_json)
                    if 'meta_data' in data:
                        metadata = data['meta_data']
                        print(f"✅ Embedded metadata found: {metadata}")
                        
                        # Check data size
                        data_size = len(data_json)
                        print(f"📊 Data size: {data_size} characters")
                        
                        # Check analysis
                        if is_async:
                            analysis_exists = await self.stock_trend_redis.exists(self.stock_trend_analysis_key)
                        else:
                            analysis_exists = self.stock_trend_redis.exists(self.stock_trend_analysis_key)
                        print(f"🤖 Analysis key '{self.stock_trend_analysis_key}' exists: {analysis_exists}")
                        
                        if analysis_exists:
                            if is_async:
                                analysis_json = await self.stock_trend_redis.get(self.stock_trend_analysis_key)
                            else:
                                analysis_json = self.stock_trend_redis.get(self.stock_trend_analysis_key)
                            analysis_size = len(analysis_json)
                            print(f"🤖 Analysis size: {analysis_size} characters")
                    else:
                        print("❌ No embedded metadata found in macro_data!")
                except json.JSONDecodeError:
                    print("❌ Error parsing macro_data JSON!")
            else:
                print("❌ No macro_data found!")
            
            # List all keys
            self.list_all_macro_keys()
            
        except Exception as e:
            print(f"❌ Error checking database contents: {e}")
            logging.error(f"Database contents check error: {traceback.format_exc()}")

    async def show_actual_macro_data(self):
        """
        Actually retrieve and display the macro data to see what's really there
        """
        print("\n🔍 SHOWING ACTUAL MACRO DATA")
        print("=" * 50)
        
        try:
            if not self.stock_trend_redis:
                print("❌ Stock Trend Redis not connected.")
                return
            
            # Handle both sync and async Redis clients
            is_async = self._is_async_redis(self.stock_trend_redis)
            
            # Get the actual data directly
            print(f"\n📊 Retrieving data from key: {self.stock_trend_macro_key}")
            if is_async:
                data_json = await self.stock_trend_redis.get(self.stock_trend_macro_key)
            else:
                data_json = self.stock_trend_redis.get(self.stock_trend_macro_key)
            
            if data_json:
                print(f"✅ Data found! Size: {len(data_json)} characters")
                try:
                    data = json.loads(data_json)
                    print(f"📊 Data structure: {list(data.keys())}")
                    
                    # Show metadata first
                    if 'meta_data' in data:
                        metadata = data['meta_data']
                        print(f"\n📋 Embedded Metadata:")
                        print(f"   Last update: {metadata.get('last_update_time', 'Unknown')}")
                        print(f"   Data range: {metadata.get('data_range', 'Unknown')}")
                        print(f"   Indicators: {metadata.get('indicators_downloaded', 'Unknown')}")
                    
                    # Show first few records of each indicator
                    for indicator, info in data.items():
                        if indicator != 'meta_data':  # Skip metadata
                            print(f"\n📈 {indicator}:")
                            print(f"   Shape: {info.get('shape', 'Unknown')}")
                            print(f"   Date range: {info.get('date_range', 'Unknown')}")
                            
                            # Show first record
                            if 'data' in info and info['data']:
                                first_record = info['data'][0]
                                print(f"   First record: {first_record}")
                except json.JSONDecodeError:
                    print("❌ Error parsing data JSON!")
            else:
                print(f"❌ No data found at key: {self.stock_trend_macro_key}")
            
            # Get the analysis
            print(f"\n🤖 Retrieving analysis from key: {self.stock_trend_analysis_key}")
            if is_async:
                analysis_json = await self.stock_trend_redis.get(self.stock_trend_analysis_key)
            else:
                analysis_json = self.stock_trend_redis.get(self.stock_trend_analysis_key)
            
            if analysis_json:
                print(f"✅ Analysis found! Size: {len(analysis_json)} characters")
                try:
                    analysis_data = json.loads(analysis_json)
                    if 'analysis' in analysis_data:
                        analysis_text = analysis_data['analysis']
                        print(f"📝 Analysis preview: {analysis_text[:200]}...")
                        
                        # Show embedded metadata
                        if 'meta_data' in analysis_data:
                            metadata = analysis_data['meta_data']
                            print(f"\n📋 Analysis Metadata:")
                            print(f"   Last update: {metadata.get('last_update_time', 'Unknown')}")
                            print(f"   Analysis length: {metadata.get('analysis_length', 'Unknown')}")
                    else:
                        print(f"📝 Analysis preview: {analysis_json[:200]}...")
                except json.JSONDecodeError:
                    print(f"📝 Analysis preview: {analysis_json[:200]}...")
            else:
                print(f"❌ No analysis found at key: {self.stock_trend_analysis_key}")
                
        except Exception as e:
            print(f"❌ Error showing macro data: {e}")
            logging.error(f"Show macro data error: {traceback.format_exc()}")

def main():
    """
    Main execution function
    """
    print("🚀 MACRO DB AGENT - MAIN EXECUTION")
    print("=" * 50)
    
    try:
        # Initialize DB agent with StockTrend Redis (same as StockTrend system)
        print("🔌 Connecting to StockTrend Redis...")
        db_agent = MacroDBAgent()
        
        # Check what's actually in the database
        db_agent.check_database_contents()
        
        # Verify database structure
        db_agent.verify_database_structure()
        
        # Show the actual macro data
        db_agent.show_actual_macro_data()
        
        # Run macro update (will check if needed first)
        success = db_agent.run_macro_update()
        
        if success:
            print("\n✅ Macro DB Agent completed successfully!")
            print("💡 Macro data now stored in StockTrend database!")
        else:
            print("\n❌ Macro DB Agent failed!")
            
    except Exception as e:
        print(f"❌ Main execution failed: {e}")
        logging.error(f"Main execution error: {traceback.format_exc()}")

def usage_example():
    """
    Example of how to use the Macro DB Agent with the new clean database structure
    """
    print("\n📚 MACRO DB AGENT USAGE EXAMPLE")
    print("=" * 50)
    
    try:
        # Initialize the agent
        agent = MacroDBAgent()
        
        # Option 1: Force cleanup first (if you have old keys)
        print("\n🧹 Option 1: Force cleanup old database structure")
        agent.force_database_cleanup()
        
        # Option 2: Verify current structure
        print("\n🔍 Option 2: Verify current database structure")
        agent.verify_database_structure()
        
        # Option 3: Run normal update (will auto-cleanup)
        print("\n🚀 Option 3: Run normal macro update")
        success = agent.run_macro_update()
        
        if success:
            print("✅ Update completed successfully!")
            # Verify final structure
            agent.verify_database_structure()
        else:
            print("❌ Update failed!")
            
    except Exception as e:
        print(f"❌ Usage example failed: {e}")

if __name__ == "__main__":
    # Uncomment the line below to run the usage example instead of main
    # usage_example()
    
    main()
