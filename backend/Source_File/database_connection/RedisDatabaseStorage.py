import redis
import json
import pandas as pd
from typing import Any, Dict, List, Union, Optional
import os
from datetime import datetime
import sys

# Import centralized config
try:
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import (
        FRONTEND_REDIS_HOST, FRONTEND_REDIS_PORT, FRONTEND_REDIS_USERNAME, FRONTEND_REDIS_PASSWORD,
        STOCK_TREND_REDIS_HOST, STOCK_TREND_REDIS_PORT, STOCK_TREND_REDIS_USERNAME, STOCK_TREND_REDIS_PASSWORD
    )
except ImportError:
    raise ImportError("config.py is required. Please ensure it exists in the backend directory.")

class RedisDatabaseStorage:
    """Clean Redis database storage functions for JSON, Text, and CSV data"""
    
    def __init__(self, db_type: str = "stock_trend", shared_clients=None):
        """
        Initialize Redis connection using centralized config
        
        Args:
            db_type (str): "frontend" or "stock_trend" (default: "stock_trend")
            shared_clients: Optional shared clients pool for connection pooling
        """
        self.db_type = db_type.lower()
        
        if shared_clients:
            # Use shared connection pool (preferred)
            if self.db_type == "frontend":
                self.redis_client = shared_clients.get_frontend_redis()
            else:
                self.redis_client = shared_clients.get_stock_trend_redis()
        else:
            # Direct connection (fallback) - use config.py
            if self.db_type == "frontend":
                host = FRONTEND_REDIS_HOST
                port = FRONTEND_REDIS_PORT
                username = FRONTEND_REDIS_USERNAME
                password = FRONTEND_REDIS_PASSWORD
            else:
                host = STOCK_TREND_REDIS_HOST
                port = STOCK_TREND_REDIS_PORT
                username = STOCK_TREND_REDIS_USERNAME
                password = STOCK_TREND_REDIS_PASSWORD
            
            if not host or not port:
                raise ValueError(f"Redis connection parameters not set in config.env for {self.db_type}")
            
            self.redis_client = redis.Redis(
                host=host,
                port=port,
                decode_responses=True,
                username=username,
                password=password
            )
            self.redis_client.ping()
    
    def _create_key_path(self, database_name: str, *folder_names: str) -> str:
        """Create Redis key path with nested folder structure"""
        path_parts = [database_name] + list(folder_names)
        return ":".join(path_parts)

    def store_json(self, result: Any, key_path: str) -> Dict[str, str]:
        """Store JSON data in Redis with simple key"""
        if isinstance(result, (dict, list)):
            json_data = json.dumps(result, indent=2)
        else:
            json_data = json.dumps({"data": result}, indent=2)
        
        self.redis_client.set(key_path, json_data)
        self.redis_client.expire(key_path, 86400 * 7)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        return {
            "operation": "store_json",
            "key": key_path,
            "size_bytes": len(json_data.encode('utf-8')),
            "timestamp": timestamp
        }
    
    def get_json(self, key_path: str) -> Any:
        """Retrieve JSON data from Redis"""
        data = self.redis_client.get(key_path)
        if not data:
            return {"error": "No data found"}
        return json.loads(data)
    
    def delete_json(self, key_path: str) -> bool:
        """Delete JSON data from Redis"""
        return self.redis_client.delete(key_path) > 0

    def redis_database_text(self, result: Any, database_name: str, *folder_names: str) -> Dict[str, str]:
        """Store any data as text in Redis with nested folder structure"""
        key_prefix = self._create_key_path(database_name, *folder_names)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"{key_prefix}:text:{timestamp}"
        
        if isinstance(result, str):
            text_data = result
        elif isinstance(result, dict):
            text_data = "\n".join([f"{k}: {v}" for k, v in result.items()])
        else:
            text_data = str(result)
        
        self.redis_client.set(key, text_data)
        self.redis_client.expire(key, 86400 * 7)
        
        return {
            "operation": "redis_database_text",
            "key": key,
            "size_bytes": len(text_data.encode('utf-8')),
            "timestamp": timestamp,
            "folder_path": ":".join([database_name] + list(folder_names))
        }

    def redis_database_csv(self, result: Any, database_name: str, *folder_names: str) -> Dict[str, str]:
        """Store data as CSV in Redis with nested folder structure"""
        key_prefix = self._create_key_path(database_name, *folder_names)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        key = f"{key_prefix}:csv:{timestamp}"
        
        if isinstance(result, pd.DataFrame):
            csv_data = result.to_csv(index=False)
        elif isinstance(result, dict):
            if all(isinstance(v, (dict, list)) for v in result.values()):
                df = pd.DataFrame(result)
            else:
                df = pd.DataFrame([result])
            csv_data = df.to_csv(index=False)
        elif isinstance(result, list):
            df = pd.DataFrame(result)
            csv_data = df.to_csv(index=False)
        else:
            csv_data = "data\n" + str(result) + "\n"
        
        self.redis_client.set(key, csv_data)
        self.redis_client.expire(key, 86400 * 7)
        
        return {
            "operation": "redis_database_csv",
            "key": key,
            "size_bytes": len(csv_data.encode('utf-8')),
            "timestamp": timestamp,
            "folder_path": ":".join([database_name] + list(folder_names))
        }

    def get_stored_data(self, database_name: str, *folder_names: str, data_type: str = "json") -> Any:
        """Retrieve data from Redis storage (legacy method for compatibility)"""
        key_path = self._create_key_path(database_name, *folder_names)
        
        # Try direct key first (for new structure)
        direct_key = f"{key_path}:{data_type}"
        direct_data = self.redis_client.get(direct_key)
        if direct_data:
            if data_type == "json":
                return json.loads(direct_data)
            elif data_type == "csv":
                return pd.read_csv(pd.io.common.StringIO(direct_data))
            else:
                return direct_data
        
        # Try key without data_type suffix (for LLM_Trend_Analyst_Result)
        if data_type == "json":
            direct_key_no_suffix = key_path
            direct_data_no_suffix = self.redis_client.get(direct_key_no_suffix)
            if direct_data_no_suffix:
                return json.loads(direct_data_no_suffix)
        
        # Fallback to pattern matching (for old structure)
        pattern = f"{key_path}:{data_type}:*"
        keys = self.redis_client.keys(pattern)
        
        if not keys:
            return {"error": "No data found"}
        
        latest_key = sorted(keys)[-1]
        data = self.redis_client.get(latest_key)
        
        if data_type == "json":
            return json.loads(data)
        elif data_type == "csv":
            return pd.read_csv(pd.io.common.StringIO(data))
        else:
            return data

    def list_stored_items(self, database_name: str, *folder_names: str) -> List[str]:
        """List all stored items in a folder"""
        pattern = f"{':'.join([database_name] + list(folder_names))}:*"
        keys = self.redis_client.keys(pattern)
        return [key.split(f":{':'.join([database_name] + list(folder_names))}:")[-1] for key in keys]
    
    def key_exists(self, key_path: str) -> bool:
        """Check if a key exists in Redis"""
        return self.redis_client.exists(key_path) > 0

# Clean function wrappers for easy usage
def redis_database_json(result: Any, database_name: str, *folder_names: str, db_type: str = "stock_trend", shared_clients=None) -> Dict[str, str]:
    """Clean function to store JSON data in Redis"""
    storage = RedisDatabaseStorage(db_type=db_type, shared_clients=shared_clients)
    return storage.store_json(result, storage._create_key_path(database_name, *folder_names))

def redis_database_text(result: Any, database_name: str, *folder_names: str, db_type: str = "stock_trend", shared_clients=None) -> Dict[str, str]:
    """Clean function to store text data in Redis"""
    storage = RedisDatabaseStorage(db_type=db_type, shared_clients=shared_clients)
    return storage.redis_database_text(result, database_name, *folder_names)

def redis_database_csv(result: Any, database_name: str, *folder_names: str, db_type: str = "stock_trend", shared_clients=None) -> Dict[str, str]:
    """Clean function to store CSV data in Redis"""
    storage = RedisDatabaseStorage(db_type=db_type, shared_clients=shared_clients)
    return storage.redis_database_csv(result, database_name, *folder_names)
