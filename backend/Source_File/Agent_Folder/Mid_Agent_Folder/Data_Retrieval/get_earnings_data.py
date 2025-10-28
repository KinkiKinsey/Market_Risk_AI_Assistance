#!/usr/bin/env python3
"""
Get Earnings & Future Data - Simple interface to access all earnings and future development information for a ticker

Usage:
    from Mid_Agent_Folder.get_earnings_data import get_earnings_data
    
    result = await get_earnings_data("TSLA")
    
    # Access data
    print(result.ticker)
    print(result.transcript)
    print(result.earning_date)
    print(result.future_development)
    print(result.company_name)
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
class EarningsResult:
    """
    Data class for earnings and future development result with easy attribute access.
    
    Attributes:
        ticker (str): Stock ticker symbol
        company_name (str): Full company name
        transcript (str): Latest earnings call transcript
        earning_date (str): Next earnings date
        future_development (str): Future business development and strategy
        last_update (str): Timestamp of last update
        data_source (str): Data source used
        transcript_source (str): Source of transcript data
        earning_date_source (str): Source of earnings date
        future_development_source (str): Source of future development
        status (str): Status of the request
        raw_data (dict): Full raw data for advanced use
    """
    ticker: str
    company_name: str
    transcript: str
    earning_date: Optional[str]
    future_development: str
    last_update: str
    data_source: str
    transcript_source: str
    earning_date_source: str
    future_development_source: str
    status: str
    raw_data: Dict[str, Any]
    
    def __repr__(self):
        return f"EarningsResult(ticker={self.ticker}, company_name={self.company_name}, status={self.status})"
    
    def summary(self):
        """Get a summary of the earnings data"""
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "earning_date": self.earning_date,
            "transcript_length": len(self.transcript),
            "future_development_length": len(self.future_development),
            "last_update": self.last_update,
            "status": self.status
        }
    
    def has_transcript(self) -> bool:
        """Check if transcript is available"""
        return bool(self.transcript and len(self.transcript) > 0)
    
    def has_earning_date(self) -> bool:
        """Check if earning date is available"""
        return bool(self.earning_date)
    
    def has_future_development(self) -> bool:
        """Check if future development is available"""
        return bool(self.future_development and len(self.future_development) > 0)


async def get_earnings_data(ticker: str, force_update: bool = False) -> EarningsResult:
    """
    Get complete earnings and future development data for a ticker.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'TSLA', 'AAPL', 'MSFT')
        force_update (bool): Force fresh data fetch (default: False)
        
    Returns:
        EarningsResult: Object with all earnings data accessible via attributes
        
    Example:
        >>> result = await get_earnings_data("TSLA")
        >>> print(result.ticker)
        'TSLA'
        >>> print(result.company_name)
        'Tesla, Inc.'
        >>> print(result.earning_date)
        '2025-01-29'
        >>> print(result.future_development[:100])
        'BUSINESS STRATEGY & DIFFICULTIES OVERCOME:\n\nTesla continues to focus on...'
        >>> print(result.has_transcript())
        True
    """
    try:
        # Initialize shared clients
        from shared_clients import shared_clients
        await shared_clients.initialize()
        
        print(f"🔍 Fetching earnings & future data for {ticker}...")
        
        # Import Earnings and Future Read Agent
        from Source_File.Agent_Folder.Sub_Agent_Folder.Earning_and_Future_Agent.Earnings_and_Future_Read_Agent import EarningsAndFutureReadAgent
        
        # Create agent instance
        agent = EarningsAndFutureReadAgent(shared_clients=shared_clients)
        
        # Get earnings data directly from database (not LLM analysis)
        data = await agent.get_earnings_data(ticker)
        
        # Check if successful
        if not data:
            print(f"❌ No earnings data found for {ticker}")
            # Try to generate fresh data if not found
            if not force_update:
                print(f"🔄 Attempting to generate fresh data...")
                # Call process_natural_query to trigger DB Agent
                await agent.process_natural_query(
                    query=f"Get latest earnings and future development for {ticker}",
                    ticker=ticker,
                    force_update=True
                )
                # Try to get data again
                data = await agent.get_earnings_data(ticker)
            
            if not data:
                return EarningsResult(
                    ticker=ticker,
                    company_name="",
                    transcript="",
                    earning_date=None,
                    future_development="",
                    last_update="",
                    data_source="",
                    transcript_source="",
                    earning_date_source="",
                    future_development_source="",
                    status="failed",
                    raw_data={}
                )
        
        # Extract nested earnings_and_future data
        earnings_data = data.get('earnings_and_future', {})
        metadata = data.get('metadata', {})
        
        # Extract data into EarningsResult object
        result = EarningsResult(
            ticker=data.get('ticker', ticker).upper(),
            company_name=earnings_data.get('company_name', ''),
            transcript=earnings_data.get('transcript', ''),
            earning_date=earnings_data.get('earning_date'),
            future_development=earnings_data.get('future_development', ''),
            last_update=metadata.get('last_update', datetime.now().isoformat()),
            data_source=metadata.get('data_source', 'Earnings_and_Future_Agent'),
            transcript_source=metadata.get('transcript_source', 'Unknown'),
            earning_date_source=metadata.get('earning_date_source', 'Unknown'),
            future_development_source=metadata.get('future_development_source', 'Tavily_Search'),
            status='success',
            raw_data=data
        )
        
        print(f"✅ Successfully retrieved earnings data for {ticker}")
        print(f"   - Company Name: {result.company_name}")
        print(f"   - Transcript: {'✅ Available' if result.has_transcript() else '❌ Not available'} ({len(result.transcript)} chars)")
        print(f"   - Earning Date: {result.earning_date if result.has_earning_date() else '❌ Not available'}")
        print(f"   - Future Dev: {'✅ Available' if result.has_future_development() else '❌ Not available'} ({len(result.future_development)} chars)")
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting earnings data for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return EarningsResult(
            ticker=ticker,
            company_name="",
            transcript="",
            earning_date=None,
            future_development="",
            last_update="",
            data_source="",
            transcript_source="",
            earning_date_source="",
            future_development_source="",
            status="error",
            raw_data={"error": str(e)}
        )


async def main():
    """Test function - Get earnings data for a sample ticker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Earnings & Future Data for a Ticker')
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., TSLA, AAPL)')
    parser.add_argument('--force', action='store_true', help='Force fresh data fetch')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    print("="*70)
    print(f"📈 EARNINGS & FUTURE DATA RETRIEVAL FOR {args.ticker}")
    print("="*70)
    
    # Get earnings data
    result = await get_earnings_data(args.ticker, force_update=args.force)
    
    # Display results
    print(f"\n📊 EARNINGS ANALYSIS SUMMARY:")
    print("="*70)
    print(f"Ticker:           {result.ticker}")
    print(f"Company Name:     {result.company_name}")
    print(f"Status:           {result.status}")
    print(f"Last Update:      {result.last_update}")
    print(f"Data Source:      {result.data_source}")
    print()
    print(f"Transcript:       {'✅ Available' if result.has_transcript() else '❌ Not available'}")
    print(f"  - Source:       {result.transcript_source}")
    print(f"  - Length:       {len(result.transcript)} characters")
    print()
    print(f"Earning Date:     {result.earning_date if result.has_earning_date() else '❌ Not available'}")
    print(f"  - Source:       {result.earning_date_source}")
    print()
    print(f"Future Dev:       {'✅ Available' if result.has_future_development() else '❌ Not available'}")
    print(f"  - Source:       {result.future_development_source}")
    print(f"  - Length:       {len(result.future_development)} characters")
    
    if args.verbose:
        print(f"\n📋 DETAILED CONTENT:")
        print("="*70)
        
        if result.has_transcript():
            print(f"\n📄 TRANSCRIPT (First 500 chars):")
            print("-"*70)
            print(result.transcript[:500] + "..." if len(result.transcript) > 500 else result.transcript)
        
        if result.has_future_development():
            print(f"\n🚀 FUTURE DEVELOPMENT (First 500 chars):")
            print("-"*70)
            print(result.future_development[:500] + "..." if len(result.future_development) > 500 else result.future_development)
    
    print("\n" + "="*70)
    print("✅ Earnings data retrieval complete!")
    print("="*70)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

