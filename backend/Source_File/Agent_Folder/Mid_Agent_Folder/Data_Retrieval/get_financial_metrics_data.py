#!/usr/bin/env python3
"""
Get Financial Metrics Data - Simple interface to access all financial metrics information for a ticker

Usage:
    from Mid_Agent_Folder.get_financial_metrics_data import get_financial_metrics_data
    
    result = await get_financial_metrics_data("TSLA")
    
    # Access data
    print(result.ticker)
    print(result.dcf_value)
    print(result.pe_ratio)
    print(result.financial_metrics)
"""

import asyncio
import sys
from typing import Dict, Any, Optional
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
class FinancialMetricsResult:
    """
    Data class for financial metrics result with easy attribute access.
    
    Attributes:
        ticker (str): Stock ticker symbol
        dcf_value (float): DCF (Discounted Cash Flow) valuation
        dcf_data (dict): Complete DCF data
        financial_metrics (dict): All financial metrics (PE, PB, ROE, ROA, etc.)
        price_data (dict): Stock price information
        metadata (dict): Update timestamps and data sources
        last_update (str): Timestamp of last update
        status (str): Status of the request
        raw_data (dict): Full raw data for advanced use
    """
    ticker: str
    dcf_value: Optional[float]
    dcf_data: Dict[str, Any]
    financial_metrics: Dict[str, Any]
    price_data: Dict[str, Any]
    metadata: Dict[str, Any]
    last_update: str
    status: str
    raw_data: Dict[str, Any]
    
    def __repr__(self):
        return f"FinancialMetricsResult(ticker={self.ticker}, dcf_value={self.dcf_value}, status={self.status})"
    
    def summary(self):
        """Get a summary of the financial metrics data"""
        return {
            "ticker": self.ticker,
            "dcf_value": self.dcf_value,
            "pe_ratio": self.get_metric("pe_ratio"),
            "last_update": self.last_update,
            "status": self.status
        }
    
    def get_metric(self, metric_name: str) -> Any:
        """Get a specific financial metric by name"""
        return self.financial_metrics.get(metric_name)
    
    def has_dcf(self) -> bool:
        """Check if DCF valuation is available"""
        return self.dcf_value is not None and self.dcf_value > 0
    
    def has_price_data(self) -> bool:
        """Check if price data is available"""
        return bool(self.price_data and len(self.price_data) > 0)


async def get_financial_metrics_data(ticker: str) -> FinancialMetricsResult:
    """
    Get complete financial metrics data for a ticker.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'TSLA', 'AAPL', 'MSFT')
        
    Returns:
        FinancialMetricsResult: Object with all financial metrics data accessible via attributes
        
    Example:
        >>> result = await get_financial_metrics_data("TSLA")
        >>> print(result.ticker)
        'TSLA'
        >>> print(result.dcf_value)
        250.45
        >>> print(result.get_metric('pe_ratio'))
        45.2
        >>> print(result.has_dcf())
        True
    """
    try:
        # Initialize shared clients
        from shared_clients import shared_clients
        await shared_clients.initialize()
        
        print(f"🔍 Fetching financial metrics data for {ticker}...")
        
        # Import Financial Metrics Read Agent
        from Source_File.Agent_Folder.Sub_Agent_Folder.Financial_Metrics_Agent.Financial_Metrics_Read_Agent import FinancialMetricsReadAgent
        
        # Create agent instance
        agent = FinancialMetricsReadAgent(shared_clients=shared_clients)
        
        # Get financial metrics data
        data = await agent.get_financial_metrics_data(ticker)
        
        # Check if successful
        if not data:
            print(f"❌ No financial metrics data found for {ticker}")
            return FinancialMetricsResult(
                ticker=ticker,
                dcf_value=None,
                dcf_data={},
                financial_metrics={},
                price_data={},
                metadata={},
                last_update="",
                status="failed",
                raw_data={}
            )
        
        # Extract data
        dcf_data = data.get('dcf_data', {})
        dcf_value = dcf_data.get('dcf') if dcf_data else None
        financial_metrics = data.get('financial_metrics', {})
        price_data = data.get('price_data', {})
        metadata = data.get('metadata', {})
        
        # Extract data into FinancialMetricsResult object
        result = FinancialMetricsResult(
            ticker=data.get('ticker', ticker).upper(),
            dcf_value=dcf_value,
            dcf_data=dcf_data,
            financial_metrics=financial_metrics,
            price_data=price_data,
            metadata=metadata,
            last_update=metadata.get('latest_update_time', datetime.now().isoformat()),
            status='success',
            raw_data=data
        )
        
        print(f"✅ Successfully retrieved financial metrics for {ticker}")
        print(f"   - DCF Value: ${result.dcf_value}" if result.has_dcf() else "   - DCF Value: ❌ Not available")
        print(f"   - Price Data: {'✅ Available' if result.has_price_data() else '❌ Not available'}")
        print(f"   - Financial Metrics: {len(result.financial_metrics)} metrics")
        print(f"   - Last Update: {result.last_update}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting financial metrics for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return FinancialMetricsResult(
            ticker=ticker,
            dcf_value=None,
            dcf_data={},
            financial_metrics={},
            price_data={},
            metadata={},
            last_update="",
            status="error",
            raw_data={"error": str(e)}
        )


async def main():
    """Test function - Get financial metrics data for a sample ticker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Financial Metrics Data for a Ticker')
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., TSLA, AAPL)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    print("="*70)
    print(f"📊 FINANCIAL METRICS DATA RETRIEVAL FOR {args.ticker}")
    print("="*70)
    
    # Get financial metrics data
    result = await get_financial_metrics_data(args.ticker)
    
    # Display results
    print(f"\n📈 FINANCIAL METRICS SUMMARY:")
    print("="*70)
    print(f"Ticker:           {result.ticker}")
    print(f"Status:           {result.status}")
    print(f"Last Update:      {result.last_update}")
    print()
    print(f"DCF Value:        ${result.dcf_value}" if result.has_dcf() else "DCF Value:        ❌ Not available")
    print(f"Price Data:       {'✅ Available' if result.has_price_data() else '❌ Not available'}")
    print(f"Financial Metrics: {len(result.financial_metrics)} metrics available")
    
    if args.verbose and result.financial_metrics:
        print(f"\n💰 DETAILED FINANCIAL METRICS:")
        print("="*70)
        for key, value in list(result.financial_metrics.items())[:10]:  # Show first 10 metrics
            print(f"  {key}: {value}")
        
        if result.dcf_data:
            print(f"\n📊 DCF DATA:")
            print("="*70)
            for key, value in result.dcf_data.items():
                print(f"  {key}: {value}")
    
    print("\n" + "="*70)
    print("✅ Financial metrics retrieval complete!")
    print("="*70)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

