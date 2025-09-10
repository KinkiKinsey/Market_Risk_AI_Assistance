#!/usr/bin/env python3
"""
Revenue Segmentation Analyst Agent
A natural language interface for querying revenue segmentation data from Redis database.
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
from Revenue_Segmentation_DB_Agent import RevenueSegmentationDatabaseStorage
from LLM_Call_Agent import LLMCallAgent
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('revenue_segmentation_analyst.log')
    ]
)

@dataclass
class RevenueSegment:
    """Data class for revenue segment information."""
    name: str
    percentage_of_total_revenue: str
    revenue_amount: str
    target_customer_or_revenue_method: str
    customer_segment_detail: str
    usage: str

class RevenueSegmentationAnalystAgent:
    """
    Natural language interface for querying revenue segmentation data from Redis database.
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, redis_username: str = "default", 
                 redis_password: str = None, collection_name: str = "Revenue_Segmentation_INFOS",
                 openai_api_key: str = None):
        """
        Initialize the Revenue Segmentation Analyst Agent.
        
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
            self.shared_clients = shared_clients
            self.redis_client = shared_clients.get_stock_trend_redis()
            self.storage = RevenueSegmentationDatabaseStorage(
                db_type="redis",
                shared_clients=shared_clients
            )
            # Set fallback attributes for compatibility
            self.redis_host = None
            self.redis_port = None
            self.redis_username = "default"
            self.redis_password = None
            self.collection_name = collection_name
            self.openai_api_key = openai_api_key
            logging.info("✅ Using shared Redis connection")
        else:
            # Use individual Redis connection
            self.shared_clients = None
            self.redis_host = redis_host
            self.redis_port = redis_port
            self.redis_username = redis_username
            self.redis_password = redis_password
            self.collection_name = collection_name
            self.openai_api_key = openai_api_key
            
            # Initialize database storage
            self.storage = RevenueSegmentationDatabaseStorage(
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
                raise Exception("❌ Shared clients not available and no fallback provided")
        
        logging.info("🤖 Revenue Segmentation Analyst Agent initialized")
        logging.info(f"   - Redis: {self.redis_host}:{self.redis_port}" if self.redis_host else "   - Redis: Shared Connection")
        logging.info(f"   - Collection: {self.collection_name}")
    
    async def get_revenue_segmentation_data(self, ticker: str) -> Optional[Dict]:
        """
        Get revenue segmentation data for a ticker from Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Optional[Dict]: Revenue segmentation data or None if not found
        """
        try:
            logging.info(f"📈 Retrieving revenue segmentation data for {ticker}")
            
            # Create Redis key - use same format as DB Agent
            redis_key = f"{self.collection_name}:{ticker.upper()}_revenue_segmentation"
            logging.info(f"   - Redis key: {redis_key}")
            
            # Get data from Redis
            stored_data = await self.redis_client.get(redis_key)
            
            if stored_data:
                data = json.loads(stored_data)
                logging.info(f"✅ Found revenue segmentation data for {ticker}")
                logging.info(f"   - Revenue segments: {len(data.get('revenue_segmentation', {}).get('business_segments', []))}")
                logging.info(f"   - Last update: {data.get('metadata', {}).get('last_update', 'Unknown')}")
                return data
            else:
                logging.info(f"📭 No revenue segmentation data found for {ticker}")
                return None
                
        except Exception as e:
            logging.error(f"❌ Error retrieving data for {ticker}: {e}")
            return None
    
    def list_available_tickers(self) -> List[str]:
        """
        List all tickers with revenue segmentation data.
        
        Returns:
            List[str]: List of ticker symbols
        """
        try:
            logging.info("📋 Listing available tickers")
            
            # Get all keys matching the pattern - use same format as DB Agent
            pattern = f"{self.collection_name}:*_revenue_segmentation"
            keys = self.redis_client.keys(pattern)
            
            # Extract ticker symbols from keys
            tickers = []
            for key in keys:
                ticker = key.split(':')[1].replace('_revenue_segmentation', '')
                tickers.append(ticker)
            
            logging.info(f"✅ Found {len(tickers)} tickers with revenue segmentation data")
            return sorted(tickers)
            
        except Exception as e:
            logging.error(f"❌ Error listing tickers: {e}")
            return []
    
    def _parse_revenue_segment(self, segment_data: Dict) -> RevenueSegment:
        """
        Parse revenue segment data into RevenueSegment object.
        
        Args:
            segment_data (Dict): Raw segment data
            
        Returns:
            RevenueSegment: Parsed segment object
        """
        return RevenueSegment(
            name=segment_data.get('name', 'Unknown'),
            percentage_of_total_revenue=segment_data.get('percentage_of_total_revenue', '0%'),
            revenue_amount=segment_data.get('Revenue Amount', 'Unknown'),
            target_customer_or_revenue_method=segment_data.get('target_customer_or_revenue_method', 'Unknown'),
            customer_segment_detail=segment_data.get('Segment of these customers, in very detail', 'Unknown'),
            usage=segment_data.get('Usage', 'Unknown')
        )
    
    def get_revenue_segments_info(self, include_details: bool = True) -> Dict:
        """
        Get information about revenue segments.
        
        Args:
            include_details (bool): Include detailed segment information
            
        Returns:
            Dict: Revenue segments information
        """
        try:
            # This would be called with specific ticker data
            # For now, return structure
            return {
                "total_segments": 0,
                "segments": [],
                "total_revenue": "Unknown",
                "largest_segment": None,
                "smallest_segment": None
            }
        except Exception as e:
            logging.error(f"❌ Error getting revenue segments info: {e}")
            return {}
    
    def get_business_segments(self, segment_type: str = "all", include_analysis: bool = True) -> Dict:
        """
        Get business segments with optional filtering.
        
        Args:
            segment_type (str): Type of segments to retrieve ("all", "high_revenue", "low_revenue")
            include_analysis (bool): Include LLM analysis
            
        Returns:
            Dict: Business segments data
        """
        try:
            # This would be called with specific ticker data
            return {
                "segment_type": segment_type,
                "segments": [],
                "analysis": None if not include_analysis else "LLM analysis would go here"
            }
        except Exception as e:
            logging.error(f"❌ Error getting business segments: {e}")
            return {}
    
    def compare_segments(self, comparison_type: str) -> Dict:
        """
        Compare different revenue segments.
        
        Args:
            comparison_type (str): Type of comparison ("revenue", "customer", "usage")
            
        Returns:
            Dict: Comparison results
        """
        try:
            return {
                "comparison_type": comparison_type,
                "results": [],
                "insights": []
            }
        except Exception as e:
            logging.error(f"❌ Error comparing segments: {e}")
            return {}
    
    def get_segment_statistics(self, statistic_type: str, segment_filter: str = "all") -> Dict:
        """
        Get statistics about revenue segments.
        
        Args:
            statistic_type (str): Type of statistics ("revenue_distribution", "customer_analysis", "growth")
            segment_filter (str): Filter for segments
            
        Returns:
            Dict: Statistics data
        """
        try:
            return {
                "statistic_type": statistic_type,
                "filter": segment_filter,
                "data": {},
                "summary": ""
            }
        except Exception as e:
            logging.error(f"❌ Error getting segment statistics: {e}")
            return {}
    
    async def analyze_query_with_llm(self, query: str, revenue_data: Dict) -> str:
        """
        Analyze revenue segmentation query using LLM.
        
        Args:
            query (str): Natural language query
            revenue_data (Dict): Revenue segmentation data
            
        Returns:
            str: LLM-generated response
        """
        try:
            logging.info(f"🤖 Analyzing query with LLM: '{query}'")
            
            ticker = revenue_data.get('ticker', 'Unknown')
            revenue_segmentation = revenue_data.get('revenue_segmentation', {})
            metadata = revenue_data.get('metadata', {})
            
            # Create focused prompt for revenue segmentation analysis
            prompt = f"""
Analyze this revenue segmentation data to provide a simple business impact assessment.

USER QUERY: "{query}"
TICKER: {ticker}

REVENUE SEGMENTATION DATA:
- Business Segments: {len(revenue_segmentation.get('business_segments', []))} segments
- Last Updated: {metadata.get('last_update', 'Unknown')}
- Next Earnings Date: {metadata.get('next_earnings_date', 'Unknown')}

REVENUE SEGMENTS:
{json.dumps(revenue_segmentation.get('business_segments', []), indent=2)[:3000]}...

METADATA:
{json.dumps(metadata, indent=2)[:1000]}...

**REQUIRED OUTPUT FORMAT - REVENUE SEGMENTATION ANALYSIS:**

**PART 1: REVENUE SEGMENTATION BREAKDOWN**
Report the actual revenue segmentation percentages for each business line:

• **Business Line Name**: XX% of total revenue
• **Business Line Name**: XX% of total revenue
• **Business Line Name**: XX% of total revenue

**PART 2: IMPACTED BUSINESS LINES**
Based on the news/policy/event mentioned, identify which business lines are impacted:

• **Impacted Business Line**: [Brief explanation of how this business line is affected]
• **Impacted Business Line**: [Brief explanation of how this business line is affected]

**RULES:**
1. Part 1: Report ONLY the actual percentage from the data (no guessing)
2. Part 2: Only mention business lines that are actually impacted by the event
3. NO percentage impact estimates - just identify which lines are affected
4. Use bullet points (•) for each segment
5. Be specific about which business lines are impacted and why
6. NO recommendations or strategic advice
7. Base all analysis on the actual revenue segmentation data provided

**CONCLUSION FORMAT:**
Total Revenue Segments: X business lines
Impacted Business Lines: X business lines affected by the event

Analyze how the news/policy/event affects each revenue segment's business operations."""

            # Use shared clients semaphore-controlled async LLM call
            try:
                from shared_clients import shared_clients
                response = await shared_clients.call_deepseek(
                    prompt=prompt,
                    system_message="You are a specialized revenue segmentation analyst. Provide evidence-based analysis using the provided data.",
                    max_tokens=1000,
                    temperature=0.2
                )
            except Exception as e:
                # Fallback to direct LLM call if shared clients fail
                response = self.llm_agent.call_llm(
                    prompt=prompt,
                    system_message="You are a specialized revenue segmentation analyst. Provide evidence-based analysis using the provided data.",
                    max_tokens=1000,
                    temperature=0.2
                )
            
            logging.info(f"✅ LLM analysis completed for {ticker}")
            return response
            
        except Exception as e:
            logging.error(f"❌ LLM analysis failed: {e}")
            return f"❌ Error analyzing revenue data: {str(e)}"
    
    async def run_revenue_analysis_if_needed(self, ticker: str) -> str:
        """
        Check if revenue segmentation data needs updating and call DB Agent if needed.
        Uses the same pattern as Stock Trend Read Agent with update locking.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            str: Update result status
        """
        try:
            logging.info(f"🔍 Checking if revenue analysis needed for {ticker}")
            
            # Call DB Agent's get_or_download method (which handles update logic)
            from Revenue_Segmentation_DB_Agent import RevenueSegmentationDatabaseStorage
            
            if self.shared_clients:
                db_agent = RevenueSegmentationDatabaseStorage(
                    db_type="redis",
                    shared_clients=self.shared_clients
                )
            else:
                db_agent = RevenueSegmentationDatabaseStorage(
                    db_type="redis",
                    host=self.redis_host,
                    port=self.redis_port,
                    username=self.redis_username,
                    password=self.redis_password
                )
            
            # Use DB Agent's update logic (same as Stock Trend pattern)
            result = await db_agent.get_or_download_revenue_segmentation(
                ticker=ticker,
                collection_name=self.collection_name
            )
            
            db_agent.close()
            
            if result:
                logging.info(f"✅ Revenue analysis data available for {ticker}")
                return "data_fresh"
            else:
                logging.info(f"❌ Failed to get revenue analysis data for {ticker}")
                return "error"
                
        except Exception as e:
            logging.error(f"❌ Error running revenue analysis for {ticker}: {e}")
            return "error"
    
    async def process_natural_query(self, query: str, ticker: str = None) -> str:
        """
        Process a natural language query about revenue segmentation data with LLM ticker extraction.
        Uses the same pattern as Stock Trend Read Agent: calls DB Agent for updates.
        
        Args:
            query (str): Natural language query
            ticker (str): Optional ticker symbol (will be extracted from query if not provided)
            
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
            
            # STEP 2: Run revenue analysis if needed (same as Stock Trend pattern)
            update_result = await self.run_revenue_analysis_if_needed(ticker)
            
            # STEP 3: Process query with available data
            if update_result == "data_fresh":
                logging.info(f"✅ Data is fresh for {ticker}, proceeding with analysis")
                
                # Get data from database
                revenue_data = await self.get_revenue_segmentation_data(ticker)
                
                if revenue_data:
                    # Use LLM for analysis with fresh data
                    try:
                        llm_response = await self.analyze_query_with_llm(query, revenue_data)
                        return f"✅ Using fresh data for {ticker}. " + llm_response
                    except Exception as e:
                        logging.warning(f"⚠️ LLM analysis failed: {e}")
                        # Provide dynamic response
                        dynamic_response = self._provide_dynamic_response(query, revenue_data, "all_data", "all")
                        return f"✅ Using fresh data for {ticker}. " + dynamic_response
                else:
                    return f"❌ Failed to retrieve data for {ticker} after update"
            else:
                logging.error(f"❌ Failed to get fresh data for {ticker}")
                return f"❌ Failed to get fresh data for {ticker}. Please try again later."
                
        except Exception as e:
            logging.error(f"❌ Error processing query: {e}")
            return f"❌ Error processing query: {e}"
    
    # Method removed - now using run_revenue_analysis_if_needed() pattern like Stock Trend Read Agent
    
    # Method removed - now using direct database access after run_revenue_analysis_if_needed()
    
    def _extract_ticker_and_info_from_query(self, query: str) -> Dict:
        """
        Extract ticker symbol and information type from natural language query.
        Uses LLM for maximum precision and reliability.
        
        Args:
            query (str): Natural language query
            
        Returns:
            Dict: {"ticker": str, "info_type": str, "json_path": str}
        """
        logging.info(f"🔍 LLM extracting ticker and info from query: '{query}'")
        
        prompt = f"""
Analyze this revenue segmentation query and extract the ticker symbol and information type:

Query: "{query}"

Available info_types:
- revenue_segments: Revenue segmentation analysis
- business_segments: Business segment details
- customer_analysis: Customer segment analysis
- revenue_distribution: Revenue distribution analysis
        - metadata: Metadata information including next earnings date
- all_data: Complete revenue segmentation information

Available json_paths:
- revenue_segmentation: Access revenue segmentation data
        - metadata: Access metadata including next earnings date
- all: Access all available data

Examples:
- "What are AAPL's revenue segments?" → ticker: "AAPL", info_type: "revenue_segments", json_path: "revenue_segmentation"
- "Show me TSLA's business segments" → ticker: "TSLA", info_type: "business_segments", json_path: "revenue_segmentation"
- "What's the revenue distribution for NVDA?" → ticker: "NVDA", info_type: "revenue_distribution", json_path: "revenue_segmentation"

Return a JSON response with this exact format:
{{
    "ticker": "AAPL",
    "info_type": "revenue_segments",
    "json_path": "revenue_segmentation",
    "confidence": 0.9
}}

Return ONLY the JSON, nothing else:"""

        try:
            response = self.llm_agent.call_llm(
                prompt=prompt,
                system_message="You are a revenue segmentation query analyzer. Extract ticker and information type, return JSON only.",
                max_tokens=200,
                temperature=0.1
            )
            
            # Parse JSON response (handle markdown code blocks)
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            cleaned_response = cleaned_response.strip()
            result = json.loads(cleaned_response)
            
            if result.get("ticker") and result.get("info_type") and result.get("json_path"):
                confidence = result.get("confidence", 0.8)
                logging.info(f"✅ LLM extracted: ticker='{result['ticker']}', info_type='{result['info_type']}', json_path='{result['json_path']}', confidence={confidence}")
                return result
            else:
                logging.error(f"❌ LLM response missing required fields: {result}")
                raise Exception("LLM response missing required fields")
                
        except Exception as e:
            logging.error(f"❌ LLM extraction failed: {e}")
            logging.info("🔄 Falling back to regex extraction...")
            return self._extract_ticker_fallback(query)
    
    def _extract_ticker_fallback(self, query: str) -> Dict:
        """Fallback method using regex when LLM extraction fails"""
        # Extract ticker with regex
        ticker_patterns = [
            r'for\s+([A-Z]{1,5})\b',
            r'([A-Z]{1,5})\s+(?:revenue|segments|business)',
            r'\b([A-Z]{1,5})\b'
        ]
        
        ticker = None
        for pattern in ticker_patterns:
            match = re.search(pattern, query.upper())
            if match:
                ticker = match.group(1)
                break
        
        # Determine info type from query
        info_type = "all_data"
        if "revenue" in query.lower():
            info_type = "revenue_segments"
        elif "business" in query.lower():
            info_type = "business_segments"
        elif "customer" in query.lower():
            info_type = "customer_analysis"
        elif "earnings" in query.lower():
            info_type = "metadata"
        
        json_path = "revenue_segmentation" if info_type != "metadata" else "metadata"
        if info_type == "all_data":
            json_path = "all"
        
        return {
            "ticker": ticker,
            "info_type": info_type,
            "json_path": json_path,
            "confidence": 0.3  # Lower confidence for regex fallback
        }
    
    def _provide_dynamic_response(self, query: str, revenue_data: Dict, info_type: str, json_path: str) -> str:
        """
        Provide dynamic response when LLM analysis fails.
        
        Args:
            query (str): User query
            revenue_data (Dict): Revenue segmentation data
            info_type (str): Type of information requested
            json_path (str): JSON path to access data
            
        Returns:
            str: Dynamic response
        """
        try:
            ticker = revenue_data.get('ticker', 'Unknown')
            revenue_segmentation = revenue_data.get('revenue_segmentation', {})
            business_segments = revenue_segmentation.get('business_segments', [])
            
            if not business_segments:
                return f"❌ No revenue segmentation data available for {ticker}"
            
            # Create a simple summary
            total_segments = len(business_segments)
            largest_segment = max(business_segments, key=lambda x: float(x.get('percentage_of_total_revenue', '0%').replace('%', '').replace('Guess ', '').replace('%', '')) if x.get('percentage_of_total_revenue') else 0)
            
            response = f"📊 Revenue Segmentation Summary for {ticker}:\n\n"
            response += f"• Total Business Segments: {total_segments}\n"
            response += f"• Largest Segment: {largest_segment.get('name', 'Unknown')} ({largest_segment.get('percentage_of_total_revenue', 'Unknown')})\n"
            response += f"• Revenue Amount: {largest_segment.get('Revenue Amount', 'Unknown')}\n\n"
            
            response += "🔍 Key Segments:\n"
            for i, segment in enumerate(business_segments[:5], 1):  # Show top 5
                response += f"{i}. {segment.get('name', 'Unknown')} - {segment.get('percentage_of_total_revenue', 'Unknown')}\n"
            
            if len(business_segments) > 5:
                response += f"... and {len(business_segments) - 5} more segments\n"
            
            return response
            
        except Exception as e:
            logging.error(f"❌ Error providing dynamic response: {e}")
            return f"❌ Error analyzing revenue data: {str(e)}"
    
    def close(self):
        """Close database connections."""
        if hasattr(self, 'storage'):
            self.storage.close()
        if hasattr(self, 'redis_client'):
            try:
                # For shared Redis connections, we don't need to close them manually
                # as they're managed by the shared client pool
                logging.info("🔌 Redis connection closed")
            except Exception as e:
                logging.warning(f"⚠️ Error closing Redis connection: {e}")
        logging.info("🔌 Revenue Segmentation Analyst Agent connections closed")


def main():
    """Main function to handle command line arguments and execute queries."""
    parser = argparse.ArgumentParser(description='Revenue Segmentation Analyst Agent - Natural Language Query Interface')
    
    # Database arguments
    parser.add_argument('--redis-host', default='redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com',
                       help='Redis host')
    parser.add_argument('--redis-port', type=int, default=16376, help='Redis port')
    parser.add_argument('--redis-username', default='default', help='Redis username')
    parser.add_argument('--redis-password', default='rl8242B4UItBhFzgHW5APEqZnkYoaEZv', help='Redis password')
    parser.add_argument('--collection', default='Revenue_Segmentation_INFOS', help='Redis collection name')
    
    # Query arguments
    parser.add_argument('--query', help='Natural language query about revenue segmentation data')
    parser.add_argument('--ticker', help='Stock ticker symbol')
    parser.add_argument('--list-tickers', action='store_true', help='List all available tickers')
    
    # OpenAI arguments
    parser.add_argument('--openai-key', help='OpenAI API key for LLM analysis (optional, will auto-import from Stock_Trend_Storage_Agent if not provided)')
    
    # Interactive mode
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    try:
        # Initialize agent
        agent = RevenueSegmentationAnalystAgent(
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
            print("\n🤖 Revenue Segmentation Analyst Agent - Interactive Mode")
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
            print("🤖 Revenue Segmentation Analyst Agent")
            print("Use --query to ask a question, --interactive for chat mode, or --list-tickers to see available data")
            print("\nExamples:")
            print("  python Revenue_Segmentation_Read_Agent.py --query 'What are AAPL revenue segments?'")
            print("  python Revenue_Segmentation_Read_Agent.py --interactive")
            print("  python Revenue_Segmentation_Read_Agent.py --list-tickers")
    
    except Exception as e:
        logging.error(f"❌ Critical error: {e}")
        sys.exit(1)
    finally:
        if 'agent' in locals():
            agent.close()


if __name__ == "__main__":
    # Example usage
    # python Revenue_Segmentation_Read_Agent.py --query "What are AAPL revenue segments?"
    # python Revenue_Segmentation_Read_Agent.py --interactive
    # python Revenue_Segmentation_Read_Agent.py --list-tickers
    # python Revenue_Segmentation_Read_Agent.py --query "Analyze AAPL revenue" --ticker AAPL
    
    main()
