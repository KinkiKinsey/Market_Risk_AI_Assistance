"""
Quant Impact DB Agent - Simple Wrapper

This agent provides a clean interface to:
1. Run the Storage Agent to generate 7 datasets
2. Automatically store them in Redis under Quant_Impact_INFOS:{ticker}
3. Retrieve the 7 datasets when needed

Usage:
    from Quant_Impact_DB_Agent import QuantImpactDBAgent
    from shared_clients import shared_clients
    
    # Initialize
    await shared_clients.initialize()
    db_agent = QuantImpactDBAgent(shared_clients=shared_clients)
    
    # Generate and store 7 datasets
    result = await db_agent.generate_and_store(ticker="AAPL", language="English")
    
    # Retrieve 7 datasets
    datasets = db_agent.retrieve_datasets(ticker="AAPL")
"""

import asyncio
import sys
from typing import Dict, Any, Tuple, Optional
import pandas as pd
from datetime import datetime

# Import the Storage Agent
import sys
from pathlib import Path
parent_dir = Path(__file__).parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from Quant_Impact_Agent.Quant_Impact_Storage_Agent import QuantImpactStorageAgent

class QuantImpactDBAgent:
    """
    Simple DB Agent that wraps the Storage Agent for easy use
    
    Responsibilities:
    - Call Storage Agent to generate 7 datasets
    - Ensure datasets are stored in Redis
    - Provide easy retrieval interface
    """
    
    def __init__(self, shared_clients=None):
        """
        Initialize the DB Agent
        
        Args:
            shared_clients: Shared clients for Redis and LLM operations
        """
        if not shared_clients:
            raise ValueError("shared_clients is required - cannot use hardcoded Redis connections")
        
        self.shared_clients = shared_clients
        # Storage agent will be initialized with user_id when needed
        self.storage_agent = None
    
    async def generate_and_store(
        self,
        ticker: str,
        user_id: str,
        market_ticker: str = "SPY",
        risk_free_rate: float = 0.025,
        period_days: int = 252
    ) -> Dict[str, Any]:
        """
        Generate all 7 datasets and store them in Redis
        
        This is the main function you should use. It:
        1. Runs the complete Storage Agent pipeline
        2. Generates all 7 datasets (in English only)
        3. Stores them in Redis under Quant_Impact_INFOS:{ticker}
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL')
            user_id: User ID for database storage (required)
            market_ticker: Market benchmark (default: 'SPY')
            risk_free_rate: Annual risk-free rate (default: 2.5%)
            period_days: Number of trading days (default: 252)
        
        Returns:
            dict: Result with status and all 7 datasets
                {
                    "status": "success",
                    "ticker": "AAPL",
                    "risk_share_index": {...},
                    "macro_volatility_df": DataFrame,
                    "micro_volatility_df": DataFrame,
                    "impact_metrics_df": DataFrame,
                    "macro_total_impact_df": DataFrame,
                    "micro_total_impact_df": DataFrame,
                    "Factor_Risk_Reward": DataFrame,
                    "meta_info": {...},
                    "storage_keys": [...]
                }
        """
        print("=" * 70)
        print(f"🚀 QUANT IMPACT DB AGENT - GENERATE & STORE")
        print("=" * 70)
        print(f"📊 Ticker: {ticker}")
        print(f"🌐 Language: English (Default)")
        print(f"⏰ Start: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print()
        
        try:
            # Initialize storage agent with user_id if not already done
            if not self.storage_agent:
                if not user_id:
                    raise ValueError("user_id is required for generate_and_store")
                self.storage_agent = QuantImpactStorageAgent(shared_clients=self.shared_clients, user_id=user_id)
            
            # Run the Storage Agent pipeline (always English)
            print("🔄 Running Storage Agent pipeline...")
            result = await self.storage_agent.process_quant_impact_analysis(
                ticker=ticker,
                language="English",
                market_ticker=market_ticker,
                risk_free_rate=risk_free_rate,
                period_days=period_days
            )
            
            if result.get("status") == "success":
                print()
                print("=" * 70)
                print("✅ SUCCESS - ALL 7 DATASETS GENERATED & STORED!")
                print("=" * 70)
                
                # Show storage location
                ticker_upper = ticker.upper()
                print(f"\n📦 Storage Location in Redis:")
                print(f"   Base Key: Quant_Impact_INFOS:{ticker_upper}")
                print(f"\n   Datasets stored as:")
                print(f"   1. Quant_Impact_INFOS:{ticker_upper}:RISK_SHARE")
                print(f"   2. Quant_Impact_INFOS:{ticker_upper}:MACRO_VOLATILITY")
                print(f"   3. Quant_Impact_INFOS:{ticker_upper}:MICRO_VOLATILITY")
                print(f"   4. Quant_Impact_INFOS:{ticker_upper}:IMPACT_METRICS")
                print(f"   5. Quant_Impact_INFOS:{ticker_upper}:MACRO_TOTAL_IMPACT")
                print(f"   6. Quant_Impact_INFOS:{ticker_upper}:MICRO_TOTAL_IMPACT")
                print(f"   7. Quant_Impact_INFOS:{ticker_upper}:FACTOR_IMPACT_METRICS")
                print(f"   8. Quant_Impact_INFOS:{ticker_upper}:META_INFO")
                
                # Add storage keys to result
                result["storage_keys"] = [
                    f"Quant_Impact_INFOS:{ticker_upper}:RISK_SHARE",
                    f"Quant_Impact_INFOS:{ticker_upper}:MACRO_VOLATILITY",
                    f"Quant_Impact_INFOS:{ticker_upper}:MICRO_VOLATILITY",
                    f"Quant_Impact_INFOS:{ticker_upper}:IMPACT_METRICS",
                    f"Quant_Impact_INFOS:{ticker_upper}:MACRO_TOTAL_IMPACT",
                    f"Quant_Impact_INFOS:{ticker_upper}:MICRO_TOTAL_IMPACT",
                    f"Quant_Impact_INFOS:{ticker_upper}:FACTOR_IMPACT_METRICS",
                    f"Quant_Impact_INFOS:{ticker_upper}:META_INFO"
                ]
                
                print(f"\n⏰ Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print("=" * 70)
                
                return result
            else:
                print()
                print("=" * 70)
                print("❌ FAILED TO GENERATE DATASETS")
                print("=" * 70)
                print(f"Status: {result.get('status')}")
                print(f"Error: {result.get('error', 'Unknown error')}")
                print("=" * 70)
                return result
                
        except Exception as e:
            print()
            print("=" * 70)
            print("❌ ERROR IN DB AGENT")
            print("=" * 70)
            print(f"Error: {e}")
            print("=" * 70)
            
            import traceback
            traceback.print_exc()
            
            return {
                "status": "error",
                "ticker": ticker,
                "error": str(e)
            }
    
    async def retrieve_datasets(self, ticker: str, user_id: str = None) -> Dict[str, Any]:
        """
        Retrieve the 7 datasets from Redis for a given ticker
        
        Args:
            ticker: Stock ticker symbol
            user_id: User ID for initializing storage agent if needed
        
        Returns:
            dict: Dictionary containing all 7 datasets
                {
                    "status": "success",
                    "ticker": "AAPL",
                    "risk_share_index": {...},
                    "macro_volatility_df": DataFrame,
                    "micro_volatility_df": DataFrame,
                    "impact_metrics_df": DataFrame,
                    "macro_total_impact_df": DataFrame,
                    "micro_total_impact_df": DataFrame,
                    "Factor_Risk_Reward": DataFrame,
                    "meta_info": {...}
                }
        """
        try:
            # Initialize storage agent if needed
            if not self.storage_agent:
                if not user_id:
                    raise ValueError("user_id is required for retrieve_datasets")
                self.storage_agent = QuantImpactStorageAgent(shared_clients=self.shared_clients, user_id=user_id)
            
            print(f"📥 Retrieving datasets for {ticker} from Redis...")
            
            result = await self.storage_agent.retrieve_8_datasets_from_csv(ticker)
            
            if result and len(result) > 0:
                print(f"✅ Retrieved {len(result)} items for {ticker}")
                result['status'] = 'success'
                result['ticker'] = ticker.upper()
                return result
            else:
                print(f"❌ No data found for {ticker}")
                return {"status": "not_found", "ticker": ticker}
                
        except Exception as e:
            print(f"❌ Error retrieving data for {ticker}: {e}")
            return {"status": "error", "ticker": ticker, "error": str(e)}
    
    async def check_data_exists(self, ticker: str, user_id: str = None) -> bool:
        """
        Check if data exists in Redis for a ticker
        
        Args:
            ticker: Stock ticker symbol
            user_id: User ID for initializing storage agent if needed
        
        Returns:
            bool: True if data exists, False otherwise
        """
        try:
            # Initialize storage agent if needed
            if not self.storage_agent:
                # For checking existence, we can use a minimal user_id if not provided
                # since we're just reading, not writing
                if not user_id:
                    user_id = "temp_check_user"
                self.storage_agent = QuantImpactStorageAgent(shared_clients=self.shared_clients, user_id=user_id)
            
            ticker = ticker.upper()
            base_key = f"Quant_Impact_INFOS:{ticker}:META_INFO"
            
            is_async = self.storage_agent._is_async_redis(self.storage_agent.redis_client)
            if is_async:
                data = await self.storage_agent.redis_client.get(base_key)
            else:
                data = self.storage_agent.redis_client.get(base_key)
            
            return data is not None
            
        except Exception as e:
            print(f"❌ Error checking data for {ticker}: {e}")
            return False


# =============================================================================
# SIMPLE USAGE FUNCTIONS
# =============================================================================

async def generate_quant_impact(ticker: str, user_id: str) -> Dict[str, Any]:
    """
    Simple function to generate and store 7 datasets (English only)
    
    Usage:
        result = await generate_quant_impact("AAPL", user_id="user123")
    """
    from shared_clients import shared_clients
    
    # Initialize if needed
    if not shared_clients._initialized:
        await shared_clients.initialize()
    
    # Create DB Agent and run (always English)
    db_agent = QuantImpactDBAgent(shared_clients=shared_clients)
    result = await db_agent.generate_and_store(ticker, user_id=user_id)
    
    return result


async def retrieve_quant_impact(ticker: str) -> Dict[str, Any]:
    """
    Simple function to retrieve 7 datasets
    
    Usage:
        datasets = await retrieve_quant_impact("AAPL")
    """
    from shared_clients import shared_clients
    
    # Create DB Agent and retrieve
    db_agent = QuantImpactDBAgent(shared_clients=shared_clients)
    result = await db_agent.retrieve_datasets(ticker)
    
    return result


# =============================================================================
# COMMAND LINE INTERFACE
# =============================================================================

async def main():
    """Command line interface"""
    if len(sys.argv) < 2:
        print("""
Quant Impact DB Agent - Command Line Interface

Usage:
    python3 Quant_Impact_DB_Agent.py <TICKER>

Examples:
    python3 Quant_Impact_DB_Agent.py AAPL
    python3 Quant_Impact_DB_Agent.py TSLA
    python3 Quant_Impact_DB_Agent.py OKLO

This will:
1. Run the complete Storage Agent pipeline (English only)
2. Generate all 7 datasets
3. Store them in Redis under Quant_Impact_INFOS:{ticker}
4. Show storage keys and confirmation

Note: All datasets are generated in English by default.
""")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    
    # Generate and store (always English)
    result = await generate_quant_impact(ticker)
    
    # Exit with appropriate code
    if result.get("status") == "success":
        print("\n🎉 All done! Datasets are ready to use.")
        sys.exit(0)
    else:
        print("\n❌ Failed to generate datasets.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

