"""
Data Retrieval Module
=====================

Simple interface to retrieve data from all agents.

Available Functions:
--------------------
- get_earnings_data(ticker)           - Earnings & Future Development
- get_sector_data(ticker)             - Sector Analysis
- get_financial_metrics_data(ticker)  - Financial Metrics & DCF
- get_market_expectation_data(ticker) - Market Trends & Expectations
- get_macro_data()                    - Macro Economic Analysis (no ticker)
- get_revenue_segmentation_data(ticker) - Revenue Segmentation

Usage Example:
--------------
    from Source_File.Agent_Folder.Mid_Agent_Folder.Data_Retrieval import get_earnings_data, get_sector_data
    
    earnings = await get_earnings_data("TSLA")
    sector = await get_sector_data("TSLA")
    
    print(earnings.ticker, earnings.company_name)
    print(sector.sector_index)
"""

from .get_earnings_data import get_earnings_data, EarningsResult
from .get_sector_data import get_sector_data, SectorResult
from .get_financial_metrics_data import get_financial_metrics_data, FinancialMetricsResult
from .get_market_expectation_data import get_market_expectation_data, MarketExpectationResult
from .get_macro_data import get_macro_data, MacroResult
from .get_revenue_segmentation_data import get_revenue_segmentation_data, RevenueSegmentationResult

__all__ = [
    # Functions
    'get_earnings_data',
    'get_sector_data',
    'get_financial_metrics_data',
    'get_market_expectation_data',
    'get_macro_data',
    'get_revenue_segmentation_data',
    # Result Classes
    'EarningsResult',
    'SectorResult',
    'FinancialMetricsResult',
    'MarketExpectationResult',
    'MacroResult',
    'RevenueSegmentationResult',
]

