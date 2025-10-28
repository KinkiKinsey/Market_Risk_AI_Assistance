#!/usr/bin/env python3
"""
Get Market Expectation Data - Simple interface to access all market expectation/stock trend information for a ticker

Usage:
    from Mid_Agent_Folder.get_market_expectation_data import get_market_expectation_data
    
    result = await get_market_expectation_data("TSLA")
    
    # Access data
    print(result.ticker)
    print(result.current_trends)
    print(result.historical_trends)
"""

import asyncio
import sys
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Add parent directory to path (for when running as script)
if __name__ == "__main__":
    parent_dir = Path(__file__).parent.parent
    sys.path.insert(0, str(parent_dir))
else:
    # When imported, add paths relative to current working directory
    import os
    cwd = Path.cwd()
    if str(cwd) not in sys.path:
        sys.path.insert(0, str(cwd))

@dataclass
class MarketExpectationResult:
    """
    Data class for market expectation/stock trend result with easy attribute access.
    
    Attributes:
        ticker (str): Stock ticker symbol
        current_trends (dict): Current ongoing trend data
        historical_trends (dict): Historical trend data
        stored_at (str): Timestamp of data storage
        last_update (str): Timestamp of last update
        status (str): Status of the request
        raw_data (dict): Full raw data for advanced use
    """
    ticker: str
    current_trends: Dict[str, Any]
    historical_trends: Dict[str, Any]
    stored_at: str
    last_update: str
    status: str
    raw_data: Dict[str, Any]
    
    def __repr__(self):
        return f"MarketExpectationResult(ticker={self.ticker}, current_trends={len(self.current_trends)}, status={self.status})"
    
    def summary(self):
        """Get a summary of the market expectation data"""
        return {
            "ticker": self.ticker,
            "current_trends_count": len(self.current_trends),
            "historical_trends_count": len(self.historical_trends),
            "last_update": self.last_update,
            "status": self.status
        }
    
    def get_current_trend(self, trend_id: str = None) -> Dict:
        """Get current trend data (first trend if no ID specified)"""
        if trend_id:
            return self.current_trends.get(trend_id, {})
        elif self.current_trends:
            return list(self.current_trends.values())[0]
        return {}
    
    def get_historical_trend(self, trend_id: str = None) -> Dict:
        """Get historical trend data (first trend if no ID specified)"""
        if trend_id:
            return self.historical_trends.get(trend_id, {})
        elif self.historical_trends:
            return list(self.historical_trends.values())[0]
        return {}
    
    def has_current_trends(self) -> bool:
        """Check if current trends are available"""
        return bool(self.current_trends and len(self.current_trends) > 0)
    
    def has_historical_trends(self) -> bool:
        """Check if historical trends are available"""
        return bool(self.historical_trends and len(self.historical_trends) > 0)
    
    def list_trend_ids(self, trend_type: str = "all") -> List[str]:
        """List all trend IDs (current, historical, or all)"""
        trend_ids = []
        if trend_type in ["current", "all"]:
            trend_ids.extend(list(self.current_trends.keys()))
        if trend_type in ["historical", "all"]:
            trend_ids.extend(list(self.historical_trends.keys()))
        return trend_ids


async def get_market_expectation_data(ticker: str) -> MarketExpectationResult:
    """
    Get complete market expectation/stock trend data for a ticker.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'TSLA', 'AAPL', 'MSFT')
        
    Returns:
        MarketExpectationResult: Object with all market expectation data accessible via attributes
        
    Example:
        >>> result = await get_market_expectation_data("TSLA")
        >>> print(result.ticker)
        'TSLA'
        >>> print(result.has_current_trends())
        True
        >>> current = result.get_current_trend()
        >>> print(current.get('day average_return'))
        0.015
    """
    try:
        # Initialize shared clients
        from shared_clients import shared_clients
        await shared_clients.initialize()
        
        print(f"🔍 Fetching market expectation data for {ticker}...")
        
        # Import Stock Trend Read Agent
        from Source_File.Agent_Folder.Sub_Agent_Folder.Market_Expectation_Agent.Stock_Trend_Read_Agent import StockTrendAnalystAgent
        
        # Create agent instance
        agent = StockTrendAnalystAgent(shared_clients=shared_clients)
        
        # Get stock trend data
        data = await agent.get_stock_data(ticker)
        
        # Check if successful
        if not data:
            print(f"❌ No market expectation data found for {ticker}")
            return MarketExpectationResult(
                ticker=ticker,
                current_trends={},
                historical_trends={},
                stored_at="",
                last_update="",
                status="failed",
                raw_data={}
            )
        
        # Extract data into MarketExpectationResult object
        result = MarketExpectationResult(
            ticker=data.get('ticker', ticker).upper(),
            current_trends=data.get('current_trends', {}),
            historical_trends=data.get('historical_trends', {}),
            stored_at=data.get('stored_at', ''),
            last_update=data.get('stored_at', datetime.now().isoformat()),
            status='success',
            raw_data=data
        )
        
        print(f"✅ Successfully retrieved market expectation data for {ticker}")
        print(f"   - Current Trends: {len(result.current_trends)} trends")
        print(f"   - Historical Trends: {len(result.historical_trends)} trends")
        print(f"   - Last Update: {result.last_update}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting market expectation data for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return MarketExpectationResult(
            ticker=ticker,
            current_trends={},
            historical_trends={},
            stored_at="",
            last_update="",
            status="error",
            raw_data={"error": str(e)}
        )


async def main():
    """Test function - Get market expectation data for a sample ticker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Market Expectation Data for a Ticker')
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., TSLA, AAPL)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    print("="*70)
    print(f"📈 MARKET EXPECTATION DATA RETRIEVAL FOR {args.ticker}")
    print("="*70)
    
    # Get market expectation data
    result = await get_market_expectation_data(args.ticker)
    
    # Display results
    print(f"\n📊 MARKET EXPECTATION SUMMARY:")
    print("="*70)
    print(f"Ticker:              {result.ticker}")
    print(f"Status:              {result.status}")
    print(f"Last Update:         {result.last_update}")
    print()
    print(f"Current Trends:      {len(result.current_trends)} trends")
    print(f"Historical Trends:   {len(result.historical_trends)} trends")
    print(f"Total Trend IDs:     {len(result.list_trend_ids())}")
    
    if args.verbose and result.has_current_trends():
        print(f"\n🔥 CURRENT TREND DETAILS:")
        print("="*70)
        current = result.get_current_trend()
        print(f"  Symbol: {current.get('symbol', 'N/A')}")
        print(f"  Day Average Return: {current.get('day average_return', 'N/A')}")
        print(f"  Slope: {current.get('Slope of stock trend', 'N/A')}")
        print(f"  Max Return: {current.get('Max Return', 'N/A')}")
        print(f"  Estimate Price: {current.get('Estimate_price', 'N/A')}")
        print(f"  Duration: {current.get('How Long it Take', 'N/A')} days")
        
        summary = current.get('summary', {})
        if summary:
            print(f"\n  📝 Macro Reason: {summary.get('macro_reason', 'N/A')[:100]}...")
            print(f"  📝 Micro Reason: {summary.get('micro_reason', 'N/A')[:100]}...")
    
    if args.verbose and result.has_historical_trends():
        print(f"\n📜 HISTORICAL TRENDS:")
        print("="*70)
        print(f"  Total Historical Trends: {len(result.historical_trends)}")
        print(f"  Trend IDs: {', '.join(list(result.historical_trends.keys())[:5])}...")
    
    print("\n" + "="*70)
    print("✅ Market expectation data retrieval complete!")
    print("="*70)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

