# FMP News Fetcher - Usage Examples

## 📦 Simple Function to Get 1 Month of News

### Copy this into your notebook:

```python
# =============================================================================
# FMP NEWS FETCHER - Get 1 Month of News for Any Ticker
# =============================================================================

from fmp_news_fetcher import get_one_month_news, get_one_month_news_detailed

# Method 1: Simple - Get news as strings (ready for LLM analysis)
ticker = "AAPL"
news_list = get_one_month_news(ticker)

print(f"Found {len(news_list)} news items for {ticker}")
print("\nFirst 3 news items:")
for i, news in enumerate(news_list[:3], 1):
    print(f"\n{i}. {news[:200]}...")

# Method 2: Detailed - Get news with metadata
news_detailed = get_one_month_news_detailed(ticker)

print(f"\n\nDetailed news:")
for item in news_detailed[:3]:
    print(f"\n📅 {item['date']}")
    print(f"📰 {item['title']}")
    print(f"🔗 {item['url']}")
    print(f"🌐 Source: {item['site']}")
```

---

## 🚀 Integration with Your Analyst Graph

```python
# Get news for analysis
ticker = "TSLA"
news_list = get_one_month_news(ticker)

# Get brain and alpha (your existing code)
brain, alpha = hedgefundbrain(ticker)

# Run impact analysis
impact_chains = analyze_news_impact(
    brain=brain,
    alpha=alpha,
    news_list=news_list  # ← FMP news here!
)

# Visualize
visualize_qq_ai_report(
    ticker=ticker,
    impact_chains=impact_chains,
    # ... other params
)
```

---

## 📊 Function Details

### `get_one_month_news(ticker: str) -> List[str]`

**Returns:** List of news strings (title + content combined)

**Perfect for:**
- LLM analysis
- Impact chain generation
- Quick news summaries

**Example Output:**
```python
[
    "Apple announces new iPhone 15 with USB-C. Apple Inc. unveiled its latest...",
    "iPhone sales exceed expectations in Q3. Market analysts report that Apple...",
    "Apple expands into AI with new chip. The tech giant announced..."
]
```

---

### `get_one_month_news_detailed(ticker: str) -> List[Dict]`

**Returns:** List of dicts with full metadata

**Perfect for:**
- News archiving
- Source tracking
- Date filtering

**Example Output:**
```python
[
    {
        'title': 'Apple announces new iPhone 15',
        'text': 'Apple Inc. unveiled its latest...',
        'url': 'https://...',
        'date': '2024-01-15 10:30:00',
        'site': 'Reuters',
        'symbol': 'AAPL'
    }
]
```

---

## ⚙️ Configuration

**API Key:** Already configured in `fmp_news_fetcher.py`

**Time Range:** Last 30 days (automatically filtered)

**Limit:** Up to 50 news items

**No setup needed - just import and use!** ✨

