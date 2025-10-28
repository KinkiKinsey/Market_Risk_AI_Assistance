#!/usr/bin/env python3
"""Test Quant Impact Agent full pipeline for NFLX"""

import sys
import asyncio
import os

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

async def test():
    print("=" * 70)
    print("🚀 TESTING QUANT IMPACT AGENT FULL PIPELINE FOR NFLX")
    print("=" * 70)
    print()
    
    ticker = "NFLX"
    user_id = "test_user"
    
    # Initialize shared clients
    print("Step 1: Initializing shared clients...")
    from shared_clients import shared_clients
    await shared_clients.initialize()
    print("✅ Shared clients initialized\n")
    
    # Run Quant Impact pipeline
    print(f"Step 2: Running Quant Impact pipeline for {ticker}...")
    try:
        from Source_File.Agent_Folder.Sub_Agent_Folder.Quant_Impact_Agent.Quant_Impact_Incremental_Update import run_incremental_update
        
        result = await run_incremental_update(
            ticker=ticker, 
            language="English",
            shared_clients=shared_clients,
            user_id=user_id
        )
        
        print(f"\n✅ Pipeline completed")
        print(f"   Status: {result.get('status')}")
        print(f"   Update type: {result.get('update_type', 'N/A')}")
        
        # Verify data in database
        print(f"\nStep 3: Verifying data in database...")
        from Source_File.database_connection import RedisDatabaseStorage
        db_storage = RedisDatabaseStorage(db_type="stock_trend", shared_clients=shared_clients)
        client = db_storage.redis_client
        
        is_async = hasattr(client, '__class__') and 'aioredis' in str(type(client))
        base_key = f"Quant_Impact_INFOS:{ticker.upper()}"
        required_keys = [
            f"{base_key}:RISK_SHARE",
            f"{base_key}:MACRO_VOLATILITY",
            f"{base_key}:MICRO_VOLATILITY",
            f"{base_key}:IMPACT_METRICS",
            f"{base_key}:MACRO_TOTAL_IMPACT",
            f"{base_key}:MICRO_TOTAL_IMPACT",
            f"{base_key}:FACTOR_IMPACT_METRICS",
            f"{base_key}:FACTOR_TIME_DF",
            f"{base_key}:META_INFO"
        ]
        
        found = 0
        for key in required_keys:
            if is_async:
                exists = await client.exists(key)
            else:
                exists = client.exists(key)
            if exists:
                found += 1
        
        print(f"   ✅ Found: {found}/{len(required_keys)} keys in database")
        
        if found == len(required_keys):
            print(f"\n🎉 SUCCESS! All data stored correctly!")
        else:
            print(f"\n⚠️  Warning: {len(required_keys) - found} keys missing")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await shared_clients.close()
        print(f"\n✅ Test completed")

if __name__ == "__main__":
    asyncio.run(test())

