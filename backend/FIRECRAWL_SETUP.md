# 🔥 Firecrawl API Integration Guide

## Overview

Firecrawl is a powerful web search and scraping API integrated into the QandQ AI Supervisor Agent. It enables:
- **Real-time news search** for company developments
- **Web content extraction** from any URL
- **Company information gathering** from public sources
- **Market sentiment analysis** from recent articles

---

## 🚀 Quick Setup

### 1. Install Dependencies

```bash
pip install requests python-dotenv
```

### 2. API Key Configuration

Your Firecrawl API key is stored in `config.env`:

```env
FIRECRAWL_API_KEY=fc-f99ff845b82f49939ad95f59b414013d
```

**✅ Already configured!** The key is loaded automatically when you use `firecrawl_utils.py`.

### 3. Import and Use

```python
from firecrawl_utils import search_web, search_news, search_company_info, search_recent_news

# Search for news
news = search_news("Google AI", ticker="GOOGL", limit=5)

# Search company info
info = search_company_info("Tesla", ticker="TSLA")

# General web search
results = search_web("semiconductor shortage 2024")
```

---

## 📖 API Functions

### `search_web(query, limit, sources, max_age_hours)`

General web search with filtering options.

**Parameters:**
- `query` (str): Search query
- `limit` (int): Max results (default: 10)
- `sources` (list): ["web", "news", "academic"] (default: ["web"])
- `max_age_hours` (int): Maximum content age in hours (default: 48)
- `only_main_content` (bool): Extract main content only (default: True)

**Returns:** Dictionary with search results

**Example:**
```python
results = search_web("AI developments 2024", limit=10)
for result in results.get('data', []):
    print(f"{result['title']}: {result['url']}")
```

---

### `search_news(query, ticker, limit, max_age_hours)`

Search specifically for news articles.

**Parameters:**
- `query` (str): Search query
- `ticker` (str, optional): Stock ticker to enhance search
- `limit` (int): Max articles (default: 10)
- `max_age_hours` (int): Max article age (default: 48)

**Returns:** Dictionary with news articles

**Example:**
```python
news = search_news("Tesla earnings", ticker="TSLA", limit=5, max_age_hours=24)
for article in news.get('data', []):
    print(f"📰 {article['title']}")
    print(f"   Published: {article.get('publishedAt', 'N/A')}")
    print(f"   URL: {article['url']}\n")
```

---

### `search_company_info(company_name, ticker, limit)`

Get company profile and business overview.

**Parameters:**
- `company_name` (str): Full company name
- `ticker` (str, optional): Stock ticker
- `limit` (int): Max results (default: 10)

**Returns:** Company information from various sources

**Example:**
```python
info = search_company_info("Apple", ticker="AAPL", limit=5)
for item in info.get('data', []):
    print(f"🏢 {item['title']}")
    print(f"   {item['snippet'][:200]}...\n")
```

---

### `search_recent_news(company_name, ticker, limit, hours)`

Get the most recent news about a company.

**Parameters:**
- `company_name` (str): Company name
- `ticker` (str, optional): Stock ticker
- `limit` (int): Number of articles (default: 10)
- `hours` (int): How recent (default: 48 hours)

**Returns:** Recent news articles

**Example:**
```python
recent = search_recent_news("Google", ticker="GOOGL", hours=12, limit=10)
print(f"Found {len(recent.get('data', []))} articles in the last 12 hours")
```

---

### `scrape_url(url, only_main_content, include_pdf)`

Scrape content from a specific URL.

**Parameters:**
- `url` (str): URL to scrape
- `only_main_content` (bool): Extract main content only (default: True)
- `include_pdf` (bool): Parse PDF content (default: False)

**Returns:** Scraped content

**Example:**
```python
content = scrape_url("https://example.com/article")
print(content.get('data', {}).get('content', 'No content'))
```

---

## 🎯 Use Cases in Supervisor Agent

### 1. **Market Sentiment Analysis**

```python
# Get recent news for sentiment analysis
ticker = "TSLA"
news = search_recent_news("Tesla", ticker=ticker, hours=24, limit=20)

# Pass to LLM for sentiment analysis
news_content = "\n".join([f"- {item['title']}" for item in news.get('data', [])])
prompt = f"Analyze the market sentiment based on these Tesla news headlines:\n{news_content}"
sentiment = llm_agent.call_deepseek(prompt)
```

### 2. **Competitive Intelligence**

```python
# Search for competitor activity
company = "NVIDIA"
competitors = ["AMD", "Intel", "Qualcomm"]

for competitor in competitors:
    news = search_news(f"{competitor} AI chips", limit=3, max_age_hours=168)
    print(f"Recent activity for {competitor}:")
    for article in news.get('data', []):
        print(f"  - {article['title']}")
```

### 3. **Company Deep Dive**

```python
# Comprehensive company analysis
company = "Google"
ticker = "GOOGL"

# Get company info
info = search_company_info(company, ticker=ticker, limit=5)

# Get recent news
news = search_recent_news(company, ticker=ticker, hours=72, limit=10)

# Get specific topic search
products = search_web(f"{company} new products 2024", limit=5)

# Combine for LLM analysis
combined = {
    "company_info": info,
    "recent_news": news,
    "products": products
}
```

### 4. **Real-time Event Monitoring**

```python
import asyncio

async def monitor_ticker(ticker, company_name, check_interval_minutes=30):
    """Monitor a ticker for breaking news"""
    while True:
        news = search_recent_news(company_name, ticker=ticker, hours=1, limit=5)
        
        if news.get('data'):
            print(f"🚨 Breaking news for {ticker}:")
            for article in news['data']:
                print(f"  📰 {article['title']}")
        
        await asyncio.sleep(check_interval_minutes * 60)

# Run monitor
await monitor_ticker("AAPL", "Apple", check_interval_minutes=15)
```

---

## 🔧 Helper Functions

### `format_search_results(results, max_results)`

Format search results into readable text.

```python
results = search_web("AI developments", limit=5)
formatted = format_search_results(results, max_results=3)
print(formatted)
```

### `extract_content_list(results)`

Extract just the content text from results.

```python
results = search_news("Tesla", limit=5)
content_list = extract_content_list(results)
for content in content_list:
    print(content[:200])
```

---

## 📊 Response Format

All Firecrawl functions return a dictionary with this structure:

```python
{
    "data": [
        {
            "title": "Article Title",
            "url": "https://example.com/article",
            "snippet": "Brief excerpt...",
            "content": "Full article content...",
            "publishedAt": "2024-01-15T10:30:00Z",
            "source": "example.com"
        },
        # ... more results
    ],
    "metadata": {
        "query": "search query",
        "resultsCount": 10,
        "processingTime": 1.23
    }
}
```

---

## ⚙️ Configuration Options

### Search Options

```python
payload = {
    "query": "your search query",
    "sources": ["web", "news"],  # What to search
    "categories": [],             # Content categories
    "limit": 10,                  # Max results
    "scrapeOptions": {
        "onlyMainContent": True,  # Strip headers/footers
        "maxAge": 172800000,      # Max age in milliseconds (48 hours)
        "parsers": ["pdf"],       # Parse PDFs if found
        "formats": []             # Output formats
    }
}
```

### Age Conversions

- 1 hour = 3,600,000 ms
- 24 hours = 86,400,000 ms
- 48 hours = 172,800,000 ms (default)
- 7 days = 604,800,000 ms

---

## 🛡️ Security & Best Practices

### ✅ DO:
- Store API key in `config.env` (already done)
- Add `config.env` to `.gitignore` (already done)
- Use reasonable limits (5-10 results) to conserve API credits
- Cache results when possible
- Handle errors gracefully with try-except

### ❌ DON'T:
- Hard-code API keys in notebooks or scripts
- Request too many results at once (API limits apply)
- Scrape excessively (respect rate limits)
- Commit `config.env` to version control

---

## 🧪 Testing

Run the example script to test your setup:

```bash
python firecrawl_utils.py
```

This will run 4 example searches and display formatted results.

---

## 📚 Additional Resources

- **Firecrawl Docs**: https://docs.firecrawl.dev
- **API Reference**: https://docs.firecrawl.dev/api-reference
- **Rate Limits**: Check your Firecrawl dashboard
- **Support**: Contact Firecrawl support or check their Discord

---

## ✅ Quick Test

```python
# Test your setup
from firecrawl_utils import search_news

result = search_news("AI developments", limit=1)
print("✅ Firecrawl working!" if result.get('data') else "❌ Setup issue")
```

---

**🎉 You're all set! Firecrawl is ready to use in your Supervisor Agent.**

