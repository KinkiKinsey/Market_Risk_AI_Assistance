#!/usr/bin/env python3
"""
Get Latest News and Queries AI
Clean, production-ready module for extracting news and generating investigative queries.

Usage:
    from get_latest_news_and_queries_AI import get_queries
    
    queries = await get_queries("TGT")
"""

import redis
import json
import asyncio
from typing import Dict, Any, List
from tavily import TavilyClient

# Configuration
TAVILY_API_KEY = "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"
REDIS_CONFIG = {
    'host': 'redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com',
    'port': 16376,
    'password': 'rl8242B4UItBhFzgHW5APEqZnkYoaEZv'
}

# =============================================================================
# INTERNAL FUNCTIONS
# =============================================================================

def _get_company_name(ticker: str) -> str:
    """Get company name from ticker using Tavily."""
    client = TavilyClient(TAVILY_API_KEY)
    response = client.search(
        query=f"What is the company name for stock ticker {ticker.upper()}? Return only the company name.",
        include_answer="advanced",
        search_depth="advanced"
    )
    
    if response and 'answer' in response:
        company_name = response['answer'].strip()
        if '\n' in company_name:
            company_name = company_name.split('\n')[0]
        return company_name
    return f"Company {ticker}"

def _get_sector_data(ticker: str) -> Dict[str, Any]:
    """Get sector data from Redis."""
    redis_client = redis.Redis(
        host=REDIS_CONFIG['host'],
        port=REDIS_CONFIG['port'],
        password=REDIS_CONFIG['password'],
        decode_responses=True
    )
    
    key = f"Sector_Analyst_INFOS:{ticker.upper()}_sector_analysis"
    sector_data_json = redis_client.get(key)
    
    if sector_data_json:
        return json.loads(sector_data_json)
    return {}

async def _search_news(query: str) -> str:
    """Search news using Tavily and return summary."""
    client = TavilyClient(TAVILY_API_KEY)
    response = client.search(
        query=query,
        include_answer="advanced",
        search_depth="advanced",
        days=7
    )
    return response.get('answer', 'No news found')

async def _gather_all_news(ticker: str, company_name: str, sector_name: str, competitors: List[str]) -> Dict[str, str]:
    """Gather all news in parallel."""
    
    tasks = []
    
    # Macro news
    tasks.append(_search_news(
        "What is the most important macroeconomic news in the last 7 days that could impact stock markets? Include Fed policy, inflation, GDP, or major economic events."
    ))
    
    # Company fundamentals
    tasks.append(_search_news(
        f"What fundamental business news about {company_name} ({ticker}) in the last 7 days? Focus on: business development, strategic initiatives, management changes, new products, expansion plans, or earnings. Exclude stock price movements."
    ))
    
    # Sector news
    if sector_name:
        tasks.append(_search_news(
            f"What important news in the {sector_name} sector in the last 7 days? Include industry trends, market changes, or regulatory updates."
        ))
    else:
        tasks.append(asyncio.sleep(0, result="No sector data"))
    
    # Competitor news
    for competitor in competitors[:3]:
        tasks.append(_search_news(
            f"What fundamental business news about {competitor} in the last 7 days? Focus on strategy, products, or business developments."
        ))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    news = {
        'macro': results[0] if not isinstance(results[0], Exception) else "Error",
        'company': results[1] if not isinstance(results[1], Exception) else "Error",
        'sector': results[2] if not isinstance(results[2], Exception) else "No sector data"
    }
    
    news['competitors'] = []
    for i, competitor in enumerate(competitors[:3]):
        comp_news = results[3 + i] if len(results) > 3 + i else "Error"
        if not isinstance(comp_news, Exception):
            news['competitors'].append({'name': competitor, 'news': comp_news})
    
    return news

# =============================================================================
# MAIN FUNCTION
# =============================================================================

async def get_queries(ticker: str) -> List[str]:
    """
    Get investigative queries for a ticker based on latest news.
    
    Args:
        ticker: Stock ticker symbol (e.g., "TGT", "AAPL", "TSLA")
    
    Returns:
        List of tagged queries:
        - "Macro: xxx"
        - "Micro: xxx"
        - "Sector: xxx"
        - "Competitor: xxx" (1-3 times)
    
    Example:
        queries = await get_queries("TGT")
        # Returns:
        # [
        #   "Macro: How will Fed rate cuts impact TGT? The Federal Reserve...",
        #   "Micro: How does new CEO impact TGT? Target appointed...",
        #   "Sector: How does retail growth impact TGT? General merchandise...",
        #   "Competitor: How does Walmart's strategy affect TGT? Walmart...",
        #   "Competitor: How does Amazon's AI affect TGT? Amazon launched...",
        #   "Competitor: How does Costco's expansion affect TGT? Costco..."
        # ]
    """
    
    # Step 1: Get company name
    company_name = _get_company_name(ticker)
    
    # Step 2: Get sector data from Redis
    sector_data = _get_sector_data(ticker)
    sector_name = sector_data.get('asset_relative_summary', None)
    competitor_summary = sector_data.get('competitor_summary', 'None')
    
    competitors = []
    if competitor_summary and competitor_summary != "None":
        competitors = [c.strip() for c in competitor_summary.split(',')]
    
    # Step 3: Gather all news in parallel
    news = await _gather_all_news(ticker, company_name, sector_name, competitors)
    
    # Step 4: Create tagged queries
    queries = []
    
    if news['macro'] and news['macro'] != "Error":
        queries.append(f"Macro: How will this macro event impact {ticker}? {news['macro']}")
    
    if news['company'] and news['company'] != "Error":
        queries.append(f"Micro: How does this business development impact {ticker}? {news['company']}")
    
    if news['sector'] and news['sector'] not in ["Error", "No sector data"]:
        queries.append(f"Sector: How does this {sector_name} trend impact {ticker}? {news['sector']}")
    
    for comp in news['competitors']:
        queries.append(f"Competitor: How does {comp['name']}'s move affect {ticker}? {comp['news']}")
    
    return queries

# =============================================================================
# CONVENIENCE FUNCTION WITH DISPLAY
# =============================================================================

async def get_queries_display(ticker: str) -> List[str]:
    """
    Get queries and display them cleanly.
    
    Args:
        ticker: Stock ticker
    
    Returns:
        List of queries
    """
    queries = await get_queries(ticker)
    
    print("=" * 70)
    print(f"🔍 INVESTIGATIVE QUERIES FOR {ticker}")
    print("=" * 70)
    
    for i, query in enumerate(queries, 1):
        tag = query.split(':')[0] if ':' in query else "Query"
        content = query.split(':', 1)[1].strip() if ':' in query else query
        print(f"\n{i}. [{tag}]")
        print(f"   {content[:250]}...")
    
    print(f"\n{'=' * 70}")
    print(f"✅ Total: {len(queries)} queries")
    print("=" * 70)
    
    return queries

