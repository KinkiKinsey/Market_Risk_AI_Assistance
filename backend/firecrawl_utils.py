#!/usr/bin/env python3
"""
Firecrawl API Integration Utility
Web search and scraping functionality for QandQ AI

SETUP:
    1. Install required packages:
       pip install requests python-dotenv
    
    2. Add your Firecrawl API key to config.env:
       FIRECRAWL_API_KEY=fc-your-key-here
    
USAGE:
    from firecrawl_utils import search_web, search_news, scrape_url
    
    # Search for general web content
    results = search_web("Google AI latest developments")
    
    # Search for news specifically
    news = search_news("Tesla earnings report", limit=5)
    
    # Scrape a specific URL
    content = scrape_url("https://example.com/article")
"""

import os
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

# Try to load from .env file
try:
    from dotenv import load_dotenv
    load_dotenv('config.env')
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print("⚠️ python-dotenv not available. Install with: pip install python-dotenv")

# ============================================================================
# CONFIGURATION
# ============================================================================

# Import centralized config
from config import FIRECRAWL_API_KEY, FIRECRAWL_BASE_URL

# ============================================================================
# CORE FUNCTIONS
# ============================================================================

def search_web(
    query: str,
    limit: int = 10,
    sources: List[str] = None,
    categories: List[str] = None,
    max_age_hours: int = 48,
    only_main_content: bool = True
) -> Dict[str, Any]:
    """
    Search the web using Firecrawl API.
    
    Args:
        query: Search query string
        limit: Maximum number of results (default: 10)
        sources: List of sources to search ["web", "news", "academic"] (default: ["web"])
        categories: List of content categories to filter by
        max_age_hours: Maximum age of content in hours (default: 48)
        only_main_content: Extract only main content, skip headers/footers (default: True)
    
    Returns:
        Dict containing search results and metadata
    
    Example:
        >>> results = search_web("AI developments 2024", limit=5)
        >>> for result in results.get('data', []):
        ...     print(result['title'], result['url'])
    """
    url = f"{FIRECRAWL_BASE_URL}/search"
    
    # Convert hours to milliseconds for API
    max_age_ms = max_age_hours * 60 * 60 * 1000
    
    payload = {
        "query": query,
        "sources": sources or ["web"],
        "categories": categories or [],
        "limit": limit,
        "scrapeOptions": {
            "onlyMainContent": only_main_content,
            "maxAge": max_age_ms,
            "parsers": ["pdf"],
            "formats": []
        }
    }
    
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Firecrawl API error: {e}")
        return {"error": str(e), "data": []}


def search_news(
    query: str,
    ticker: Optional[str] = None,
    limit: int = 10,
    max_age_hours: int = 48
) -> Dict[str, Any]:
    """
    Search for news articles using Firecrawl.
    
    Args:
        query: Search query (e.g., "Google AI")
        ticker: Optional stock ticker to include in search
        limit: Maximum number of articles (default: 10)
        max_age_hours: Maximum age of articles in hours (default: 48)
    
    Returns:
        Dict containing news articles and metadata
    
    Example:
        >>> news = search_news("Tesla earnings", ticker="TSLA", limit=5)
        >>> for article in news.get('data', []):
        ...     print(f"{article['title']}: {article['url']}")
    """
    # Enhance query with ticker if provided
    if ticker:
        query = f"{query} {ticker}"
    
    return search_web(
        query=query,
        limit=limit,
        sources=["news"],
        max_age_hours=max_age_hours,
        only_main_content=True
    )


def search_company_info(
    company_name: str,
    ticker: Optional[str] = None,
    limit: int = 10
) -> Dict[str, Any]:
    """
    Search for company information and recent developments.
    
    Args:
        company_name: Full company name (e.g., "Google", "Tesla")
        ticker: Optional stock ticker
        limit: Maximum number of results (default: 10)
    
    Returns:
        Dict containing company information from various sources
    
    Example:
        >>> info = search_company_info("Apple", ticker="AAPL")
        >>> print(info.get('data', [])[0]['content'])
    """
    query = f"{company_name} company profile business overview"
    if ticker:
        query += f" {ticker}"
    
    return search_web(
        query=query,
        limit=limit,
        sources=["web"],
        max_age_hours=720,  # 30 days for company info
        only_main_content=True
    )


def search_recent_news(
    company_name: str,
    ticker: Optional[str] = None,
    limit: int = 10,
    hours: int = 48
) -> Dict[str, Any]:
    """
    Search for recent news about a company.
    
    Args:
        company_name: Company name or ticker
        ticker: Optional stock ticker
        limit: Number of articles (default: 10)
        hours: How recent (default: 48 hours)
    
    Returns:
        Dict with recent news articles
    
    Example:
        >>> news = search_recent_news("Google", ticker="GOOGL", hours=24)
        >>> for article in news.get('data', []):
        ...     print(f"[{article['publishedAt']}] {article['title']}")
    """
    query = f"recent news {company_name}"
    if ticker:
        query += f" {ticker}"
    
    return search_news(
        query=query,
        ticker=ticker,
        limit=limit,
        max_age_hours=hours
    )


def scrape_url(
    url: str,
    only_main_content: bool = True,
    include_pdf: bool = False
) -> Dict[str, Any]:
    """
    Scrape content from a specific URL.
    
    Args:
        url: URL to scrape
        only_main_content: Extract only main content (default: True)
        include_pdf: Parse PDF content if available (default: False)
    
    Returns:
        Dict containing scraped content
    
    Example:
        >>> content = scrape_url("https://example.com/article")
        >>> print(content.get('data', {}).get('content', ''))
    """
    scrape_url_endpoint = f"{FIRECRAWL_BASE_URL}/scrape"
    
    payload = {
        "url": url,
        "options": {
            "onlyMainContent": only_main_content,
            "parsers": ["pdf"] if include_pdf else [],
            "formats": ["markdown", "html"]
        }
    }
    
    headers = {
        "Authorization": f"Bearer {FIRECRAWL_API_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(scrape_url_endpoint, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ Firecrawl scrape error: {e}")
        return {"error": str(e), "data": {}}


# ============================================================================
# FORMATTED OUTPUT HELPERS
# ============================================================================

def format_search_results(results: Dict[str, Any], max_results: int = 5) -> str:
    """
    Format Firecrawl search results into readable text.
    
    Args:
        results: Results from search_web or search_news
        max_results: Maximum results to include (default: 5)
    
    Returns:
        Formatted string with search results
    """
    data = results.get('data', [])
    if not data:
        return "No results found."
    
    output = []
    for i, item in enumerate(data[:max_results], 1):
        title = item.get('title', 'No title')
        url = item.get('url', 'No URL')
        snippet = item.get('snippet', item.get('content', ''))[:200]
        
        output.append(f"{i}. {title}")
        output.append(f"   URL: {url}")
        output.append(f"   {snippet}...")
        output.append("")
    
    return "\n".join(output)


def extract_content_list(results: Dict[str, Any]) -> List[str]:
    """
    Extract just the content text from search results.
    
    Args:
        results: Results from Firecrawl search
    
    Returns:
        List of content strings
    """
    data = results.get('data', [])
    return [item.get('content', item.get('snippet', '')) for item in data if item.get('content') or item.get('snippet')]


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

def example_usage():
    """Example usage of Firecrawl utilities"""
    print("=" * 70)
    print("🔥 FIRECRAWL API - EXAMPLE USAGE")
    print("=" * 70)
    
    # Example 1: Search for general web content
    print("\n📖 Example 1: General Web Search")
    print("-" * 70)
    results = search_web("artificial intelligence latest developments", limit=3)
    print(format_search_results(results, max_results=3))
    
    # Example 2: Search for news
    print("\n📰 Example 2: News Search")
    print("-" * 70)
    news = search_news("Tesla stock", ticker="TSLA", limit=3, max_age_hours=24)
    print(format_search_results(news, max_results=3))
    
    # Example 3: Company information
    print("\n🏢 Example 3: Company Info")
    print("-" * 70)
    company_info = search_company_info("Google", ticker="GOOGL", limit=2)
    print(format_search_results(company_info, max_results=2))
    
    # Example 4: Extract content list
    print("\n📝 Example 4: Content Extraction")
    print("-" * 70)
    content_list = extract_content_list(results)
    for i, content in enumerate(content_list[:2], 1):
        print(f"{i}. {content[:150]}...")
    
    print("\n" + "=" * 70)
    print("✅ Firecrawl examples complete!")
    print("=" * 70)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    example_usage()

