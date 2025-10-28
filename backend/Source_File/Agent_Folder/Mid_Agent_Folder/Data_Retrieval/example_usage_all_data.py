#!/usr/bin/env python3
"""
Example Usage - How to use all data retrieval functions

This example shows how to retrieve data from all agents and access their information.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

# Import all data retrieval functions
from get_earnings_data import get_earnings_data
from get_sector_data import get_sector_data
from get_financial_metrics_data import get_financial_metrics_data
from get_market_expectation_data import get_market_expectation_data
from get_macro_data import get_macro_data
from get_revenue_segmentation_data import get_revenue_segmentation_data


async def example_usage(ticker: str = "TSLA"):
    """
    Example showing how to retrieve and use all data types.
    
    Args:
        ticker (str): Stock ticker symbol
    """
    print("="*80)
    print(f"🚀 COMPREHENSIVE DATA RETRIEVAL EXAMPLE FOR {ticker}")
    print("="*80)
    
    # 1. Get Earnings & Future Data
    print("\n📈 1. EARNINGS & FUTURE DATA")
    print("-"*80)
    earnings = await get_earnings_data(ticker)
    print(f"   Ticker: {earnings.ticker}")
    print(f"   Company: {earnings.company_name}")
    print(f"   Earnings Date: {earnings.earning_date}")
    print(f"   Has Transcript: {earnings.has_transcript()}")
    print(f"   Has Future Dev: {earnings.has_future_development()}")
    
    # 2. Get Sector Data
    print("\n🏭 2. SECTOR DATA")
    print("-"*80)
    sector = await get_sector_data(ticker)
    print(f"   Ticker: {sector.ticker}")
    print(f"   Sector Index: {sector.sector_index}")
    print(f"   Asset Relative: {sector.asset_relative[:50]}...")
    print(f"   Answers Available: {len(sector.answer_collection)}")
    
    # 3. Get Financial Metrics Data
    print("\n💰 3. FINANCIAL METRICS DATA")
    print("-"*80)
    financial = await get_financial_metrics_data(ticker)
    print(f"   Ticker: {financial.ticker}")
    print(f"   DCF Value: ${financial.dcf_value}" if financial.has_dcf() else "   DCF Value: Not available")
    print(f"   Has Price Data: {financial.has_price_data()}")
    print(f"   Financial Metrics: {len(financial.financial_metrics)} metrics")
    
    # 4. Get Market Expectation Data
    print("\n📊 4. MARKET EXPECTATION DATA")
    print("-"*80)
    market = await get_market_expectation_data(ticker)
    print(f"   Ticker: {market.ticker}")
    print(f"   Current Trends: {len(market.current_trends)}")
    print(f"   Historical Trends: {len(market.historical_trends)}")
    print(f"   Has Current Trends: {market.has_current_trends()}")
    
    # 5. Get Macro Data (no ticker needed)
    print("\n🌍 5. MACRO ECONOMIC DATA")
    print("-"*80)
    macro = await get_macro_data()
    print(f"   Indicators: {len(macro.indicators)}")
    print(f"   Has Analysis: {macro.has_analysis()}")
    print(f"   Data Range: {macro.data_range.get('start_date', 'N/A')} to {macro.data_range.get('end_date', 'N/A')}")
    
    # 6. Get Revenue Segmentation Data
    print("\n💼 6. REVENUE SEGMENTATION DATA")
    print("-"*80)
    revenue = await get_revenue_segmentation_data(ticker)
    print(f"   Ticker: {revenue.ticker}")
    print(f"   Business Segments: {len(revenue.business_segments)}")
    print(f"   Total Revenue: {revenue.total_revenue}")
    print(f"   Segment Names: {', '.join(revenue.list_segment_names())}")
    
    # Example: Accessing specific data
    print("\n" + "="*80)
    print("🎯 EXAMPLE: ACCESSING SPECIFIC DATA")
    print("="*80)
    
    # Access earnings transcript (first 200 chars)
    if earnings.has_transcript():
        print(f"\n📄 Earnings Transcript Preview:")
        print(f"   {earnings.transcript[:200]}...")
    
    # Access current market trend
    if market.has_current_trends():
        current_trend = market.get_current_trend()
        print(f"\n📈 Current Market Trend:")
        print(f"   Day Average Return: {current_trend.get('day average_return', 'N/A')}")
        print(f"   Estimate Price: ${current_trend.get('Estimate_price', 'N/A')}")
    
    # Access largest revenue segment
    if revenue.has_segments():
        largest = revenue.get_largest_segment()
        print(f"\n💰 Largest Revenue Segment:")
        print(f"   Name: {largest.get('name', 'N/A')}")
        print(f"   Revenue %: {largest.get('percentage_of_total_revenue', 'N/A')}")
    
    # Access macro indicators
    if macro.indicators:
        print(f"\n🌍 Sample Macro Indicators:")
        for indicator in macro.indicators[:5]:
            print(f"   • {indicator}")
    
    print("\n" + "="*80)
    print("✅ ALL DATA RETRIEVAL COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Example usage of all data retrieval functions')
    parser.add_argument('--ticker', default='TSLA', help='Stock ticker symbol (default: TSLA)')
    
    args = parser.parse_args()
    
    # Run the example
    asyncio.run(example_usage(args.ticker))

