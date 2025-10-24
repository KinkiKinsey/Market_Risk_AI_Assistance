"""
Quick Test Script for Q&Q.AI Visualization
===========================================

Use this to quickly test the visualization with fake data.
Perfect for development and testing without hitting APIs.

Usage:
    python quick_test.py
"""

from test_data_generator import generate_test_data
from visualize_qq_ai_report_impact_chains import visualize_qq_ai_report

def quick_test_visualization(ticker: str = "AAPL"):
    """Quick test with fake data"""
    
    print(f"🧪 Quick Test: Generating visualization for {ticker}...")
    
    # Generate test data
    test_data = generate_test_data(ticker, news_days=5)
    
    # Visualize
    visualize_qq_ai_report(
        ticker=test_data['ticker'],
        impact_chains=test_data['impact_chains'],
        dates=test_data['dates'],
        links=test_data['links'],
        macro_df=test_data['macro_df'],
        micro_df=test_data['micro_df'],
        factor_time_df=test_data['factor_time_df'],
        language="English"
    )
    
    print("\n✅ Visualization generated! Check your browser.")
    print(f"📊 Summary:")
    print(f"   - {len(test_data['impact_chains'])} impact chains")
    print(f"   - {len(test_data['macro_df'])} macro factors")
    print(f"   - {len(test_data['micro_df'])} micro factors")
    
    return test_data


if __name__ == "__main__":
    test_data = quick_test_visualization("TGT")

