#!/usr/bin/env python3
"""
Financial Metrics Read Agent
A natural language interface for querying financial metrics data from Redis database.
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
from Financial_Metrics_DB_Agent import FinancialMetricsDatabaseStorage
from LLM_Call_Agent import LLMCallAgent
import re
from dataclasses import dataclass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('financial_metrics_read_agent.log')
    ]
)

@dataclass
class FinancialMetricsData:
    """Data class for financial metrics information."""
    ticker: str
    financial_metrics: Dict
    dcf_data: Dict
    price_data: Dict
    metadata: Dict

class FinancialMetricsReadAgent:
    """
    Natural language interface for querying financial metrics data from Redis database.
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, redis_username: str = "default", 
                 redis_password: str = None, collection_name: str = "Financial_Metrics_INFOS",
                 openai_api_key: str = None):
        """
        Initialize the Financial Metrics Read Agent.
        
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
            self.storage = FinancialMetricsDatabaseStorage(
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
            self.storage = FinancialMetricsDatabaseStorage(
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
        
        logging.info(f"✅ Financial Metrics Read Agent initialized")
        logging.info(f"   - Redis: {redis_host}:{redis_port}")
        logging.info(f"   - Collection: {collection_name}")
        logging.info(f"   - LLM Provider: deepseek")
    
    async def get_financial_metrics_data(self, ticker: str) -> Optional[Dict]:
        """
        Get financial metrics data for a specific ticker.
        Uses the DB Agent's proper update logic instead of direct download.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Optional[Dict]: Financial metrics data or None if not found
        """
        try:
            # Use the DB Agent's proper update logic instead of direct download
            return await self.storage.get_or_download_financial_metrics(ticker, self.collection_name)
                    
        except Exception as e:
            logging.error(f"❌ Error in get_financial_metrics_data for {ticker}: {e}")
            return None
    
    def list_available_tickers(self) -> List[str]:
        """
        List all available tickers with financial metrics data.
        
        Returns:
            List[str]: List of available ticker symbols
        """
        try:
            tickers = self.storage.list_financial_metrics_tickers(self.collection_name)
            logging.info(f"✅ Found {len(tickers)} tickers with financial metrics data")
            return tickers
        except Exception as e:
            logging.error(f"❌ Error listing tickers: {e}")
            return []
    
    async def validate_analysis_agent(self, prompt: str, financial_metrics: Dict) -> str:
        """
        Simple LLM function to analyze financial metrics using centralized LLM agent.
        This is the same function from your Financial_Metric.ipynb.
        
        Args:
            prompt (str): The analysis prompt/question
            financial_metrics (dict): Financial data to analyze
        
        Returns:
            str: LLM analysis result
        """
        try:
            # Format the financial metrics for the prompt
            metrics_text = json.dumps(financial_metrics, indent=2)
            
            full_prompt = f"""
            You are a financial analyst AI. 
            Your main job is to determine whether the company is in a healthy financial situation with good valuation.

            User Query::
            {prompt}
            
            Financial Data:
            {metrics_text}
            
            IMPORTANT ANALYSIS GUIDELINES:

            1. PRIMARY VALUATION ASSESSMENT (DCF ONLY):
               - VALUATION DECISIONS (overvalued/undervalued) should ONLY be based on DCF (Discounted Cash Flow) analysis
               - DCF is the PRIMARY and ONLY tool for determining if a stock is overvalued or undervalued
               - Use Fair Value Band (±10–20%): Many analysts treat a stock within 10–20% above or below DCF as "reasonably valued"
               - PE ratios and other metrics are for REFERENCE and SECTOR CONTEXT only, NOT for valuation decisions

            2. SECTOR-SPECIFIC FINANCIAL METRICS CONTEXT (For Reference Only):

               TECHNOLOGY (High-Growth/Software/AI/Semiconductors):
               - Typical PE Range: 20x–30x (exception: early-stage SaaS/AI can trade at 30x–60x+)
               - DCF Discount Rate: 8–10%
               - Sector Context: High reinvestment, growth-weighted multiples, innovation premium
               - Example: "AAPL (Tech sector): PE 23x, within typical tech range of 20-30x"

               HEALTHCARE/BIOTECH:
               - Mature Pharma/MedTech PE: 15x–25x
               - Biotech (pre-profit): Often valued on EV/sales (5x–10x) rather than PE
               - DCF Discount Rate: 9–12%
               - Sector Context: Pipeline-driven, regulatory risk, defensive characteristics

               FINANCIALS (Banks, Insurance, Asset Managers):
               - PE Range: 8x–14x
               - P/BV (Price/Book): 0.8x–1.5x is normal
               - Sector Context: Interest rate sensitive, cyclical, regulatory environment

               ENERGY (Oil & Gas, Renewables):
               - PE Range: 8x–12x
               - EV/EBITDA: 4x–7x
               - Sector Context: Commodity price dependent, cyclical, infrastructure intensive

               INDUSTRIALS/MANUFACTURING:
               - PE Range: 12x–18x
               - EV/EBITDA: 6x–10x
               - Sector Context: Economic cycle dependent, capital intensive, global trade exposure

               CONSUMER DISCRETIONARY (Retail, Autos, Luxury):
               - PE Range: 15x–22x
               - Sector Context: Economic sensitivity, brand value, discretionary spending patterns

               CONSUMER STAPLES (Food, Beverage, Household Goods):
               - PE Range: 18x–25x
               - Sector Context: Defensive, stable demand, brand loyalty, inflation resistance

               UTILITIES:
               - PE Range: 12x–18x
               - P/BV: 1.0x–1.5x
               - Sector Context: Regulated returns, stable cash flows, infrastructure assets

               REAL ESTATE (REITs):
               - Valuation Metric: P/FFO (Funds From Operations) = 12x–20x
               - Sector Context: Property market cycles, interest rate sensitivity, geographic diversification

               TELECOM/MEDIA:
               - PE Range: 10x–18x
               - EV/EBITDA: 5x–9x
               - Sector Context: Infrastructure heavy, regulatory environment, technology disruption

            3. VALUATION BANDS BY COMPANY TYPE (DCF only):
               - Growth & Momentum Stocks: Can trade 50–200% above DCF for long stretches (e.g., Tesla, Nvidia during growth surges)
                 * Market prices in optionality, new markets, and narrative beyond base-case cash flows
               - Mature/Stable Companies: Often stay within ±10–30% of DCF since future cash flows are more predictable
               - Deep Value/Distressed: Can trade 40–70% below DCF if markets doubt assumptions (high risk, recession fears, governance issues)

            4. FINANCIAL HEALTH ANALYSIS (Other metrics):
               - Other metrics (ROE, ROA, ROIC, debt ratios, cash flow, etc.) are for analyzing FINANCIAL HEALTH, NOT valuation
               - Use these metrics to assess whether the company is financially sound, profitable, and stable
               - Financial health supports valuation but doesn't determine fair value

            5. COMPANY SECTOR ANALYSIS (NEW FEATURE):
               - Use the ticker_description data to identify the company's sector and business description
               - Report financial metrics in sector context (e.g., "AAPL (Tech sector): PE 23x, ROE 15%, within typical tech ranges")
               - Consider the company's business model and industry characteristics
               - Factor in sector-specific growth expectations and risk profiles

            6. ANALYSIS REQUIREMENTS:
               - Keep your response under 200 words
               - PRIMARY VALUATION: Use ONLY DCF to determine overvalued/undervalued status
               - SECTOR CONTEXT: Report PE, ROE, and other metrics in sector context for reference
               - FINANCIAL HEALTH: Use other metrics only for financial health assessment
               - Provide actionable insights and clear conclusions
               - Use bullet points or short paragraphs for readability
               - Avoid unnecessary technical jargon
               - ALWAYS lead with DCF-based valuation decision
               - Then provide sector context for other metrics
               - Example format: "VALUATION: Overvalued (DCF $100 vs price $120). SECTOR CONTEXT: AAPL (Tech): PE 23x, ROE 15% - within typical tech ranges."

            Please provide a clear, concise analysis based on the above financial data and guidelines.
            """
            
            # Use shared clients semaphore-controlled async LLM call
            try:
                from shared_clients import shared_clients
                response = await shared_clients.call_deepseek(
                    prompt=full_prompt,
                    system_message="You are a financial analyst AI. Provide clear, insightful analysis of financial data in under 200 words.",
                    max_tokens=300,  # Reduced to help enforce word limit (approximately 200 words)
                    temperature=0.3
                )
            except Exception as e:
                # Fallback to direct LLM call if shared clients fail
                response = self.llm_agent.call_llm(
                    prompt=full_prompt,
                    system_message="You are a financial analyst AI. Provide clear, insightful analysis of financial data in under 200 words.",
                    max_tokens=300,  # Reduced to help enforce word limit (approximately 200 words)
                    temperature=0.3
                )
            
            logging.info(f"✅ LLM analysis completed for financial metrics")
            return response
            
        except Exception as e:
            error_msg = f"Error calling LLM: {e}"
            logging.error(f"❌ {error_msg}")
            return error_msg
    
    async def analyze_financial_metrics(self, ticker: str, query: str) -> Dict:
        """
        Analyze financial metrics for a ticker based on a natural language query.
        
        Args:
            ticker (str): Stock ticker symbol
            query (str): Natural language query about the financial metrics
            
        Returns:
            Dict: Analysis result with data and LLM response
        """
        try:
            logging.info(f"🔍 Analyzing financial metrics for {ticker}")
            logging.info(f"   - Query: {query}")
            
            # Get financial metrics data
            data = await self.get_financial_metrics_data(ticker)
            
            if not data:
                return {
                    "error": f"No financial metrics data found for {ticker}",
                    "ticker": ticker,
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            
            # Extract the financial metrics from the stored data structure
            financial_metrics = data.get('financial_metrics', {})
            
            # Run LLM analysis
            logging.info(f"🤖 Running LLM analysis for {ticker}")
            llm_analysis = await self.validate_analysis_agent(query, financial_metrics)
            
            # Prepare result
            result = {
                "ticker": ticker.upper(),
                "query": query,
                "analysis_timestamp": datetime.now().isoformat(),
                "data_retrieved_at": data.get('stored_at', 'Unknown'),
                "llm_response": llm_analysis,  # Changed from llm_analysis to llm_response for consistency
                "data_summary": {
                    "has_financial_metrics": bool(financial_metrics.get('financial_metrics')),
                    "has_dcf_data": bool(financial_metrics.get('dcf', {}).get('best_estimate')),
                    "has_price_data": bool(financial_metrics.get('price', {}).get('latest_price')),
                    "latest_price": financial_metrics.get('price', {}).get('latest_price'),
                    "market_cap": financial_metrics.get('financial_metrics', {}).get('market_cap'),
                    "best_dcf_estimate": financial_metrics.get('dcf', {}).get('best_estimate'),
                    "ev_to_ebitda": financial_metrics.get('financial_metrics', {}).get('ev_to_ebitda')
                },
                "metadata": data.get('metadata', {})
            }
            
            logging.info(f"✅ Financial metrics analysis completed for {ticker}")
            return result
            
        except Exception as e:
            logging.error(f"❌ Error analyzing financial metrics for {ticker}: {e}")
            return {
                "error": f"Analysis failed for {ticker}: {str(e)}",
                "ticker": ticker,
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def check_update_status(self, ticker: str) -> Dict:
        """
        Check the update status for a ticker based on the 6:00 PM rule.
        Rule: Update once per day after 6:00 PM (not every time after 6:00 PM).
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict: Update status information
        """
        try:
            existing_data = self.storage.get_financial_metrics_data(ticker, self.collection_name)
            
            if not existing_data:
                return {
                    "ticker": ticker.upper(),
                    "status": "no_data",
                    "message": "No data found for this ticker",
                    "action_needed": "download_fresh_data"
                }
            
            metadata = existing_data.get('metadata', {})
            last_update = metadata.get('latest_update_time')
            
            if not last_update:
                return {
                    "ticker": ticker.upper(),
                    "status": "unknown_update_time",
                    "message": "No update time found in metadata",
                    "action_needed": "check_manually"
                }
            
            current_time = datetime.now()
            update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
            current_date = current_time.date()
            update_date = update_time.date()
            
            if current_date == update_date:
                # Same day - check if past 6:00 PM
                six_pm_today = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
                
                if current_time >= six_pm_today:
                    # Past 6:00 PM on same day - check if we already updated after 6:00 PM
                    last_update_hour = update_time.hour
                    
                    if last_update_hour < 18:
                        # Haven't updated after 6:00 PM today - need update
                        time_since_update = current_time - update_time
                        return {
                            "ticker": ticker.upper(),
                            "status": "update_needed",
                            "message": f"Past 6:00 PM on {current_date}, first update after 6 PM needed",
                            "last_update": last_update,
                            "current_time": current_time.isoformat(),
                            "six_pm_threshold": six_pm_today.isoformat(),
                            "time_since_update": str(time_since_update),
                            "last_update_hour": last_update_hour,
                            "action_needed": "download_fresh_data"
                        }
                    else:
                        # Already updated after 6:00 PM today - data is fresh
                        time_since_update = current_time - update_time
                        return {
                            "ticker": ticker.upper(),
                            "status": "fresh",
                            "message": f"Already updated after 6:00 PM today, data is fresh",
                            "last_update": last_update,
                            "current_time": current_time.isoformat(),
                            "six_pm_threshold": six_pm_today.isoformat(),
                            "time_since_update": str(time_since_update),
                            "last_update_hour": last_update_hour,
                            "action_needed": "none"
                        }
                else:
                    # Before 6:00 PM on same day
                    time_until_update = six_pm_today - current_time
                    return {
                        "ticker": ticker.upper(),
                        "status": "fresh",
                        "message": f"Data is fresh, next update at 6:00 PM on {current_date}",
                        "last_update": last_update,
                        "current_time": current_time.isoformat(),
                        "six_pm_threshold": six_pm_today.isoformat(),
                        "time_until_update": str(time_until_update),
                        "action_needed": "none"
                    }
            else:
                # Different day
                days_difference = (current_date - update_date).days
                return {
                    "ticker": ticker.upper(),
                    "status": "update_needed",
                    "message": f"Data is from different day, {days_difference} day(s) old",
                    "last_update": last_update,
                    "current_time": current_time.isoformat(),
                    "update_date": update_date.isoformat(),
                    "current_date": current_date.isoformat(),
                    "days_difference": days_difference,
                    "action_needed": "download_fresh_data"
                }
                
        except Exception as e:
            logging.error(f"❌ Error checking update status for {ticker}: {e}")
            return {
                "ticker": ticker.upper(),
                "status": "error",
                "message": f"Error checking status: {str(e)}",
                "action_needed": "check_manually"
            }
    
    async def get_financial_metrics_summary(self, ticker: str) -> Dict:
        """
        Get a summary of financial metrics for a ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict: Summary of financial metrics
        """
        try:
            data = await self.get_financial_metrics_data(ticker)
            
            if not data:
                return {"error": f"No data found for {ticker}"}
            
            financial_metrics = data.get('financial_metrics', {})
            
            summary = {
                "ticker": ticker.upper(),
                "summary_timestamp": datetime.now().isoformat(),
                "data_retrieved_at": data.get('stored_at', 'Unknown'),
                "valuation_metrics": {
                    "market_cap": financial_metrics.get('financial_metrics', {}).get('market_cap'),
                    "enterprise_value": financial_metrics.get('financial_metrics', {}).get('enterprise_value'),
                    "ev_to_ebitda": financial_metrics.get('financial_metrics', {}).get('ev_to_ebitda'),
                    "ev_to_sales": financial_metrics.get('financial_metrics', {}).get('ev_to_sales'),
                    "roe": financial_metrics.get('financial_metrics', {}).get('roe'),
                    "roic": financial_metrics.get('financial_metrics', {}).get('roic')
                },
                "dcf_valuation": {
                    "best_estimate": financial_metrics.get('dcf', {}).get('best_estimate'),
                    "source": financial_metrics.get('dcf', {}).get('source'),
                    "total_results": financial_metrics.get('dcf', {}).get('total_results_found', 0)
                },
                "price_data": {
                    "latest_price": financial_metrics.get('price', {}).get('latest_price'),
                    "price_change": financial_metrics.get('price', {}).get('price_summary', {}).get('price_change'),
                    "price_change_pct": financial_metrics.get('price', {}).get('price_summary', {}).get('price_change_pct'),
                    "data_points": financial_metrics.get('price', {}).get('total_data_points', 0)
                }
            }
            
            return summary
            
        except Exception as e:
            logging.error(f"❌ Error getting summary for {ticker}: {e}")
            return {"error": f"Summary failed for {ticker}: {str(e)}"}
    
    def close(self):
        """Close database connections."""
        if hasattr(self, 'storage'):
            self.storage.close()
        if hasattr(self, 'redis_client'):
            self.redis_client.close()
        logging.info("🔚 Financial Metrics Read Agent connections closed")


def main():
    """Main function for testing the Financial Metrics Read Agent."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Financial Metrics Read Agent')
    parser.add_argument('ticker', help='Stock ticker symbol to analyze')
    parser.add_argument('--query', default='Is the current stock price overvalued or undervalued based on the financial metrics?', 
                       help='Natural language query about the financial metrics')
    parser.add_argument('--summary', action='store_true', help='Get summary instead of analysis')
    parser.add_argument('--update-status', action='store_true', help='Check update status for ticker')
    parser.add_argument('--list-tickers', action='store_true', help='List all available tickers')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Set log level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    # Configuration
    REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
    REDIS_PORT = 16376
    REDIS_USERNAME = "default"
    REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    COLLECTION_NAME = "Financial_Metrics_INFOS"
    
    try:
        logging.info(f"🔧 INITIALIZING FINANCIAL METRICS READ AGENT")
        logging.info(f"   - Ticker: {args.ticker.upper()}")
        logging.info(f"   - Redis: {REDIS_HOST}:{REDIS_PORT}")
        logging.info(f"   - Collection: {COLLECTION_NAME}")
        
        # Initialize the read agent
        agent = FinancialMetricsReadAgent(
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            redis_username=REDIS_USERNAME,
            redis_password=REDIS_PASSWORD,
            collection_name=COLLECTION_NAME
        )
        
        # List tickers if requested
        if args.list_tickers:
            logging.info(f"📋 LISTING AVAILABLE TICKERS")
            tickers = agent.list_available_tickers()
            if tickers:
                logging.info(f"✅ Found {len(tickers)} tickers:")
                for ticker in tickers:
                    logging.info(f"   - {ticker}")
            else:
                logging.info("ℹ️ No tickers found")
        
        # Get summary if requested
        elif args.summary:
            logging.info(f"📊 GETTING FINANCIAL METRICS SUMMARY")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            
            summary = agent.get_financial_metrics_summary(args.ticker.upper())
            if 'error' not in summary:
                logging.info("✅ FINANCIAL METRICS SUMMARY RETRIEVED")
                print(f"\n📋 Financial Metrics Summary for {args.ticker.upper()}:")
                print(json.dumps(summary, indent=2))
            else:
                logging.error(f"❌ {summary['error']}")
        
        # Check update status if requested
        elif args.update_status:
            logging.info(f"🔄 CHECKING UPDATE STATUS")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            
            status = agent.check_update_status(args.ticker.upper())
            logging.info(f"✅ UPDATE STATUS CHECKED")
            print(f"\n🔄 Update Status for {args.ticker.upper()}:")
            print(json.dumps(status, indent=2))
        
        # Run analysis (default action)
        else:
            logging.info(f"🔍 RUNNING FINANCIAL METRICS ANALYSIS")
            logging.info(f"   - Ticker: {args.ticker.upper()}")
            logging.info(f"   - Query: {args.query}")
            
            result = agent.analyze_financial_metrics(args.ticker.upper(), args.query)
            
            if 'error' not in result:
                logging.info("✅ FINANCIAL METRICS ANALYSIS COMPLETED")
                print(f"\n🤖 Financial Metrics Analysis for {args.ticker.upper()}:")
                print(f"Query: {result['query']}")
                print(f"Analysis: {result['llm_analysis']}")
                print(f"\n📊 Data Summary:")
                print(f"   - Latest Price: ${result['data_summary']['latest_price']}")
                print(f"   - Market Cap: ${result['data_summary']['market_cap']:,}")
                print(f"   - Best DCF Estimate: ${result['data_summary']['best_dcf_estimate']}")
                print(f"   - EV/EBITDA: {result['data_summary']['ev_to_ebitda']}")
            else:
                logging.error(f"❌ {result['error']}")
        
    except KeyboardInterrupt:
        logging.warning("⚠️  OPERATION CANCELLED BY USER")
    except Exception as e:
        logging.error("❌ CRITICAL ERROR IN MAIN EXECUTION:")
        logging.error(f"   - Error type: {type(e).__name__}")
        logging.error(f"   - Error details: {e}")
        sys.exit(1)
    finally:
        if 'agent' in locals():
            agent.close()
            logging.info("🔚 Financial Metrics Read Agent closed")


if __name__ == "__main__":
    # Example usage:
    # python Financial_Metrics_Read_Agent.py AAPL
    # python Financial_Metrics_Read_Agent.py TSLA --query "What is the current valuation multiple?"
    # python Financial_Metrics_Read_Agent.py AAPL --summary
    # python Financial_Metrics_Read_Agent.py AAPL --update-status
    # python Financial_Metrics_Read_Agent.py --list-tickers
    main()
