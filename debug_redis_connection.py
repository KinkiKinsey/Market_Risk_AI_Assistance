#!/usr/bin/env python3
"""
Debug script to check Redis connection and data for Stock Trend Agent
"""

import asyncio
import redis
import json
from datetime import datetime

async def debug_redis_connection():
    """Debug Redis connection and data availability"""
    
    print("🔍 DEBUGGING REDIS CONNECTION AND DATA")
    print("=" * 50)
    
    # Redis configuration
    redis_host = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
    redis_port = 16376
    redis_username = "default"
    redis_password = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    
    try:
        # Connect to Redis
        print(f"🔌 Connecting to Redis: {redis_host}:{redis_port}")
        redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            username=redis_username,
            password=redis_password,
            decode_responses=True
        )
        
        # Test connection
        redis_client.ping()
        print("✅ Redis connection successful!")
        
        # Check for CRWV data
        ticker = "CRWV"
        collection_name = "stock_trends"
        redis_key = f"{collection_name}:{ticker.upper()}_trends"
        
        print(f"\n🔍 Checking for data with key: {redis_key}")
        
        # Get data
        data_str = redis_client.get(redis_key)
        
        if data_str:
            print("✅ Data found!")
            data = json.loads(data_str)
            
            print(f"📊 Data structure:")
            print(f"   - Keys: {list(data.keys())}")
            print(f"   - Current trends: {len(data.get('current_trends', {}))}")
            print(f"   - Historical trends: {len(data.get('historical_trends', {}))}")
            print(f"   - Stored at: {data.get('stored_at', 'Unknown')}")
            
            # Check data freshness
            stored_at = data.get('stored_at')
            if stored_at:
                try:
                    if isinstance(stored_at, str):
                        stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                    else:
                        stored_datetime = stored_at
                    
                    hours_since_update = (datetime.now() - stored_datetime).total_seconds() / 3600
                    print(f"⏰ Data age: {hours_since_update:.1f} hours")
                    
                    if hours_since_update < 24:
                        print("✅ Data is FRESH (< 24 hours)")
                    else:
                        print("❌ Data is STALE (> 24 hours)")
                        
                except Exception as e:
                    print(f"⚠️ Error parsing timestamp: {e}")
            
        else:
            print("❌ No data found!")
            
            # Check what keys exist
            print(f"\n🔍 Checking for keys with pattern: {collection_name}:*")
            pattern = f"{collection_name}:*"
            keys = redis_client.keys(pattern)
            print(f"📋 Found {len(keys)} keys:")
            for key in keys[:10]:  # Show first 10 keys
                print(f"   - {key}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_redis_connection())
