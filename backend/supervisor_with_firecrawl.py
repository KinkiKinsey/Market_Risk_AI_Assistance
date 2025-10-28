# =============================================================================
# SUPERVISOR AGENT WITH FIRECRAWL INTEGRATION
# =============================================================================

from typing import Dict, Any, List
import requests
import os

# ============================================================================
# FIRECRAWL INTEGRATION - Recent Company News
# ============================================================================

def get_company_recent_news_firecrawl(company_name: str, ticker: str = None, limit: int = 10) -> Dict[str, Any]:
    """
    Get recent 10 news about a company using Firecrawl API
    Focus on business developments and strategic news
    
    Args:
        company_name (str): Full company name (e.g., "Google", "Tesla")
        ticker (str, optional): Stock ticker symbol
        limit (int): Number of news articles to fetch (default: 10)
    
    Returns:
        dict: {
            'company_name': str,
            'ticker': str,
            'news_count': int,
            'news_summary': str,  # Formatted summary of all news
            'news_list': list,    # List of individual news items
            'raw_data': dict      # Raw Firecrawl response
        }
    """
    try:
        # Load API key from environment
        # Import centralized config
        import sys
        import os
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        if backend_dir not in sys.path:
            sys.path.insert(0, backend_dir)
        from config import FIRECRAWL_API_KEY
        api_key = FIRECRAWL_API_KEY
        if not api_key:
            raise ValueError("FIRECRAWL_API_KEY is required in config.env")
        
        # Build search query focused on business and development
        query = f"{company_name} recent business developments strategy news"
        if ticker:
            query += f" {ticker}"
        
        print(f"🔥 Fetching recent news for {company_name} using Firecrawl...")
        
        # Firecrawl API call
        url = "https://api.firecrawl.dev/v2/search"
        
        payload = {
            "query": query,
            "sources": ["news"],  # Only news sources
            "categories": [],
            "limit": limit,
            "scrapeOptions": {
                "onlyMainContent": True,
                "maxAge": 604800000,  # 7 days in milliseconds
                "parsers": [],
                "formats": []
            }
        }
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        
        # Extract news items
        news_items = data.get('data', [])
        news_count = len(news_items)
        
        print(f"✅ Found {news_count} news articles for {company_name}")
        
        # Format news list
        news_list = []
        for i, item in enumerate(news_items, 1):
            news_entry = {
                'index': i,
                'title': item.get('title', 'No title'),
                'url': item.get('url', ''),
                'snippet': item.get('snippet', item.get('content', ''))[:300],
                'published_at': item.get('publishedAt', 'Unknown date')
            }
            news_list.append(news_entry)
        
        # Create formatted summary
        news_summary = f"📰 Recent News for {company_name} ({ticker or 'N/A'}):\n\n"
        for news in news_list:
            news_summary += f"{news['index']}. {news['title']}\n"
            news_summary += f"   📅 {news['published_at']}\n"
            news_summary += f"   📝 {news['snippet']}...\n"
            news_summary += f"   🔗 {news['url']}\n\n"
        
        # Create result dictionary
        result = {
            'company_name': company_name,
            'ticker': ticker or 'N/A',
            'news_count': news_count,
            'news_summary': news_summary,
            'news_list': news_list,
            'raw_data': data
        }
        
        print(f"✅ Firecrawl news fetch complete for {company_name}")
        print(f"📊 Total articles: {news_count}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error fetching news for {company_name}: {e}")
        return {
            'company_name': company_name,
            'ticker': ticker or 'N/A',
            'news_count': 0,
            'news_summary': f'Error fetching news: {str(e)}',
            'news_list': [],
            'raw_data': {},
            'error': str(e)
        }


def get_company_news_titles_only(company_name: str, ticker: str = None, limit: int = 10) -> List[str]:
    """
    Get just the news titles as a simple list
    
    Args:
        company_name (str): Company name
        ticker (str, optional): Stock ticker
        limit (int): Number of articles
    
    Returns:
        list: List of news titles
    """
    result = get_company_recent_news_firecrawl(company_name, ticker, limit)
    return [news['title'] for news in result.get('news_list', [])]


def format_news_for_llm(company_name: str, ticker: str = None, limit: int = 10) -> str:
    """
    Format news in a clean way for LLM input
    
    Args:
        company_name (str): Company name
        ticker (str, optional): Stock ticker
        limit (int): Number of articles
    
    Returns:
        str: Formatted news text for LLM
    """
    result = get_company_recent_news_firecrawl(company_name, ticker, limit)
    
    formatted = f"Recent News Summary for {company_name} ({ticker or 'N/A'}):\n\n"
    
    for news in result.get('news_list', []):
        formatted += f"• {news['title']}\n"
        formatted += f"  {news['snippet'][:150]}...\n\n"
    
    return formatted


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Test the function
    print("=" * 70)
    print("🔥 FIRECRAWL NEWS FETCH TEST")
    print("=" * 70)
    
    # Example 1: Get Google news
    google_news = get_company_recent_news_firecrawl("Google", ticker="GOOGL", limit=5)
    print("\n📰 Google News:")
    print(google_news['news_summary'])
    
    # Example 2: Get just titles
    titles = get_company_news_titles_only("Tesla", ticker="TSLA", limit=3)
    print("\n📋 Tesla News Titles:")
    for i, title in enumerate(titles, 1):
        print(f"{i}. {title}")
    
    # Example 3: Format for LLM
    llm_format = format_news_for_llm("Apple", ticker="AAPL", limit=5)
    print("\n📝 LLM Formatted News:")
    print(llm_format[:500] + "...")

