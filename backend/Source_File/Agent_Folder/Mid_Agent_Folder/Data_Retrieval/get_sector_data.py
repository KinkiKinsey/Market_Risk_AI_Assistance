#!/usr/bin/env python3
"""
Get Sector Data - Simple interface to access all sector information for a ticker

Usage:
    from Mid_Agent_Folder.get_sector_data import get_sector_data
    
    result = await get_sector_data("TSLA")
    
    # Access data
    print(result.ticker)
    print(result.asset_relative)
    print(result.answer_collection)
    print(result.sector_index)
    print(result.last_update)
"""

import asyncio
import sys
from typing import Dict, Any
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
class SectorResult:
    """
    Data class for sector analysis result with easy attribute access.
    
    Attributes:
        ticker (str): Stock ticker symbol
        asset_relative (str): Full asset/product description
        asset_relative_summary (str): 1-5 word sector summary (e.g., "General Merchandise Retail")
        competitor_summary (str): Comma-separated competitor names (e.g., "Walmart, Amazon, Costco")
        sector_index (str): Sector index (e.g., XLE, XLF, XLK)
        answer_collection (dict): Collection of sector-related answers
        url_collection (dict): Collection of URLs for each answer
        last_update (str): Timestamp of last update
        data_source (str): Data source used
        status (str): Status of the request
        raw_data (dict): Full raw data for advanced use
    """
    ticker: str
    asset_relative: str
    asset_relative_summary: str
    competitor_summary: str
    sector_index: str
    answer_collection: Dict[str, str]
    url_collection: Dict[str, list]
    last_update: str
    data_source: str
    status: str
    raw_data: Dict[str, Any]
    
    def __repr__(self):
        return f"SectorResult(ticker={self.ticker}, sector_index={self.sector_index}, status={self.status})"
    
    def summary(self):
        """Get a summary of the sector data"""
        return {
            "ticker": self.ticker,
            "sector_index": self.sector_index,
            "asset_relative_summary": self.asset_relative_summary,
            "competitor_summary": self.competitor_summary,
            "asset_relative": self.asset_relative,
            "num_answers": len(self.answer_collection),
            "last_update": self.last_update,
            "status": self.status
        }
    
    def get_competitors_list(self) -> list:
        """Get competitors as a list"""
        if not self.competitor_summary or self.competitor_summary.lower() == "none":
            return []
        return [c.strip() for c in self.competitor_summary.split(',')]
    
    def get_answer(self, key: str) -> str:
        """Get a specific answer by key"""
        return self.answer_collection.get(key, "")
    
    def get_urls(self, key: str) -> list:
        """Get URLs for a specific answer key"""
        return self.url_collection.get(key, [])
    
    # === Helper methods for sector_index nested fields ===
    @property
    def sector_index_ticker(self) -> str:
        """Get sector index ticker (e.g., XLP, XLK)"""
        if isinstance(self.sector_index, dict):
            return self.sector_index.get('ticker', '')
        return self.sector_index
    
    @property
    def sector_index_description(self) -> str:
        """Get sector index description"""
        if isinstance(self.sector_index, dict):
            return self.sector_index.get('description', '')
        return ''
    
    @property
    def confidence_score(self) -> float:
        """Get confidence score for sector index match (0-1)"""
        if isinstance(self.sector_index, dict):
            return self.sector_index.get('confidence_score', 0.0)
        return 0.0
    
    @property
    def reasoning(self) -> str:
        """Get LLM reasoning for sector index match"""
        if isinstance(self.sector_index, dict):
            return self.sector_index.get('reasoning', '')
        return ''
    
    @property
    def match_method(self) -> str:
        """Get match method (e.g., llm_analysis)"""
        if isinstance(self.sector_index, dict):
            return self.sector_index.get('match_method', '')
        return ''


async def get_sector_data(ticker: str) -> SectorResult:
    """
    Get complete sector analysis data for a ticker.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'TSLA', 'AAPL', 'MSFT')
        
    Returns:
        SectorResult: Object with all sector data accessible via attributes
        
    Example:
        >>> result = await get_sector_data("TSLA")
        >>> print(result.ticker)
        'TSLA'
        >>> print(result.asset_relative)
        'Electric Vehicles and Clean Energy'
        >>> print(result.sector_index)
        'XLK'
        >>> print(result.answer_collection.keys())
        dict_keys(['sector_overview', 'competitive_landscape', ...])
    """
    try:
        # Initialize shared clients
        from shared_clients import shared_clients
        await shared_clients.initialize()
        
        print(f"🔍 Fetching sector data for {ticker}...")
        
        # Import Sector Analyst Read Agent
        from Source_File.Agent_Folder.Sub_Agent_Folder.Sector_Analyst_Agent.Sector_Analyst_Read_Agent import SectorAnalystReadAgent
        
        # Create agent instance
        agent = SectorAnalystReadAgent(shared_clients=shared_clients)
        
        # Get sector data
        data = await agent.process_sector_query(ticker)
        
        # Check if successful
        if data.get('status') == 'failed' or 'error' in data:
            print(f"❌ Failed to get sector data: {data.get('error', 'Unknown error')}")
            return SectorResult(
                ticker=ticker,
                asset_relative="",
                asset_relative_summary="",
                competitor_summary="",
                sector_index="",
                answer_collection={},
                url_collection={},
                last_update="",
                data_source="",
                status="failed",
                raw_data=data
            )
        
        # Extract data into SectorResult object
        result = SectorResult(
            ticker=data.get('ticker', ticker).upper(),
            asset_relative=data.get('asset_relative', ''),
            asset_relative_summary=data.get('asset_relative_summary', ''),
            competitor_summary=data.get('competitor_summary', ''),
            sector_index=data.get('relative_sector_index', ''),
            answer_collection=data.get('answer_collection', {}),
            url_collection=data.get('url_collection', {}),
            last_update=data.get('last_update', datetime.now().isoformat()),
            data_source=data.get('data_source', 'Sector_Analyst_Agent'),
            status=data.get('status', 'success'),
            raw_data=data
        )
        
        print(f"✅ Successfully retrieved sector data for {ticker}")
        print(f"   - Sector Index: {result.sector_index}")
        print(f"   - Sector Summary: {result.asset_relative_summary}")
        print(f"   - Competitors: {result.competitor_summary}")
        print(f"   - Answers Available: {len(result.answer_collection)}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting sector data for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return SectorResult(
            ticker=ticker,
            asset_relative="",
            asset_relative_summary="",
            competitor_summary="",
            sector_index="",
            answer_collection={},
            url_collection={},
            last_update="",
            data_source="",
            status="error",
            raw_data={"error": str(e)}
        )


async def main():
    """Test function - Get sector data for a sample ticker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Sector Data for a Ticker')
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., TSLA, AAPL)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    print("="*70)
    print(f"🏭 SECTOR DATA RETRIEVAL FOR {args.ticker}")
    print("="*70)
    
    # Get sector data
    result = await get_sector_data(args.ticker)
    
    # Display results
    print(f"\n📊 SECTOR ANALYSIS SUMMARY:")
    print("="*70)
    print(f"Ticker:          {result.ticker}")
    print(f"Status:          {result.status}")
    print(f"Sector Index:    {result.sector_index}")
    print(f"Sector Summary:  {result.asset_relative_summary}")
    print(f"Competitors:     {result.competitor_summary}")
    print(f"Asset:           {result.asset_relative[:100]}..." if len(result.asset_relative) > 100 else f"Asset:           {result.asset_relative}")
    print(f"Last Update:     {result.last_update}")
    print(f"Data Source:     {result.data_source}")
    
    if args.verbose and result.answer_collection:
        print(f"\n📋 DETAILED ANSWERS:")
        print("="*70)
        for key, answer in result.answer_collection.items():
            print(f"\n🔹 {key}:")
            print(f"   {answer[:200]}..." if len(answer) > 200 else f"   {answer}")
            
            # Show URLs if available
            urls = result.get_urls(key)
            if urls:
                print(f"   📎 Sources ({len(urls)} URLs):")
                for url in urls[:3]:  # Show first 3 URLs
                    print(f"      - {url}")
    
    print("\n" + "="*70)
    print("✅ Sector data retrieval complete!")
    print("="*70)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

