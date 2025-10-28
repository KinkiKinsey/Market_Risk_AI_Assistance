#!/usr/bin/env python3
"""
Get Macro Data - Simple interface to access all macro-economic analysis data

Usage:
    from Mid_Agent_Folder.get_macro_data import get_macro_data
    
    result = await get_macro_data()
    
    # Access data
    print(result.analysis)
    print(result.indicators)
    print(result.last_update)
"""

import asyncio
import sys
from typing import Dict, Any, List
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
class MacroResult:
    """
    Data class for macro-economic analysis result with easy attribute access.
    
    Attributes:
        analysis (str): LLM-generated macro economic analysis
        metadata (dict): Data metadata (update time, data range, etc.)
        indicators (list): List of available economic indicators
        macro_data (dict): Raw macro data for all indicators
        last_update (str): Timestamp of last update
        data_range (dict): Start and end dates of data coverage
        status (str): Status of the request
        raw_data (dict): Full raw data for advanced use
    """
    analysis: str
    metadata: Dict[str, Any]
    indicators: List[str]
    macro_data: Dict[str, Any]
    last_update: str
    data_range: Dict[str, str]
    status: str
    raw_data: Dict[str, Any]
    
    def __repr__(self):
        return f"MacroResult(indicators={len(self.indicators)}, last_update={self.last_update}, status={self.status})"
    
    def summary(self):
        """Get a summary of the macro data"""
        return {
            "indicators_count": len(self.indicators),
            "last_update": self.last_update,
            "data_range": self.data_range,
            "analysis_length": len(self.analysis),
            "status": self.status
        }
    
    def get_indicator_data(self, indicator_name: str) -> Dict:
        """Get data for a specific economic indicator"""
        return self.macro_data.get(indicator_name, {})
    
    def has_analysis(self) -> bool:
        """Check if analysis is available"""
        return bool(self.analysis and len(self.analysis) > 0)
    
    def has_indicator(self, indicator_name: str) -> bool:
        """Check if a specific indicator is available"""
        return indicator_name in self.indicators
    
    def list_indicators(self) -> List[str]:
        """Get list of all available indicators"""
        return self.indicators


async def get_macro_data() -> MacroResult:
    """
    Get complete macro-economic analysis data.
    Note: Macro data is global, not ticker-specific.
    
    Returns:
        MacroResult: Object with all macro economic data accessible via attributes
        
    Example:
        >>> result = await get_macro_data()
        >>> print(result.has_analysis())
        True
        >>> print(len(result.indicators))
        15
        >>> print(result.get_indicator_data('GDP'))
        {'value': 3.2, 'trend': 'increasing'}
    """
    try:
        # Initialize shared clients
        from shared_clients import shared_clients
        await shared_clients.initialize()
        
        print(f"🔍 Fetching macro economic data...")
        
        # Import Macro Read Agent
        from Source_File.Agent_Folder.Sub_Agent_Folder.Macro_Analyst_Agent.Macro_Read_Agent import MacroReadAgent
        
        # Create agent instance
        agent = MacroReadAgent(shared_clients=shared_clients)
        
        # Get macro data
        data = await agent.read_macro_data()
        
        # Check if successful
        if 'error' in data:
            print(f"❌ Failed to get macro data: {data.get('error', 'Unknown error')}")
            return MacroResult(
                analysis="",
                metadata={},
                indicators=[],
                macro_data={},
                last_update="",
                data_range={},
                status="failed",
                raw_data=data
            )
        
        # Extract data
        analyst_data = data.get('analyst', {})
        macro_data = data.get('macro_data', {})
        metadata = data.get('metadata', {})
        analysis = data.get('analysis', analyst_data.get('analysis', ''))
        indicators = list(data.get('indicators', []))
        
        # Remove 'meta_data' from indicators if present
        if 'meta_data' in indicators:
            indicators.remove('meta_data')
        
        # Extract data into MacroResult object
        result = MacroResult(
            analysis=analysis,
            metadata=metadata,
            indicators=indicators,
            macro_data=macro_data,
            last_update=metadata.get('last_update_time', datetime.now().isoformat()),
            data_range=metadata.get('data_range', {}),
            status='success',
            raw_data=data
        )
        
        print(f"✅ Successfully retrieved macro economic data")
        print(f"   - Indicators: {len(result.indicators)} economic indicators")
        print(f"   - Analysis: {'✅ Available' if result.has_analysis() else '❌ Not available'} ({len(result.analysis)} chars)")
        print(f"   - Last Update: {result.last_update}")
        print(f"   - Data Range: {result.data_range.get('start_date', 'N/A')} to {result.data_range.get('end_date', 'N/A')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error getting macro data: {e}")
        import traceback
        traceback.print_exc()
        return MacroResult(
            analysis="",
            metadata={},
            indicators=[],
            macro_data={},
            last_update="",
            data_range={},
            status="error",
            raw_data={"error": str(e)}
        )


async def main():
    """Test function - Get macro economic data"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Get Macro Economic Data')
    parser.add_argument('--verbose', action='store_true', help='Show detailed output')
    
    args = parser.parse_args()
    
    print("="*70)
    print(f"🌍 MACRO ECONOMIC DATA RETRIEVAL")
    print("="*70)
    
    # Get macro data
    result = await get_macro_data()
    
    # Display results
    print(f"\n📊 MACRO ECONOMIC SUMMARY:")
    print("="*70)
    print(f"Status:           {result.status}")
    print(f"Last Update:      {result.last_update}")
    print(f"Data Range:       {result.data_range.get('start_date', 'N/A')} to {result.data_range.get('end_date', 'N/A')}")
    print()
    print(f"Analysis:         {'✅ Available' if result.has_analysis() else '❌ Not available'}")
    print(f"  - Length:       {len(result.analysis)} characters")
    print()
    print(f"Indicators:       {len(result.indicators)} economic indicators")
    
    if args.verbose:
        print(f"\n📈 AVAILABLE INDICATORS:")
        print("="*70)
        for indicator in result.indicators:
            print(f"  • {indicator}")
        
        if result.has_analysis():
            print(f"\n🤖 MACRO ECONOMIC ANALYSIS (First 500 chars):")
            print("="*70)
            print(result.analysis[:500] + "..." if len(result.analysis) > 500 else result.analysis)
    
    print("\n" + "="*70)
    print("✅ Macro economic data retrieval complete!")
    print("="*70)


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())

