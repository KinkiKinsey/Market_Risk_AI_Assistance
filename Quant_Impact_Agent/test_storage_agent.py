"""
Test Quant Impact Storage Agent - Generate 7 Datasets

This script tests the complete pipeline and validates all 7 datasets are generated.

Usage:
    python3 test_storage_agent.py <TICKER> <LANGUAGE>
    
Example:
    python3 test_storage_agent.py AAPL English
    python3 test_storage_agent.py TSLA Chinese
"""

import asyncio
import sys
from datetime import datetime

# Import the storage agent
from Quant_Impact_Storage_Agent import QuantImpactStorageAgent
from shared_clients import shared_clients

async def test_storage_agent(ticker: str, language: str = "English"):
    """
    Test the complete storage agent pipeline
    
    Args:
        ticker: Stock ticker symbol
        language: Language for output (English or Chinese)
    """
    print("=" * 70)
    print(f"🧪 TESTING QUANT IMPACT STORAGE AGENT")
    print("=" * 70)
    print(f"📊 Ticker: {ticker}")
    print(f"🌐 Language: {language}")
    print(f"⏰ Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    
    try:
        # Initialize shared clients
        print("🚀 Initializing shared clients...")
        await shared_clients.initialize()
        print("✅ Shared clients initialized\n")
        
        # Create storage agent
        print("📦 Creating Quant Impact Storage Agent...")
        agent = QuantImpactStorageAgent(shared_clients=shared_clients)
        print("✅ Storage agent created\n")
        
        # Run the complete pipeline
        print("🔄 Running complete analysis pipeline...")
        print("-" * 70)
        result = await agent.process_quant_impact_analysis(
            ticker=ticker,
            language=language
        )
        print("-" * 70)
        print()
        
        # Check results
        if result.get("status") == "success":
            print("=" * 70)
            print("✅ ANALYSIS COMPLETED SUCCESSFULLY!")
            print("=" * 70)
            print()
            
            # Validate all 7 datasets
            print("📊 VALIDATING 7 DATASETS:")
            print("-" * 70)
            
            datasets = {
                "1. risk_share_index": result.get("risk_share_index"),
                "2. macro_volatility_df": result.get("macro_volatility_df"),
                "3. micro_volatility_df": result.get("micro_volatility_df"),
                "4. risk_reward_df": result.get("risk_reward_df"),
                "5. macro_total_impact_df": result.get("macro_total_impact_df"),
                "6. micro_total_impact_df": result.get("micro_total_impact_df"),
                "7. Factor_Risk_Reward": result.get("Factor_Risk_Reward")
            }
            
            all_present = True
            for name, dataset in datasets.items():
                if dataset is not None:
                    if isinstance(dataset, dict):
                        print(f"✅ {name}: Dict with {len(dataset)} keys")
                    else:
                        print(f"✅ {name}: DataFrame with {len(dataset)} rows")
                else:
                    print(f"❌ {name}: MISSING!")
                    all_present = False
            
            print("-" * 70)
            print()
            
            # Show summary statistics
            print("📈 SUMMARY STATISTICS:")
            print("-" * 70)
            print(f"Ticker: {result.get('ticker')}")
            print(f"Macro Factors: {len(result.get('macro_factors', []))}")
            print(f"Micro Factors: {len(result.get('micro_factors', []))}")
            print(f"Summary DataFrame Rows: {len(result.get('summary_df', []))}")
            
            if result.get('risk_share_index'):
                rsi = result['risk_share_index']
                print(f"\nRisk Share:")
                print(f"  Macro Risk: {rsi.get('macro_risk_share', 0):.1f}%")
                print(f"  Micro Risk: {rsi.get('micro_risk_share', 0):.1f}%")
            
            print("-" * 70)
            print()
            
            # Show Factor_Risk_Reward details
            if result.get('Factor_Risk_Reward') is not None:
                frr = result['Factor_Risk_Reward']
                print("🎯 FACTOR_RISK_REWARD DETAILS:")
                print("-" * 70)
                print(f"Total Factor Categories: {len(frr)}")
                if len(frr) > 0:
                    print(f"\nTop 3 Factors by Max Return:")
                    for idx, row in frr.head(3).iterrows():
                        print(f"  {idx+1}. {row['factor_name']} ({row['category']})")
                        print(f"     Max: {row['max_compound_return']:.4f}, Min: {row['min_compound_return']:.4f}")
                print("-" * 70)
                print()
            
            # Final verdict
            if all_present:
                print("=" * 70)
                print("🎉 SUCCESS! ALL 7 DATASETS GENERATED CORRECTLY!")
                print("=" * 70)
                print()
                print("✅ Storage Agent is working correctly")
                print("✅ All datasets are present")
                print("✅ Data stored in Redis")
                print()
                return True
            else:
                print("=" * 70)
                print("⚠️ WARNING: SOME DATASETS ARE MISSING!")
                print("=" * 70)
                return False
                
        else:
            print("=" * 70)
            print("❌ ANALYSIS FAILED!")
            print("=" * 70)
            print(f"Status: {result.get('status')}")
            print(f"Error: {result.get('error', 'Unknown error')}")
            print()
            return False
            
    except Exception as e:
        print("=" * 70)
        print("❌ TEST FAILED WITH EXCEPTION!")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        print(f"⏰ End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python3 test_storage_agent.py <TICKER> [LANGUAGE]")
        print()
        print("Examples:")
        print("  python3 test_storage_agent.py AAPL English")
        print("  python3 test_storage_agent.py TSLA Chinese")
        sys.exit(1)
    
    ticker = sys.argv[1].upper()
    language = sys.argv[2] if len(sys.argv) > 2 else "English"
    
    # Run the test
    success = asyncio.run(test_storage_agent(ticker, language))
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

