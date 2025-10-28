#!/usr/bin/env python3
"""
Get Revenue Segmentation Data - Simple interface to access revenue segmentation information for a ticker

Usage:
    from Mid_Agent_Folder.get_revenue_segmentation_data import get_revenue_segmentation_data
    
    result = await get_revenue_segmentation_data("TSLA")
    
    # Access data
    print(result.ticker)
    print(result.business_segments)
    print(result.total_revenue)
"""

import asyncio
import sys
from typing import Dict, Any, List, Optional
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
class RevenueSegmentationResult:
    """
    Data class for revenue segmentation result with easy attribute access.
    
    Attributes:
        ticker (str): Stock ticker symbol
        business_segments (list): List of business segments with revenue data
        total_revenue (str): Total company revenue
        cost_segments (list): List of cost structure segments (NEW)
        supplier_segments (list): List of supplier segments (NEW)
        metadata (dict): Metadata (update time, earnings date, etc.)
        last_update (str): Timestamp of last update
        next_earnings_date (str): Next earnings date
        stored_at (str): Timestamp when data was stored
        status (str): Status of the request
        raw_data (dict): Full raw data for advanced use
    """
    ticker: str
    business_segments: List[Dict[str, Any]]
    total_revenue: str
    cost_segments: List[Dict[str, Any]]  # ✅ NEW
    supplier_segments: List[Dict[str, Any]]  # ✅ NEW
    metadata: Dict[str, Any]
    last_update: str
    next_earnings_date: Optional[str]
    stored_at: str
    status: str
    raw_data: Dict[str, Any]
    
    def __repr__(self):
        return f"RevenueSegmentationResult(ticker={self.ticker}, segments={len(self.business_segments)}, status={self.status})"
    
    def summary(self):
        """Get a summary of the revenue segmentation data"""
        return {
            "ticker": self.ticker,
            "segments_count": len(self.business_segments),
            "cost_segments_count": len(self.cost_segments),  # ✅ NEW
            "supplier_segments_count": len(self.supplier_segments),  # ✅ NEW
            "total_revenue": self.total_revenue,
            "next_earnings_date": self.next_earnings_date,
            "last_update": self.last_update,
            "status": self.status
        }
    
    def get_segment(self, segment_name: str) -> Optional[Dict]:
        """Get a specific business segment by name"""
        for segment in self.business_segments:
            if segment.get('name', '').lower() == segment_name.lower():
                return segment
        return None
    
    def get_segment_by_index(self, index: int) -> Optional[Dict]:
        """Get a business segment by index"""
        if 0 <= index < len(self.business_segments):
            return self.business_segments[index]
        return None
    
    def has_segments(self) -> bool:
        """Check if business segments are available"""
        return bool(self.business_segments and len(self.business_segments) > 0)
    
    def list_segment_names(self) -> List[str]:
        """Get list of all segment names"""
        return [segment.get('name', 'Unknown') for segment in self.business_segments]
    
    def get_largest_segment(self) -> Optional[Dict]:
        """Get the segment with highest revenue percentage"""
        if not self.business_segments:
            return None
        
        def extract_percentage(segment):
            pct_str = segment.get('percentage_of_total_revenue', '0%')
            try:
                return float(pct_str.replace('%', ''))
            except:
                return 0.0
        
        return max(self.business_segments, key=extract_percentage)
    
    # ✅ NEW METHODS FOR COST AND SUPPLIER DATA
    def get_cost_segment(self, category: str) -> Optional[Dict]:
        """Get a specific cost segment by category name"""
        for segment in self.cost_segments:
            if segment.get('category', '').lower() == category.lower():
                return segment
        return None
    
    def get_supplier_segment(self, supplier_name: str) -> Optional[Dict]:
        """Get a specific supplier segment by supplier name"""
        for segment in self.supplier_segments:
            if segment.get('supplier_name', '').lower() == supplier_name.lower():
                return segment
        return None
    
    def has_cost_data(self) -> bool:
        """Check if cost structure data is available"""
        return bool(self.cost_segments and len(self.cost_segments) > 0)
    
    def has_supplier_data(self) -> bool:
        """Check if supplier data is available"""
        return bool(self.supplier_segments and len(self.supplier_segments) > 0)
    
    def list_cost_categories(self) -> List[str]:
        """Get list of all cost categories"""
        return [segment.get('category', 'Unknown') for segment in self.cost_segments]
    
    def list_suppliers(self) -> List[str]:
        """Get list of all suppliers"""
        return [segment.get('supplier_name', 'Unknown') for segment in self.supplier_segments]


async def get_revenue_segmentation_data(ticker: str) -> RevenueSegmentationResult:
    """
    Get complete revenue segmentation data for a ticker.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., 'TSLA', 'AAPL', 'MSFT')
        
    Returns:
        RevenueSegmentationResult: Object with all revenue segmentation data accessible via attributes
        
    Example:
        >>> result = await get_revenue_segmentation_data("TSLA")
        >>> print(result.ticker)
        'TSLA'
        >>> print(result.has_segments())
        True
        >>> print(result.list_segment_names())
        ['Automotive', 'Energy Generation', 'Services']
        >>> largest = result.get_largest_segment()
        >>> print(largest['name'])
        'Automotive'
    """
    try:
        # Initialize shared clients
        from shared_clients import shared_clients
        await shared_clients.initialize()
        
        print(f"🔍 Fetching revenue segmentation data for {ticker}...")
        
        # Import Revenue Segmentation Read Agent
        from Source_File.Agent_Folder.Sub_Agent_Folder.Fundamental_Segmentation_Agent.Revenue_Segmentation_Read_Agent import RevenueSegmentationAnalystAgent
        
        # Create agent instance
        agent = RevenueSegmentationAnalystAgent(shared_clients=shared_clients)
        
        # Get revenue segmentation data
        data = await agent.get_revenue_segmentation_data(ticker)
        
        # Check if successful
        if not data:
            print(f"❌ No revenue segmentation data found for {ticker}")
            return RevenueSegmentationResult(
                ticker=ticker,
                business_segments=[],
                total_revenue="",
                cost_segments=[],  # ✅ NEW
                supplier_segments=[],  # ✅ NEW
                metadata={},
                last_update="",
                next_earnings_date=None,
                stored_at="",
                status="failed",
                raw_data={}
            )
        
        # Extract data
        revenue_segmentation = data.get('revenue_segmentation', {})
        business_segments = revenue_segmentation.get('business_segments', [])
        total_revenue = revenue_segmentation.get('total_revenue', '')
        
        # ✅ NEW: Extract cost and supplier data
        cost_supply_segmentation = data.get('cost_supply_segmentation', {})
        cost_segments = cost_supply_segmentation.get('cost_segments', [])
        supplier_segments = cost_supply_segmentation.get('supplier_segments', [])
        
        metadata = data.get('metadata', {})
        
        # Extract data into RevenueSegmentationResult object
        result = RevenueSegmentationResult(
            ticker=data.get('ticker', ticker).upper(),
            business_segments=business_segments,
            total_revenue=total_revenue,
            cost_segments=cost_segments,  # ✅ NEW
            supplier_segments=supplier_segments,  # ✅ NEW
            metadata=metadata,
            last_update=metadata.get('last_update', data.get('stored_at', datetime.now().isoformat())),
            next_earnings_date=metadata.get('next_earnings_date'),
            stored_at=data.get('stored_at', ''),
            status='success',
            raw_data=data
        )
        
        print(f"✅ Successfully retrieved revenue segmentation data for {ticker}")
        print(f"   - Business Segments: {len(result.business_segments)} segments")
        print(f"   - Cost Segments: {len(result.cost_segments)} segments")  # ✅ NEW
        print(f"   - Supplier Segments: {len(result.supplier_segments)} segments")  # ✅ NEW
        print(f"   - Total Revenue: {result.total_revenue}")
        print(f"   - Next Earnings: {result.next_earnings_date if result.next_earnings_date else 'Not available'}")
        print(f"   - Last Update: {result.last_update}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting revenue segmentation data for {ticker}: {e}")
        import traceback
        traceback.print_exc()
        return RevenueSegmentationResult(
            ticker=ticker,
            business_segments=[],
            total_revenue="",
            cost_segments=[],  # ✅ NEW
            supplier_segments=[],  # ✅ NEW
            metadata={},
            last_update="",
            next_earnings_date=None,
            stored_at="",
            status="error",
            raw_data={"error": str(e)}
        )


async def main():
    """Test function - Get revenue segmentation data for a sample ticker"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Revenue Segmentation Data for a Ticker')
    parser.add_argument('ticker', help='Stock ticker symbol (e.g., TSLA, AAPL)')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    print("="*70)
    print(f"💰 REVENUE SEGMENTATION DATA RETRIEVAL FOR {args.ticker}")
    print("="*70)
    
    # Get revenue segmentation data
    result = await get_revenue_segmentation_data(args.ticker)
    
    # Display results
    print(f"\n📊 REVENUE SEGMENTATION SUMMARY:")
    print("="*70)
    print(f"Ticker:              {result.ticker}")
    print(f"Status:              {result.status}")
    print(f"Total Revenue:       {result.total_revenue}")
    print(f"Business Segments:   {len(result.business_segments)} segments")
    print(f"Cost Segments:       {len(result.cost_segments)} segments")  # ✅ NEW
    print(f"Supplier Segments:   {len(result.supplier_segments)} segments")  # ✅ NEW
    print(f"Next Earnings Date:  {result.next_earnings_date if result.next_earnings_date else 'Not available'}")
    print(f"Last Update:         {result.last_update}")
    
    if args.verbose and result.has_segments():
        print(f"\n💼 BUSINESS SEGMENTS:")
        print("="*70)
        for i, segment in enumerate(result.business_segments, 1):
            print(f"\n  {i}. {segment.get('name', 'Unknown')}")
            print(f"     Revenue %: {segment.get('percentage_of_total_revenue', 'N/A')}")
            print(f"     Revenue Amount: {segment.get('Revenue Amount', 'N/A')}")
            print(f"     Target Customer: {segment.get('target_customer_or_revenue_method', 'N/A')}")
        
        largest = result.get_largest_segment()
        if largest:
            print(f"\n  🏆 Largest Segment: {largest.get('name')} ({largest.get('percentage_of_total_revenue')})")
    
    # ✅ NEW: Display cost and supplier data
    if args.verbose and result.has_cost_data():
        print(f"\n💰 COST STRUCTURE:")
        print("="*70)
        for i, cost in enumerate(result.cost_segments, 1):
            print(f"\n  {i}. {cost.get('category', 'Unknown')}")
            print(f"     Percentage: {cost.get('percentage_of_revenue', 'N/A')}")
            print(f"     Amount: {cost.get('cost_amount', 'N/A')}")
            print(f"     Details: {cost.get('details', 'N/A')[:100]}...")
    
    if args.verbose and result.has_supplier_data():
        print(f"\n🏭 SUPPLIERS:")
        print("="*70)
        for i, supplier in enumerate(result.supplier_segments, 1):
            print(f"\n  {i}. {supplier.get('supplier_name', 'Unknown')}")
            print(f"     Products: {supplier.get('products_supplied', 'N/A')}")
            print(f"     Relationship: {supplier.get('relationship_type', 'N/A')}")
            print(f"     Details: {supplier.get('details', 'N/A')[:100]}...")
    
    print("\n" + "="*70)
    print("✅ Revenue segmentation data retrieval complete!")
    print("="*70)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

