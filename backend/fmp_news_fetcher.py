"""
FMP News Fetcher - Simple function to get 1 month of news for any ticker
"""

import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
import os

# Import centralized config
from config import FMP_API_KEY, FMP_API_V3_URL


def get_news(ticker: str, days: int) -> List[Dict[str, str]]:
    """
    Get news for a ticker from N days ago to today
    
    Args:
        ticker: Stock ticker (e.g., "AAPL", "TSLA")
        days: Number of days back (e.g., 30, 60, 90)
    
    Returns:
        List of dicts with: news, date, link
    
    Example:
        >>> news = get_news("AAPL", 30)
        >>> for item in news[:3]:
        >>>     print(f"{item['date']}: {item['news']}")
        >>>     print(f"Link: {item['link']}\n")
    """
    
    url = f"{FMP_API_V3_URL}/stock_news"
    params = {'tickers': ticker, 'limit': 100, 'apikey': FMP_API_KEY}
    
    response = requests.get(url, params=params, timeout=10)
    data = response.json()
    
    cutoff_date = datetime.now() - timedelta(days=days)
    results = []
    
    for item in data:
        try:
            date_str = item['publishedDate'].split('.')[0]
            news_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            
            if news_date >= cutoff_date:
                title = item.get('title', '')
                text = item.get('text', '')
                news_content = f"{title}. {text}" if text else title
                
                results.append({
                    'news': news_content,
                    'date': date_str,
                    'link': item.get('url', '')
                })
        except:
            continue
    
    print(f"✅ Found {len(results)} news items for {ticker} in last {days} days")
    return results


def get_one_month_news(ticker: str) -> List[str]:
    """
    Get 1 month of news for a ticker from FMP API
    
    Args:
        ticker: Stock ticker symbol (e.g., "AAPL", "TSLA")
    
    Returns:
        List of news strings (titles + content combined)
    
    Example:
        >>> news = get_one_month_news("AAPL")
        >>> print(f"Found {len(news)} news items")
        >>> print(news[0])
    """
    
    print(f"📰 Fetching 1 month of news for {ticker}...")
    
    # FMP Stock News endpoint
    url = f"{FMP_API_V3_URL}/stock_news"
    
    params = {
        'tickers': ticker,
        'limit': 50,  # Get up to 50 news items
        'apikey': FMP_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        news_data = response.json()
        
        if not news_data:
            print(f"⚠️ No news found for {ticker}")
            return []
        
        # Filter to last 30 days
        one_month_ago = datetime.now() - timedelta(days=30)
        news_list = []
        
        for item in news_data:
            # Parse published date
            published_date_str = item.get('publishedDate', '')
            
            try:
                # FMP format: "2024-01-15 10:30:00"
                published_date = datetime.strptime(published_date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                
                # Only include news from last 30 days
                if published_date >= one_month_ago:
                    title = item.get('title', '')
                    text = item.get('text', '')
                    
                    # Combine title and text
                    news_content = f"{title}. {text}" if text else title
                    
                    if news_content:
                        news_list.append(news_content)
            
            except Exception as e:
                # Skip items with parsing errors
                continue
        
        print(f"✅ Found {len(news_list)} news items in the last 30 days")
        return news_list
    
    except requests.exceptions.RequestException as e:
        print(f"❌ Error fetching news: {e}")
        return []
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return []


def get_one_month_news_detailed(ticker: str) -> List[Dict[str, Any]]:
    """
    Get 1 month of news with detailed metadata
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        List of dicts with keys: title, text, url, date, site
    
    Example:
        >>> news = get_one_month_news_detailed("AAPL")
        >>> for item in news[:3]:
        >>>     print(f"{item['date']}: {item['title']}")
    """
    
    print(f"📰 Fetching detailed news for {ticker}...")
    
    url = f"{FMP_API_V3_URL}/stock_news"
    
    params = {
        'tickers': ticker,
        'limit': 50,
        'apikey': FMP_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        news_data = response.json()
        
        if not news_data:
            print(f"⚠️ No news found for {ticker}")
            return []
        
        # Filter to last 30 days
        one_month_ago = datetime.now() - timedelta(days=30)
        news_list = []
        
        for item in news_data:
            published_date_str = item.get('publishedDate', '')
            
            try:
                published_date = datetime.strptime(published_date_str.split('.')[0], '%Y-%m-%d %H:%M:%S')
                
                if published_date >= one_month_ago:
                    news_item = {
                        'title': item.get('title', ''),
                        'text': item.get('text', ''),
                        'url': item.get('url', ''),
                        'date': published_date_str,
                        'site': item.get('site', ''),
                        'symbol': item.get('symbol', ticker)
                    }
                    news_list.append(news_item)
            
            except Exception as e:
                continue
        
        print(f"✅ Found {len(news_list)} detailed news items")
        return news_list
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


# Quick test function
if __name__ == "__main__":
    # Test with AAPL
    print("=" * 60)
    print("Testing FMP News Fetcher")
    print("=" * 60)
    
    news = get_one_month_news("AAPL")
    
    if news:
        print(f"\n📊 Sample of {len(news)} news items:")
        print("\n" + "=" * 60)
        for i, item in enumerate(news[:3], 1):
            print(f"\n{i}. {item[:200]}...")
            print("-" * 60)
    else:
        print("\n⚠️ No news found")

