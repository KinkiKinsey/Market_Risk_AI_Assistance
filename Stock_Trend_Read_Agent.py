#!/usr/bin/env python3
"""
Stock Trend Analyst Agent
A natural language interface for querying stock trend data from Redis database.
"""

import sys
import os
from pathlib import Path

# Fix import paths for multiprocessing in Streamlit
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import argparse
from pathlib import Path
import redis
from Stock_Trend_DB_Agent import DatabaseStorage
from LLM_Call_Agent import LLMCallAgent
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('stock_analyst.log')
    ]
)

@dataclass
class TrendSegment:
    """Data class for trend segment information."""
    trend_id: str
    time_period: str
    trend_type: str  # 'uptrend' or 'downtrend'
    symbol: str
    day_average_return: float
    slope: float
    max_return: float
    estimate_price: float
    duration: float
    macro_reason: str
    micro_reason: str
    return_variance: float

class StockTrendAnalystAgent:
    """
    Natural language interface for querying stock trend data from Redis database.
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, redis_username: str = "default", 
                 redis_password: str = None, collection_name: str = "Stock_Trend_INFOS",
                 openai_api_key: str = None):
        """
        Initialize the Stock Trend Analyst Agent.
        
        Args:
            redis_host (str): Redis host
            redis_port (int): Redis port
            redis_username (str): Redis username
            redis_password (str): Redis password
            collection_name (str): Redis collection/namespace
            openai_api_key (str): OpenAI API key for LLM queries
        """
        if shared_clients:
            # Use shared Redis connection
            self.redis_client = shared_clients.get_stock_trend_redis()
            self.storage = DatabaseStorage(
                db_type="redis",
                shared_clients=shared_clients
            )
            logging.info("✅ Using shared Redis connection")
        else:
            # Use individual Redis connection
            self.redis_host = redis_host
            self.redis_port = redis_port
            self.redis_username = redis_username
            self.redis_password = redis_password
            self.collection_name = collection_name
            self.openai_api_key = openai_api_key
            
            # Initialize database storage
            self.storage = DatabaseStorage(
                db_type="redis",
                host=redis_host,
                port=redis_port,
                username=redis_username,
                password=redis_password
            )
            
            # Direct Redis connection for Read Agent
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                username=redis_username,
                password=redis_password,
                decode_responses=True
            )
        
        # Use shared clients for LLM operations
        if shared_clients:
            self.llm_agent = shared_clients.get_llm_agent()
            logging.info("✅ Using shared LLM client")
        else:
            try:
                from shared_clients import shared_clients
                self.llm_agent = shared_clients.get_llm_agent()
                logging.info("✅ Using shared LLM client")
            except ImportError:
                # Fallback to direct LLM agent if shared clients not available
                self.llm_agent = LLMCallAgent(
                    openai_api_key=openai_api_key,
                    deepseek_api_key=None,
                    default_provider="deepseek",
                    default_model="deepseek-chat"
                )
                logging.info("⚠️ Using direct LLM client (shared clients not available)")
        
        logging.info("🤖 Stock Trend Analyst Agent initialized")
        logging.info(f"   - Redis: {redis_host}:{redis_port}")
        logging.info(f"   - Collection: {collection_name}")
        logging.info(f"   - LLM Provider: {self.llm_agent.get_provider_status()['deepseek']}")
        
        # Define available functions for the LLM
        self.available_functions = [
            {
                "name": "get_current_trend_info",
                "description": "Get detailed information about the current ongoing trend",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "include_price_distribution": {
                            "type": "boolean",
                            "description": "Whether to include price distribution analysis"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_historical_trends",
                "description": "Get information about historical trend segments",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trend_type": {
                            "type": "string",
                            "enum": ["uptrend", "downtrend", "all"],
                            "description": "Filter by trend type"
                        },
                        "time_period": {
                            "type": "string",
                            "description": "Specific time period to analyze (e.g., '2025-01-27 to 2025-01-29')"
                        },
                        "include_analysis": {
                            "type": "boolean",
                            "description": "Whether to include detailed macro/micro analysis"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "compare_trends",
                "description": "Compare current trend with historical trends",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "comparison_type": {
                            "type": "string",
                            "enum": ["performance", "duration", "volatility", "reasons"],
                            "description": "Type of comparison to perform"
                        }
                    },
                    "required": ["comparison_type"]
                }
            },
            {
                "name": "get_trend_statistics",
                "description": "Get statistical analysis of trends",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "statistic_type": {
                            "type": "string",
                            "enum": ["returns", "volatility", "duration", "price_movement"],
                            "description": "Type of statistics to calculate"
                        },
                        "trend_filter": {
                            "type": "string",
                            "enum": ["current", "historical", "all"],
                            "description": "Which trends to include in statistics"
                        }
                    },
                    "required": ["statistic_type"]
                }
            },
            {
                "name": "analyze_price_distribution",
                "description": "Analyze price distribution parameters for trends",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "trend_id": {
                            "type": "string",
                            "description": "Specific trend ID to analyze"
                        },
                        "include_risk_metrics": {
                            "type": "boolean",
                            "description": "Whether to include risk assessment metrics"
                        }
                    },
                    "required": []
                }
            }
        ]
    
    def get_stock_data(self, ticker: str) -> Optional[Dict]:
        """
        Retrieve stock trend data for a given ticker using direct Redis access.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Optional[Dict]: Stock trend data or None if not found
        """
        try:
            logging.info(f"📈 Retrieving data for ticker: {ticker}")
            
            # Direct Redis access using the same logic as DB Agent
            redis_key = f"{self.collection_name}:{ticker.upper()}_trends"
            data_str = self.redis_client.get(redis_key)
            
            if data_str:
                data = json.loads(data_str)
                logging.info(f"✅ Found data for {ticker}")
                logging.info(f"   - Current trends: {len(data.get('current_trends', {}))}")
                logging.info(f"   - Historical trends: {len(data.get('historical_trends', {}))}")
                logging.info(f"   - Last updated: {data.get('stored_at', 'Unknown')}")
                return data
            else:
                logging.warning(f"⚠️ No data found for ticker: {ticker}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error retrieving data for {ticker}: {e}")
            return None
    
    def list_available_tickers(self) -> List[str]:
        """
        List all available stock tickers in the database.
        
        Returns:
            List[str]: List of available ticker symbols
        """
        try:
            logging.info("📋 Listing available tickers...")
            tickers = self.storage.list_stock_tickers(self.collection_name)
            
            if tickers:
                logging.info(f"✅ Found {len(tickers)} tickers: {', '.join(tickers)}")
            else:
                logging.info("ℹ️ No tickers found in database")
            
            return tickers
            
        except Exception as e:
            logging.error(f"❌ Error listing tickers: {e}")
            return []
    
    def _parse_trend_segment(self, trend_id: str, trend_data: Dict) -> TrendSegment:
        """Parse a trend segment into a structured format."""
        return TrendSegment(
            trend_id=trend_id,
            time_period=trend_data.get('current', 'Unknown'),
            trend_type='uptrend' if 'uptrend' in trend_id else 'downtrend',
            symbol=trend_data.get('symbol', ''),
            day_average_return=trend_data.get('day average_return', 0.0),
            slope=trend_data.get('Slope of stock trend', 0.0),
            max_return=trend_data.get('Max Return', 0.0),
            estimate_price=trend_data.get('Estimate_price', 0.0),
            duration=trend_data.get('How Long it Take', 0.0),
            macro_reason=trend_data.get('summary', {}).get('macro_reason', ''),
            micro_reason=trend_data.get('summary', {}).get('micro_reason', ''),
            return_variance=trend_data.get('return rate variance', 0.0)
        )
    
    def get_current_trend_info(self, include_price_distribution: bool = True) -> Dict:
        """Get detailed information about the current ongoing trend."""
        if not hasattr(self, '_current_stock_data'):
            return {"error": "No stock data loaded"}
        
        current_trends = self._current_stock_data.get('current_trends', {})
        if not current_trends:
            return {"error": "No current trends available"}
        
        result = {
            "current_trends_count": len(current_trends),
            "trends": []
        }
        
        for trend_id, trend_data in current_trends.items():
            trend_info = {
                "trend_id": trend_id,
                "time_period": trend_data.get('current', 'Unknown'),
                "trend_type": 'uptrend' if 'uptrend' in trend_id else 'downtrend',
                "symbol": trend_data.get('symbol', ''),
                "day_average_return": trend_data.get('day average_return', 0.0),
                "slope": trend_data.get('Slope of stock trend', 0.0),
                "max_return": trend_data.get('Max Return', 0.0),
                "estimate_price": trend_data.get('Estimate_price', 0.0),
                "duration": trend_data.get('How Long it Take', 0.0),
                "return_variance": trend_data.get('return rate variance', 0.0),
                "macro_reason": trend_data.get('summary', {}).get('macro_reason', ''),
                "micro_reason": trend_data.get('summary', {}).get('micro_reason', '')
            }
            
            if include_price_distribution:
                trend_info["price_distribution"] = {
                    "estimate_price": trend_data.get('Estimate_price', 0.0),
                    "return_variance": trend_data.get('return rate variance', 0.0),
                    "max_return": trend_data.get('Max Return', 0.0)
                }
            
            result["trends"].append(trend_info)
        
        return result
    
    def get_historical_trends(self, trend_type: str = "all", time_period: str = None, 
                            include_analysis: bool = True) -> Dict:
        """Get information about historical trend segments."""
        if not hasattr(self, '_current_stock_data'):
            return {"error": "No stock data loaded"}
        
        historical_trends = self._current_stock_data.get('historical_trends', {})
        if not historical_trends:
            return {"error": "No historical trends available"}
        
        filtered_trends = []
        
        for trend_id, trend_data in historical_trends.items():
            # Filter by trend type
            if trend_type != "all":
                if trend_type == "uptrend" and "uptrend" not in trend_id:
                    continue
                if trend_type == "downtrend" and "downtrend" not in trend_id:
                    continue
            
            # Filter by time period
            if time_period and trend_data.get('current', '') != time_period:
                continue
            
            trend_info = {
                "trend_id": trend_id,
                "time_period": trend_data.get('current', 'Unknown'),
                "trend_type": 'uptrend' if 'uptrend' in trend_id else 'downtrend',
                "symbol": trend_data.get('symbol', ''),
                "day_average_return": trend_data.get('day average_return', 0.0),
                "slope": trend_data.get('Slope of stock trend', 0.0),
                "max_return": trend_data.get('Max Return', 0.0),
                "estimate_price": trend_data.get('Estimate_price', 0.0),
                "duration": trend_data.get('How Long it Take', 0.0),
                "return_variance": trend_data.get('return rate variance', 0.0)
            }
            
            if include_analysis:
                trend_info["macro_reason"] = trend_data.get('summary', {}).get('macro_reason', '')
                trend_info["micro_reason"] = trend_data.get('summary', {}).get('micro_reason', '')
            
            filtered_trends.append(trend_info)
        
        return {
            "historical_trends_count": len(filtered_trends),
            "trends": filtered_trends
        }
    
    def compare_trends(self, comparison_type: str) -> Dict:
        """Compare current trend with historical trends."""
        if not hasattr(self, '_current_stock_data'):
            return {"error": "No stock data loaded"}
        
        current_trends = self._current_stock_data.get('current_trends', {})
        historical_trends = self._current_stock_data.get('historical_trends', {})
        
        if not current_trends or not historical_trends:
            return {"error": "Insufficient data for comparison"}
        
        comparison_result = {
            "comparison_type": comparison_type,
            "current_trends": len(current_trends),
            "historical_trends": len(historical_trends)
        }
        
        if comparison_type == "performance":
            # Compare average returns
            current_returns = [t.get('day average_return', 0.0) for t in current_trends.values()]
            historical_returns = [t.get('day average_return', 0.0) for t in historical_trends.values()]
            
            comparison_result.update({
                "current_avg_return": sum(current_returns) / len(current_returns) if current_returns else 0,
                "historical_avg_return": sum(historical_returns) / len(historical_returns) if historical_returns else 0,
                "performance_difference": (sum(current_returns) / len(current_returns) if current_returns else 0) - 
                                       (sum(historical_returns) / len(historical_returns) if historical_returns else 0)
            })
        
        elif comparison_type == "volatility":
            # Compare return variances
            current_variances = [t.get('return rate variance', 0.0) for t in current_trends.values()]
            historical_variances = [t.get('return rate variance', 0.0) for t in historical_trends.values()]
            
            comparison_result.update({
                "current_avg_variance": sum(current_variances) / len(current_variances) if current_variances else 0,
                "historical_avg_variance": sum(historical_variances) / len(historical_variances) if historical_variances else 0,
                "volatility_difference": (sum(current_variances) / len(current_variances) if current_variances else 0) - 
                                       (sum(historical_variances) / len(historical_variances) if historical_variances else 0)
            })
        
        return comparison_result
    
    def get_trend_statistics(self, statistic_type: str, trend_filter: str = "all") -> Dict:
        """Get statistical analysis of trends."""
        if not hasattr(self, '_current_stock_data'):
            return {"error": "No stock data loaded"}
        
        trends_data = {}
        if trend_filter in ["current", "all"]:
            trends_data.update(self._current_stock_data.get('current_trends', {}))
        if trend_filter in ["historical", "all"]:
            trends_data.update(self._current_stock_data.get('historical_trends', {}))
        
        if not trends_data:
            return {"error": "No trends available for analysis"}
        
        if statistic_type == "returns":
            returns = [t.get('day average_return', 0.0) for t in trends_data.values()]
            return {
                "statistic_type": "returns",
                "count": len(returns),
                "mean": sum(returns) / len(returns) if returns else 0,
                "min": min(returns) if returns else 0,
                "max": max(returns) if returns else 0,
                "positive_count": len([r for r in returns if r > 0]),
                "negative_count": len([r for r in returns if r < 0])
            }
        
        elif statistic_type == "volatility":
            variances = [t.get('return rate variance', 0.0) for t in trends_data.values()]
            return {
                "statistic_type": "volatility",
                "count": len(variances),
                "mean_variance": sum(variances) / len(variances) if variances else 0,
                "max_variance": max(variances) if variances else 0,
                "min_variance": min(variances) if variances else 0
            }
        
        elif statistic_type == "duration":
            durations = [t.get('How Long it Take', 0.0) for t in trends_data.values()]
            return {
                "statistic_type": "duration",
                "count": len(durations),
                "mean_duration": sum(durations) / len(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0
            }
        
        return {"error": f"Unknown statistic type: {statistic_type}"}
    
    def analyze_price_distribution(self, trend_id: str = None, include_risk_metrics: bool = True) -> Dict:
        """Analyze price distribution parameters for trends."""
        if not hasattr(self, '_current_stock_data'):
            return {"error": "No stock data loaded"}
        
        all_trends = {}
        all_trends.update(self._current_stock_data.get('current_trends', {}))
        all_trends.update(self._current_stock_data.get('historical_trends', {}))
        
        if trend_id:
            if trend_id not in all_trends:
                return {"error": f"Trend ID {trend_id} not found"}
            trends_to_analyze = {trend_id: all_trends[trend_id]}
        else:
            trends_to_analyze = all_trends
        
        analysis_result = {
            "trends_analyzed": len(trends_to_analyze),
            "price_distributions": []
        }
        
        for trend_id, trend_data in trends_to_analyze.items():
            distribution = {
                "trend_id": trend_id,
                "estimate_price": trend_data.get('Estimate_price', 0.0),
                "return_variance": trend_data.get('return rate variance', 0.0),
                "max_return": trend_data.get('Max Return', 0.0),
                "day_average_return": trend_data.get('day average_return', 0.0),
                "slope": trend_data.get('Slope of stock trend', 0.0)
            }
            
            if include_risk_metrics:
                # Calculate risk metrics
                volatility = trend_data.get('return rate variance', 0.0) ** 0.5
                distribution["risk_metrics"] = {
                    "volatility": volatility,
                    "risk_level": "High" if volatility > 0.05 else "Medium" if volatility > 0.02 else "Low",
                    "price_stability": "Stable" if abs(trend_data.get('day average_return', 0.0)) < 0.01 else "Volatile"
                }
            
            analysis_result["price_distributions"].append(distribution)
        
        return analysis_result
    
    async def analyze_query_with_llm(self, query: str, stock_data: Dict) -> str:
        """
        Use LLM Call Agent to analyze the query and provide insights about the stock data.
        
        Args:
            query (str): Natural language query
            stock_data (Dict): Stock trend data
            
        Returns:
            str: LLM-generated analysis and response
        """
        if not self.llm_agent.get_available_providers():
            return "❌ No LLM providers configured. Cannot provide LLM analysis."
        
        try:
            # Store stock data for function access
            self._current_stock_data = stock_data
            
            # Create system message with function calling instructions
            system_message = """You are a specialized stock market analyst assistant with access to precise data extraction functions.

**CRITICAL DATA STRUCTURE UNDERSTANDING:**

1. **CURRENT TRENDS** (current_trends): 
   - This represents the MOST RECENT and ONGOING trend analysis
   - Contains current stock price distribution parameters (mean, std, percentiles)
   - Shows what is happening RIGHT NOW in the market
   - Use get_current_trend_info() for current data queries

2. **HISTORICAL TRENDS** (historical_trends):
   - This contains PAST trend segments with their respective price distributions
   - Each historical segment has its own price distribution parameters
   - Use get_historical_trends() for historical data queries
   - Do NOT use current_trends when asking about historical data

**STOCK PRICE DISTRIBUTION PARAMETERS (CRITICAL):**
- Each trend segment contains detailed price distribution data
- Key parameters include: estimate_price, return_variance, max_return, day_average_return
- These parameters are CRUCIAL for understanding price behavior and risk assessment
- Use analyze_price_distribution() for detailed price analysis

**FUNCTION CALLING RULES:**
- For current trend questions → Call get_current_trend_info()
- For historical trend questions → Call get_historical_trends()
- For trend comparisons → Call compare_trends()
- For statistical analysis → Call get_trend_statistics()
- For price distribution analysis → Call analyze_price_distribution()

**QUERY INTERPRETATION RULES:**
- If the query asks about "current", "now", "ongoing", "recent" → Use get_current_trend_info()
- If the query asks about "past", "historical", "previous", "trend analysis" → Use get_historical_trends()
- If the query asks about "price distribution", "risk", "volatility" → Use analyze_price_distribution()
- If the query asks about "trend continuation" → Use compare_trends()
- If the query asks about "statistics", "averages", "performance" → Use get_trend_statistics()

**RESPONSE FORMAT REQUIREMENTS:**
You MUST structure your response in EXACTLY ONE section:

**SIMILAR TREND MAPPING**: 
- **MAPPING RULE: Find trends with similar macro + micro conditions**
  - Analyze user query for macro/micro context
  - Search database for trends with matching macro_reason + micro_reason patterns
  - Map multiple trends if they have similar macro/micro conditions
  - Focus on PRECISION, not quantity - only include highly relevant matches
  - Match either uptrend or downtrend based on query context

- **MUST use EXACT FORMAT with detailed price distribution:**
  ```
  <Similar Trend Time: [trend_name] [start_date, end_date]>
  <Reason: because similar macro as [macro_reason], micro as [micro_reason]>
  <Similar Trend Price: start: [start_date], end: [end_date], day_avg_return: [X.XXX%], slope: [X.XX], max_return: [X.XX%], estimate_price: $[X.XX], duration: [X.X] days, return_variance: [X.XXXXXX], volatility: [X.XX%]>
  ```

- **INCLUDE ALL PRICE DISTRIBUTION VARIABLES from database:**
  - start, end, day_avg_return, slope, max_return, estimate_price, duration, return_variance, volatility
  - **USE EXACT macro_reason and micro_reason from database summary field**
  - Do NOT make up or approximate values

- **MAPPING STRATEGY:**
  1. Identify macro themes in user query (policy, earnings, AI, etc.)
  2. Find trends with similar macro_reason patterns
  3. Within those trends, identify micro_reason similarities
  4. Include trends that match BOTH macro and micro conditions
  5. Output precise matches, not exhaustive lists

Always call the appropriate function first to get precise data, then provide analysis based on the function results."""
            
            # Use simple LLM call for analysis (works with DeepSeek)
            analysis_prompt = f"""
Analyze this stock data and answer the user's query.

USER QUERY: "{query}"

STOCK DATA SUMMARY:
- Ticker: {stock_data.get('ticker', 'Unknown')}
- Current Trends: {len(stock_data.get('current_trends', {}))} segments
- Historical Trends: {len(stock_data.get('historical_trends', {}))} segments
- Last Updated: {stock_data.get('stored_at', 'Unknown')}

**CRITICAL: ONLY USE THE EXACT VALUES FROM THE DATABASE BELOW - DO NOT MAKE UP DATES OR APPROXIMATE VALUES**

ACTUAL DATABASE DATA (USE EXACT VALUES):
{json.dumps(stock_data, indent=2)}

**IMPORTANT: Use the exact numerical values from the database:**
- Use exact "day average_return" values (e.g., -0.0253 = -2.53%)
- Use exact "Max Return" values (e.g., -0.33 = -33%)
- Use exact "Estimate_price" values (e.g., 177.49000549316406 = $177.49)
- Use exact "Slope of stock trend" values (e.g., -3.29)
- Use exact "How Long it Take" values (e.g., 28.0 = 28 days)
- Calculate volatility from "return rate variance" (sqrt of variance)
- **USE EXACT MACRO/MICRO REASONS from "summary" field:**
  - Use exact "macro_reason" from database (e.g., "Not specified by LLM.")
  - Use exact "micro_reason" from database (e.g., "Not specified by LLM.")
  - Do NOT make up or approximate macro/micro reasons

**CRITICAL MAPPING RULE:**
- **IGNORE CURRENT TRENDS** - Current trends are ONLY additional context about what's happening now
- **FOCUS ON HISTORICAL TRENDS** - Your main purpose is to dig into historical data and find similar patterns
- **MAP USER QUERY TO HISTORICAL TRENDS** based on macro/micro condition similarity
- **Current trends are NOT answers** - they just provide context about current market conditions

AVAILABLE DATA:
1. **Current Trends: IGNORE THESE FOR ANSWERS** - Only use as context about current market
2. **Historical Trends: FOCUS ON THESE** - Past trend segments with performance data for mapping
3. Price Distribution: Risk metrics, volatility, and return analysis
4. Trend Statistics: Performance comparisons and statistical analysis

**IMPORTANT: Structure your response in EXACTLY ONE section:**

**SIMILAR TREND MAPPING**: 
- **MUST use EXACT FORMAT with detailed price distribution:**
  ```
  <Similar Trend Time: [trend_name] [start_date, end_date]>
  <Reason: because similar macro as [macro_reason], micro as [micro_reason]>
  <Similar Trend Price: start: [start_date], end: [end_date], day_avg_return: [X.XXX%], slope: [X.XX], max_return: [X.XX%], estimate_price: $[X.XX], duration: [X.X] days, return_variance: [X.XXXXXX], volatility: [X.XX%]>
  ```
- **INCLUDE ALL PRICE DISTRIBUTION VARIABLES from database:**
  - start, end, day_avg_return, slope, max_return, estimate_price, duration, return_variance, volatility
  - **USE EXACT macro_reason and micro_reason from database summary field**
  - Do NOT make up or approximate values
- **ONLY OUTPUT THIS FORMAT - NO OTHER SECTIONS**
- **FOCUS ON HISTORICAL MAPPING:** Your role is to map user queries to RELEVANT HISTORICAL TRENDS and output the original data

**REMEMBER: Current trends are context only. Historical trends are your answers.**
"""
            
            # Use shared clients semaphore-controlled async LLM call
            try:
                from shared_clients import shared_clients
                analysis_response = await shared_clients.call_deepseek(
                    prompt=analysis_prompt,
                    system_message="You are a HISTORICAL TREND MAPPING specialist. Your ONLY job is to find RELEVANT HISTORICAL TRENDS from the database that match the user's query based on macro + micro conditions. IGNORE CURRENT TRENDS - they are only context, not answers. Structure your response in EXACTLY ONE section: SIMILAR TREND MAPPING. MAPPING RULE: Find HISTORICAL trends with similar macro + micro conditions. Analyze user query for macro/micro context, search database for HISTORICAL trends with matching macro_reason + micro_reason patterns, map multiple HISTORICAL trends if they have similar macro/micro conditions, focus on PRECISION not quantity, match either uptrend or downtrend based on query context. Use format <Similar Trend Time: [trend] [dates]>, <Reason: because similar macro as [reason], micro as [reason]>, <Similar Trend Price: start: [start_date], end: [end_date], day_avg_return: [X.XXX%], slope: [X.XX], max_return: [X.XX%], estimate_price: $[X.XX], duration: [X.X] days, return_variance: [X.XXXXXX], volatility: [X.XX%]>. Focus on precise HISTORICAL mapping based on macro + micro condition similarity.",
                    max_tokens=1000,
                    temperature=0.3
                )
            except Exception as e:
                # Fallback to direct LLM call if shared clients fail
                analysis_response = self.llm_agent.call_llm(
                    prompt=analysis_prompt,
                    system_message="You are a HISTORICAL TREND MAPPING specialist. Your ONLY job is to find RELEVANT HISTORICAL TRENDS from the database that match the user's query based on macro + micro conditions. IGNORE CURRENT TRENDS - they are only context, not answers. Structure your response in EXACTLY ONE section: SIMILAR TREND MAPPING. MAPPING RULE: Find HISTORICAL trends with similar macro + micro conditions. Analyze user query for macro/micro context, search database for HISTORICAL trends with matching macro_reason + micro_reason patterns, map multiple HISTORICAL trends if they have similar macro/micro conditions, focus on PRECISION not quantity, match either uptrend or downtrend based on query context. Use format <Similar Trend Time: [trend] [dates]>, <Reason: because similar macro as [reason], micro as [reason]>, <Similar Trend Price: start: [start_date], end: [end_date], day_avg_return: [X.XXX%], slope: [X.XX], max_return: [X.XX%], estimate_price: $[X.XX], duration: [X.X] days, return_variance: [X.XXXXXX], volatility: [X.XX%]>. Focus on precise HISTORICAL mapping based on macro + micro condition similarity.",
                    max_tokens=1000,
                    temperature=0.3
                )
            
            return analysis_response
            
        except Exception as e:
            logging.error(f"❌ Error in LLM analysis: {e}")
            return f"❌ Error in LLM analysis: {e}"
    
    def check_database_status(self, ticker: str, force_update: bool = False) -> Dict:
        """
        Check database status for a ticker - data availability and freshness.
        
        Args:
            ticker (str): Stock ticker symbol
            force_update (bool): Force update even if recent data exists
            
        Returns:
            Dict: Status information including data availability and freshness
        """
        try:
            logging.info(f"🔍 Checking database status for ticker: {ticker}")
            
            # Get stock data from database
            stock_data = self.get_stock_data(ticker)
            
            if not stock_data:
                return {
                    "status": "not_found",
                    "message": f"No data found for ticker {ticker}",
                    "recommendation": "run_analysis",
                    "ticker": ticker
                }
            
            # Check data freshness
            stored_at = stock_data.get('stored_at')
            if stored_at:
                if isinstance(stored_at, str):
                    stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                else:
                    stored_datetime = stored_at
                
                current_time = datetime.now()
                hours_since_update = (current_time - stored_datetime).total_seconds() / 3600
                
                if hours_since_update < 24 and not force_update:
                    return {
                        "status": "fresh",
                        "message": f"Data is fresh (updated {hours_since_update:.1f} hours ago)",
                        "hours_since_update": hours_since_update,
                        "recommendation": "use_existing",
                        "ticker": ticker,
                        "stock_data": stock_data
                    }
                else:
                    return {
                        "status": "stale",
                        "message": f"Data is {hours_since_update:.1f} hours old",
                        "hours_since_update": hours_since_update,
                        "recommendation": "update_analysis",
                        "ticker": ticker,
                        "stock_data": stock_data
                    }
            else:
                return {
                    "status": "unknown_freshness",
                    "message": "Data found but timestamp unknown",
                    "recommendation": "use_existing",
                    "ticker": ticker,
                    "stock_data": stock_data
                }
                
        except Exception as e:
            logging.error(f"❌ Error checking database status: {e}")
            return {
                "status": "error",
                "message": f"Error checking database: {e}",
                "recommendation": "run_analysis",
                "ticker": ticker
            }
    
    def run_stock_analysis_if_needed(self, ticker: str, force_update: bool = False) -> Dict:
        """
        Check if stock data is fresh and available.
        Only returns success if data is fresh (< 24 hours old).
        
        Args:
            ticker (str): Stock ticker symbol
            force_update (bool): Force update even if recent data exists
            
        Returns:
            Dict: Analysis result and status
        """
        try:
            logging.info(f"🔄 Checking data freshness for ticker: {ticker}")
            
            # Check database status first
            db_status = self.check_database_status(ticker, force_update)
            
            if db_status["status"] == "fresh":
                logging.info(f"✅ Data is fresh for {ticker}")
                return {
                    "status": "success",
                    "message": "Data is fresh",
                    "stock_data": db_status["stock_data"],
                    "analysis_performed": False
                }
            
            else:
                logging.info(f"🔄 Data is stale for {ticker}, triggering update with locking...")
                
                # Use the new update locking method
                update_result = self.storage.update_if_stale_with_lock(ticker, self.collection_name, force_update)
                
                if update_result == "data_fresh":
                    logging.info(f"✅ Data became fresh during check for {ticker}")
                    # Get the fresh data
                    fresh_data = self.get_stock_data(ticker)
                    return {
                        "status": "success",
                        "message": "Data is fresh",
                        "stock_data": fresh_data,
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                elif update_result == "updated":
                    logging.info(f"✅ Successfully updated data for {ticker}")
                    # Get the updated data
                    updated_data = self.get_stock_data(ticker)
                    return {
                        "status": "success",
                        "message": "Data updated successfully",
                        "stock_data": updated_data,
                        "analysis_performed": True,
                        "update_result": update_result
                    }
                elif update_result == "waited_for_update":
                    logging.info(f"✅ Waited for another user to update {ticker}")
                    # Get the data that was updated by another user
                    updated_data = self.get_stock_data(ticker)
                    return {
                        "status": "success",
                        "message": "Data updated by another user",
                        "stock_data": updated_data,
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                elif update_result == "timeout":
                    logging.warning(f"⚠️ Timeout waiting for {ticker} update")
                    # Try to get whatever data is available
                    available_data = self.get_stock_data(ticker)
                    return {
                        "status": "partial_success",
                        "message": "Timeout waiting for update, using available data",
                        "stock_data": available_data,
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                else:
                    logging.error(f"❌ Update failed for {ticker}: {update_result}")
                    return {
                        "status": "error",
                        "message": f"Update failed: {update_result}",
                        "analysis_performed": False,
                        "update_result": update_result
                    }
                    
        except Exception as e:
            logging.error(f"❌ Error in run_stock_analysis_if_needed: {e}")
            return {
                "status": "error",
                "message": f"Error: {e}",
                "analysis_performed": False
            }
    
    async def process_natural_query(self, query: str, ticker: str = None, force_update: bool = False) -> str:
        """
        Process a natural language query about stock data with LLM ticker extraction.
        Uses LLM to extract ticker first, then uses it as constant throughout logic.
        
        Args:
            query (str): Natural language query
            ticker (str): Optional ticker symbol (will be extracted from query if not provided)
            force_update (bool): Force update even if recent data exists
            
        Returns:
            str: Response to the query
        """
        try:
            # STEP 1: Extract ticker using LLM (most important)
            if not ticker:
                logging.info(f"🔍 Using LLM to extract ticker from query: '{query}'")
                query_analysis = self._extract_ticker_and_info_from_query(query)
                ticker = query_analysis.get("ticker")
                
                if not ticker:
                    return "❌ Could not identify a stock ticker in your query. Please specify a ticker symbol."
            
            ticker = ticker.upper()
            logging.info(f"✅ Extracted ticker: {ticker}")
            logging.info(f"🔍 Processing query: '{query}' for ticker: {ticker}")
            
            # STEP 2: Check database status with extracted ticker
            db_status = self.check_database_status(ticker, force_update)
            
            # STEP 3: Use ticker as constant variable throughout all if/else logic
            if db_status["status"] == "fresh":
                logging.info(f"✅ Data is fresh for {ticker}, proceeding with analysis")
                stock_data = db_status["stock_data"]
                
                # Use LLM for analysis with fresh data
                try:
                    llm_response = await self.analyze_query_with_llm(query, stock_data)
                    return f"✅ Using fresh data for {ticker}. " + llm_response
                except Exception as e:
                    logging.warning(f"⚠️ LLM analysis failed: {e}")
                    # Provide dynamic response
                    dynamic_response = self._provide_dynamic_response(query, stock_data, "all_data", "all")
                    return f"✅ Using fresh data for {ticker}. " + dynamic_response
                    
            else:
                # Data is missing, stale, or unknown freshness - DIRECTLY CALL DB AGENT
                logging.info(f"📋 Data not fresh for {ticker} - directly calling DB Agent")
                return await self._call_db_agent_and_retry(ticker, query)
                
        except Exception as e:
            logging.error(f"❌ Error processing query: {e}")
            return f"❌ Error processing query: {e}"
    
    async def _call_db_agent_and_retry(self, ticker: str, query: str) -> str:
        """
        Directly call DB Agent to download data and then retry the query.
        Uses ticker as constant variable throughout.
        
        Args:
            ticker (str): Stock ticker symbol (constant variable)
            query (str): Original query
            
        Returns:
            str: Response after DB Agent call
        """
        try:
            logging.info(f"📥 Directly calling DB Agent for {ticker}")
            
            # Import and call DB Agent directly
            from Stock_Trend_DB_Agent import DatabaseStorage
            
            # Initialize DB Agent with same Redis config
            db_agent = DatabaseStorage(
                db_type="redis",
                host=self.redis_host,
                port=self.redis_port,
                username=self.redis_username,
                password=self.redis_password
            )
            
            # Call DB Agent with force_update=True for {ticker}
            success = await db_agent.download_and_store_ticker(
                ticker=ticker,
                collection_name=self.collection_name,
                force_update=True  # Force fresh analysis for {ticker}
            )
            
            db_agent.close()
            
            if success:
                logging.info(f"✅ DB Agent successfully downloaded {ticker} data")
                
                # Now retry the query with fresh data for {ticker}
                logging.info(f"🔄 Retrying query with fresh data for {ticker}")
                return await self._process_query_with_fresh_data(query, ticker)
            else:
                logging.error(f"❌ DB Agent failed to download {ticker} data")
                return f"❌ Failed to download data for {ticker}. Please try again later."
                
        except Exception as e:
            logging.error(f"❌ Error calling DB Agent for {ticker}: {e}")
            return f"❌ Error updating data for {ticker}: {e}"
    
    async def _process_query_with_fresh_data(self, query: str, ticker: str) -> str:
        """
        Process query with fresh data after DB Agent download.
        Uses ticker as constant variable throughout.
        
        Args:
            query (str): Original query
            ticker (str): Stock ticker symbol (constant variable)
            
        Returns:
            str: Response with fresh data
        """
        try:
            # Get fresh data from database for {ticker}
            stock_data = self.get_stock_data(ticker)
            
            if stock_data:
                logging.info(f"✅ Processing query with fresh data for {ticker}")
                
                # Use LLM for analysis with fresh data for {ticker}
                try:
                    llm_response = await self.analyze_query_with_llm(query, stock_data)
                    return f"🆕 Fresh data downloaded for {ticker}. " + llm_response
                except Exception as e:
                    logging.warning(f"⚠️ LLM analysis failed for {ticker}: {e}")
                    # Provide dynamic response for {ticker}
                    dynamic_response = self._provide_dynamic_response(query, stock_data, "all_data", "all")
                    return f"🆕 Fresh data downloaded for {ticker}. " + dynamic_response
            else:
                return f"❌ Failed to retrieve fresh data for {ticker}"
                
        except Exception as e:
            logging.error(f"❌ Error processing fresh data for {ticker}: {e}")
            return f"❌ Error processing fresh data for {ticker}: {e}"
    
    def _extract_ticker_and_info_from_query(self, query: str) -> Dict:
        """
        Extract ticker symbol and information type from natural language query using LLM.
        
        Args:
            query (str): Natural language query
            
        Returns:
            Dict: {"ticker": str, "info_type": str, "json_path": str}
        """
        logging.info(f"🔍 Extracting ticker and info from query: '{query}'")
        
        # Use LLM_Call_Agent's predefined function
        try:
            result = self.llm_agent.extract_ticker_and_info_from_query(query)
            return result
        except Exception as e:
            logging.warning(f"⚠️ LLM extraction failed: {e}")
            # Fallback to simple ticker extraction
            ticker = self._extract_ticker_with_regex(query)
            return {"ticker": ticker, "info_type": "all_data", "json_path": "all"}
    
    def _extract_ticker_from_query(self, query: str) -> Optional[str]:
        """
        Extract ticker symbol from natural language query using LLM.
        
        Args:
            query (str): Natural language query
            
        Returns:
            Optional[str]: Extracted ticker symbol or None
        """
        # Use the new method and just return the ticker
        result = self._extract_ticker_and_info_from_query(query)
        return result.get("ticker")
    
    def _parse_llm_ticker_response(self, response: str) -> Optional[str]:
        """Parse LLM response to extract ticker symbol."""
        if not response or response.upper() == "NONE":
            return None
        
        # Clean the response
        response = response.strip().upper()
        
        # Split by commas and clean each ticker
        tickers = []
        for ticker in response.split(','):
            ticker = ticker.strip()
            if ticker and len(ticker) <= 5 and ticker.isalpha():
                tickers.append(ticker)
        
        # Return first valid ticker
        return tickers[0] if tickers else None
    
    def _extract_ticker_with_regex(self, query: str) -> Optional[str]:
        """Fallback regex method for ticker extraction."""
        import re
        
        # Look for common ticker patterns - prioritize specific patterns first
        ticker_patterns = [
            r'ticker\s+([A-Z]{1,5})',  # "ticker AAPL"
            r'stock\s+([A-Z]{1,5})',   # "stock AAPL"
            r'([A-Z]{1,5})\s+stock',   # "AAPL stock"
            r'for\s+([A-Z]{1,5})',     # "for AAPL"
            r'about\s+([A-Z]{1,5})',   # "about AAPL"
            r'([A-Z]{1,5})\s+trend',   # "AAPL trend"
            r'([A-Z]{1,5})\s+analysis', # "AAPL analysis"
            r'([A-Z]{1,5})\s+performance', # "AAPL performance"
            r'\b([A-Z]{1,5})\b',       # Standalone tickers (last resort)
        ]
        
        for i, pattern in enumerate(ticker_patterns):
            match = re.search(pattern, query.upper())
            if match:
                ticker = match.group(1)
                logging.info(f"🔍 Regex pattern {i+1} matched: '{ticker}' from '{query.upper()}'")
                
                # Filter out common words that might be mistaken for tickers
                common_words = {'THE', 'AND', 'FOR', 'WITH', 'ABOUT', 'WHAT', 'HOW', 'WHY', 'WHEN', 'WHERE', 'IS', 'ARE', 'WAS', 'WERE', 'BEEN', 'BEING', 'HAVE', 'HAS', 'HAD', 'DO', 'DOES', 'DID', 'WILL', 'WOULD', 'COULD', 'SHOULD', 'CAN', 'MAY', 'MIGHT', 'MUST', 'SHALL', 'ABOUT', 'ABOVE', 'ACROSS', 'AFTER', 'AGAINST', 'ALONG', 'AMONG', 'AROUND', 'BEFORE', 'BEHIND', 'BELOW', 'BENEATH', 'BESIDE', 'BETWEEN', 'BEYOND', 'DURING', 'EXCEPT', 'INSIDE', 'NEAR', 'OFF', 'OVER', 'PAST', 'SINCE', 'THROUGH', 'THROUGHOUT', 'TOWARD', 'UNDER', 'UNDERNEATH', 'UNTIL', 'UP', 'UPON', 'WITHIN', 'WITHOUT', 'TREND', 'TRENDS', 'STOCK', 'STOCKS', 'SHARE', 'SHARES', 'PRICE', 'PRICES', 'MARKET', 'MARKETS', 'TRADING', 'TRADE', 'BUY', 'SELL', 'HOLD', 'RECENT', 'INSIGHT', 'FROM', 'CURRENT'}
                
                if ticker not in common_words:
                    logging.info(f"✅ Valid ticker found via regex: '{ticker}'")
                    return ticker
                else:
                    logging.info(f"❌ Ticker '{ticker}' filtered out as common word")
            else:
                logging.info(f"🔍 Regex pattern {i+1} did not match: '{pattern}'")
        
        logging.info(f"❌ No valid ticker found in query: '{query}'")
        return None
    
    def _provide_dynamic_response(self, query: str, stock_data: Dict, info_type: str, json_path: str) -> str:
        """
        Provide a dynamic response based on the specific information requested.
        
        Args:
            query (str): User query
            stock_data (Dict): Stock trend data
            info_type (str): Type of information requested
            json_path (str): JSON path to retrieve specific data
            
        Returns:
            str: Focused response based on user's request
        """
        ticker = stock_data.get('ticker', 'Unknown')
        
        # Get the specific data based on json_path
        if json_path == "current_trends":
            data = stock_data.get('current_trends', {})
            data_type = "Current Trends"
        elif json_path == "historical_trends":
            data = stock_data.get('historical_trends', {})
            data_type = "Historical Trends"
        elif json_path == "all":
            data = stock_data
            data_type = "All Data"
        else:
            data = stock_data.get('current_trends', {})
            data_type = "Current Trends"
        
        response = f"📊 **{info_type.replace('_', ' ').title()} Analysis for {ticker}**\n"
        response += "=" * 60 + "\n\n"
        
        # Metadata information
        response += f"**📅 Last Updated:** {stock_data.get('stored_at', 'Unknown')}\n"
        response += f"**📈 Data Type:** {data_type}\n"
        response += f"**🔍 Query:** {query}\n\n"
        
        # Current Trends with Time Intervals
        if data and json_path == "current_trends":
            response += "🔄 **CURRENT TRENDS (Ongoing):**\n"
            response += "-" * 40 + "\n"
            
            for trend_id, trend_data in data.items():
                time_info = trend_data.get('time', {})
                start_date = time_info.get('start', 'Unknown')
                end_date = time_info.get('end', 'Unknown')
                duration = trend_data.get('How Long it Take', 0)
                
                response += f"**{trend_id.upper()}**\n"
                response += f"⏰ **Time Period:** {start_date} to {end_date} ({duration} days)\n"
                response += f"📈 **Trend Type:** {'🟢 UPTREND' if 'uptrend' in trend_id else '🔴 DOWNTREND'}\n"
                response += f"📊 **Symbol:** {trend_data.get('symbol', 'N/A')}\n"
                response += f"💰 **Estimate Price:** ${trend_data.get('Estimate_price', 0):.2f}\n"
                response += f"📈 **Day Average Return:** {trend_data.get('day average_return', 0):.4f}\n"
                response += f"📊 **Slope:** {trend_data.get('Slope of stock trend', 0):.2f}\n"
                response += f"📈 **Max Return:** {trend_data.get('Max Return', 0):.4f}\n"
                response += f"📊 **Return Variance:** {trend_data.get('return rate variance', 0):.6f}\n"
                
                # Summary information
                summary = trend_data.get('summary', {})
                if summary:
                    response += f"🌍 **Macro Factors:** {summary.get('macro_reason', 'N/A')[:200]}...\n"
                    response += f"🏢 **Company Factors:** {summary.get('micro_reason', 'N/A')[:200]}...\n"
                
                response += "\n"
        
        # Historical Trends with Time Intervals
        if data and json_path == "historical_trends":
            response += "📚 **HISTORICAL TRENDS:**\n"
            response += "-" * 40 + "\n"
            
            # Sort historical trends by time (assuming they have time information)
            sorted_trends = sorted(data.items(), 
                                 key=lambda x: x[1].get('time', {}).get('start', 'Unknown'))
            
            for trend_id, trend_data in sorted_trends[:5]:  # Show first 5 for brevity
                time_info = trend_data.get('time', {})
                start_date = time_info.get('start', 'Unknown')
                end_date = time_info.get('end', 'Unknown')
                duration = trend_data.get('How Long it Take', 0)
                
                response += f"**{trend_id.upper()}**\n"
                response += f"⏰ **Time Period:** {start_date} to {end_date} ({duration} days)\n"
                response += f"📈 **Trend Type:** {'🟢 UPTREND' if 'uptrend' in trend_id else '🔴 DOWNTREND'}\n"
                response += f"📊 **Symbol:** {trend_data.get('symbol', 'N/A')}\n"
                response += f"💰 **Estimate Price:** ${trend_data.get('Estimate_price', 0):.2f}\n"
                response += f"📈 **Day Average Return:** {trend_data.get('day average_return', 0):.4f}\n"
                response += f"📊 **Slope:** {trend_data.get('Slope of stock trend', 0):.2f}\n"
                response += f"📈 **Max Return:** {trend_data.get('Max Return', 0):.4f}\n"
                
                # Summary information (shorter for historical)
                summary = trend_data.get('summary', {})
                if summary:
                    response += f"🌍 **Macro:** {summary.get('macro_reason', 'N/A')[:100]}...\n"
                    response += f"🏢 **Company:** {summary.get('micro_reason', 'N/A')[:100]}...\n"
                
                response += "\n"
            
            if len(data) > 5:
                response += f"... and {len(data) - 5} more historical trends\n\n"
        
        # Query information
        response += f"🔍 **Query:** {query}\n"
        response += "💡 *For detailed LLM analysis with function calling, please configure OpenAI API key.*\n"
        
        return response
    

    
    def close(self):
        """Close the database connection."""
        self.storage.close()
        logging.info("🔚 Stock Trend Analyst Agent closed")


def main():
    """Main function to handle command line arguments and execute queries."""
    parser = argparse.ArgumentParser(description='Stock Trend Analyst Agent - Natural Language Query Interface')
    
    # Database arguments
    parser.add_argument('--redis-host', default='redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com',
                       help='Redis host')
    parser.add_argument('--redis-port', type=int, default=16376, help='Redis port')
    parser.add_argument('--redis-username', default='default', help='Redis username')
    parser.add_argument('--redis-password', default='rl8242B4UItBhFzgHW5APEqZnkYoaEZv', help='Redis password')
    parser.add_argument('--collection', default='Stock_Trend_INFOS', help='Redis collection name')
    
    # Query arguments
    parser.add_argument('--query', help='Natural language query about stock data')
    parser.add_argument('--ticker', help='Stock ticker symbol')
    parser.add_argument('--list-tickers', action='store_true', help='List all available tickers')
    parser.add_argument('--force-update', action='store_true', help='Force update even if recent data exists')
    
    # OpenAI arguments
    parser.add_argument('--openai-key', help='OpenAI API key for LLM analysis (optional, will auto-import from Stock_Trend_Storage_Agent if not provided)')
    
    # Interactive mode
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    try:
        # Initialize agent
        agent = StockTrendAnalystAgent(
            redis_host=args.redis_host,
            redis_port=args.redis_port,
            redis_username=args.redis_username,
            redis_password=args.redis_password,
            collection_name=args.collection,
            openai_api_key=args.openai_key
        )
        
        # List tickers if requested
        if args.list_tickers:
            tickers = agent.list_available_tickers()
            if tickers:
                print(f"\n📋 Available tickers: {', '.join(tickers)}")
            else:
                print("\nℹ️ No tickers found in database")
            return
        
        # Process single query
        if args.query:
            response = agent.process_natural_query(args.query, args.ticker)
            print(f"\n🤖 Response:\n{response}")
            return
        
        # Interactive mode
        if args.interactive:
            print("\n🤖 Stock Trend Analyst Agent - Interactive Mode")
            print("Type 'quit' to exit, 'list' to see available tickers")
            print("=" * 60)
            
            while True:
                try:
                    query = input("\n💬 Enter your query: ").strip()
                    
                    if query.lower() in ['quit', 'exit', 'q']:
                        break
                    elif query.lower() == 'list':
                        tickers = agent.list_available_tickers()
                        if tickers:
                            print(f"📋 Available tickers: {', '.join(tickers)}")
                        else:
                            print("ℹ️ No tickers found in database")
                        continue
                    elif not query:
                        continue
                    
                    response = agent.process_natural_query(query)
                    print(f"\n🤖 Response:\n{response}")
                    
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
        
        # Default: show help
        if not any([args.query, args.list_tickers, args.interactive]):
            print("🤖 Stock Trend Analyst Agent")
            print("Use --query to ask a question, --interactive for chat mode, or --list-tickers to see available data")
            print("\nExamples:")
            print("  python Stock_Trend_Analyst_Agent.py --query 'What is the current trend for AAPL?'")
            print("  python Stock_Trend_Analyst_Agent.py --interactive")
            print("  python Stock_Trend_Analyst_Agent.py --list-tickers")
    
    except Exception as e:
        logging.error(f"❌ Critical error: {e}")
        sys.exit(1)
    finally:
        if 'agent' in locals():
            agent.close()


if __name__ == "__main__":
    # Example usage
    # python Stock_Trend_Analyst_Agent.py --query "What is the current trend for AAPL?"
    # python Stock_Trend_Analyst_Agent.py --interactive
    # python Stock_Trend_Analyst_Agent.py --list-tickers
    # python Stock_Trend_Analyst_Agent.py --query "Analyze AAPL trends" --ticker AAPL
    
    main() 