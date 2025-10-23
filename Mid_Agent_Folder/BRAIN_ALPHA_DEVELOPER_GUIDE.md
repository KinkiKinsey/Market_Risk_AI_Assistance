# 🧠 Hedge Fund Brain & Alpha - Developer Guide

## Overview

The **Hedge Fund Brain** is a qualitative intelligence system that processes multi-source financial data through a LangGraph-based workflow to produce:
1. **Brain**: A 4-layer structured intelligence framework (Macro → Sector → Market → Micro)
2. **Alpha Insights**: Actionable investment signals extracted from the brain

This guide explains how to use the `hedgefundbrain()` function in your applications.

---

## Table of Contents

- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Data Sources](#data-sources)
- [Output Structure](#output-structure)
- [Advanced Usage](#advanced-usage)
- [Caching & Update Logic](#caching--update-logic)
- [Integration Examples](#integration-examples)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

### Installation & Setup

```python
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.getcwd(), 'Mid_Agent_Folder'))

# Import the main function
from Hedge_Fund_Brain import hedgefundbrain
```

### Basic Usage

```python
import asyncio

async def main():
    # Generate brain and alpha for a ticker
    brain, alpha = await hedgefundbrain("TGT")
    
    # Access brain layers
    print(f"Macro factors: {len(brain['Macro'])}")
    print(f"Sector factors: {len(brain['Sector'])}")
    print(f"Market factors: {len(brain['Market'])}")
    print(f"Micro factors: {len(brain['Micro'])}")
    
    # Access alpha insights
    for insight in alpha:
        print(f"Feature: {insight['feature']}")
        print(f"Reasoning: {insight['reasoning']}")

# Run in Jupyter
await main()

# Run in script
asyncio.run(main())
```

---

## Architecture

### Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    HEDGE FUND BRAIN                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Data Collection (update_pool)                          │
│     ├─ Financial Metrics (15-day cache)                    │
│     ├─ Market Expectation (24-hour cache)                  │
│     ├─ Earnings & Future (30-day cache)                    │
│     ├─ Macro Analysis (Event-driven)                       │
│     ├─ Revenue Segmentation (Event-driven)                 │
│     └─ Sector Analysis (Event-driven)                      │
│                                                             │
│  2. Earnings Pipeline (LangGraph)                          │
│     ├─ Extract Q&A pairs                                   │
│     ├─ Refine Q&A                                          │
│     └─ Generate Buy-Side Focus                             │
│                                                             │
│  3. Brain Building Pipeline (LangGraph)                    │
│     ├─ Extractor Node (Multi-source → 4 layers)          │
│     ├─ Reflector Node (Quality control)                   │
│     └─ Alpha Discovery Node (Investment signals)          │
│                                                             │
│  4. Redis Storage                                          │
│     ├─ Key: Hedge_Fund_Brain:{TICKER}:brain              │
│     └─ Key: Hedge_Fund_Brain:{TICKER}:alpha              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

#### 1. **Data Collection Layer**
- **Purpose**: Gather and cache data from 6 specialized sub-agents
- **Location**: `update_pool.py`
- **Output**: Consolidated data dictionary with all sources

#### 2. **Earnings Pipeline**
- **Purpose**: Process earnings transcripts into structured Q&A and buy-side focus
- **Graph Type**: LangGraph StateGraph
- **Nodes**: `extract_qa_pairs` → `refine_qa` → `generate_buy_side_focus`

#### 3. **Brain Building Pipeline**
- **Purpose**: Transform raw data into 4-layer brain structure + alpha insights
- **Graph Type**: LangGraph StateGraph
- **Nodes**: `extractor_node` → `reflector_node` → `alpha_node`

#### 4. **Redis Cache Layer**
- **Purpose**: Store processed brain/alpha with 7-day freshness threshold
- **Keys**: `Hedge_Fund_Brain:{TICKER}:brain`, `Hedge_Fund_Brain:{TICKER}:alpha`

---

## Data Sources

The brain aggregates data from 6 specialized agents:

| Agent | Update Frequency | Description |
|-------|------------------|-------------|
| **Financial Metrics** | 15 days | Balance sheet, income statement, cash flow |
| **Market Expectation** | 24 hours | Stock trends, analyst ratings, price targets |
| **Earnings & Future** | 30 days | Earnings transcripts, guidance, strategy |
| **Macro Analyst** | Event-driven | Economic indicators, policy changes |
| **Revenue Segmentation** | Event-driven | Product lines, geographic breakdown |
| **Sector Analyst** | Event-driven | Industry trends, competitive landscape |

### Data Flow

```python
# 1. Update pool checks freshness and triggers updates
data = await update_pool(ticker)

# 2. Data dictionary structure
data = {
    "financial_metrics": {...},      # 15-day cache
    "market_expectation": {...},     # 24-hour cache
    "earnings_future": {...},        # 30-day cache
    "macro": {...},                  # Event-driven
    "revenue_segmentation": {...},   # Event-driven
    "sector": {...}                  # Event-driven
}

# 3. Brain pipeline processes all sources
brain, alpha = await generate_new_brain(ticker)
```

---

## Output Structure

### 1. Brain Object

A dictionary with 4 layers, each containing a list of factors:

```python
brain = {
    "Macro": [
        {
            "factor": "Fed Rate Cut 25 Basis Points",
            "dimension": "Monetary Policy",
            "sentiment": "Positive",
            "reasoning": "Lower rates reduce cost of capital..."
        }
    ],
    "Sector": [
        {
            "factor": "Retail Sector Valuation Compression",
            "dimension": "Sector Trends",
            "sentiment": "Negative",
            "reasoning": "P/E multiples declining due to..."
        }
    ],
    "Market": [
        {
            "factor": "Price Target Upgrades By Analysts",
            "dimension": "Market Expectation",
            "sentiment": "Positive",
            "reasoning": "Consensus target raised to..."
        }
    ],
    "Micro": [
        {
            "factor": "Q4 Earnings Exceeded Expectations",
            "dimension": "Financial Performance",
            "sentiment": "Positive",
            "reasoning": "EPS beat by 15%, revenue growth..."
        }
    ]
}
```

**Fields:**
- `factor` (str): Concise factor name
- `dimension` (str): Category (e.g., "Monetary Policy", "Financial Performance")
- `sentiment` (str): "Positive", "Negative", or "Neutral"
- `reasoning` (str): 1-2 sentence explanation

### 2. Alpha Insights

A list of actionable investment signals derived from the brain:

```python
alpha = [
    {
        "feature": "Margin Expansion Opportunity",
        "reasoning": "Cost reduction initiatives + pricing power = 200bps margin expansion over 12 months",
        "confidence": 0.78,
        "direction": "Bullish"
    },
    {
        "feature": "Tariff Risk Mispriced",
        "reasoning": "25% tariff exposure but stock only down 5%, implies market underestimating impact",
        "confidence": 0.65,
        "direction": "Bearish"
    }
]
```

**Fields:**
- `feature` (str): Alpha signal name
- `reasoning` (str): Detailed explanation (2-3 sentences)
- `confidence` (float): Confidence score (0.0 - 1.0)
- `direction` (str): "Bullish", "Bearish", or "Neutral"

---

## Advanced Usage

### 1. Accessing Specific Brain Layers

```python
brain, alpha = await hedgefundbrain("AAPL")

# Get all macro factors
for factor in brain["Macro"]:
    print(f"{factor['factor']}: {factor['sentiment']}")

# Filter by sentiment
positive_factors = [
    f for layer in ["Macro", "Sector", "Market", "Micro"]
    for f in brain[layer]
    if f["sentiment"] == "Positive"
]

# Group by dimension
from collections import defaultdict
by_dimension = defaultdict(list)
for layer in brain.values():
    for factor in layer:
        by_dimension[factor["dimension"]].append(factor)
```

### 2. Working with Alpha Insights

```python
# Sort by confidence
sorted_alpha = sorted(alpha, key=lambda x: x["confidence"], reverse=True)

# Filter by direction
bullish_signals = [a for a in alpha if a["direction"] == "Bullish"]

# High-confidence signals only
high_confidence = [a for a in alpha if a["confidence"] > 0.75]

# Generate summary
for insight in high_confidence:
    print(f"🎯 {insight['feature']} ({insight['confidence']:.0%})")
    print(f"   {insight['reasoning']}\n")
```

### 3. Force Fresh Update

```python
# Delete cached data to force regeneration
import redis

client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
client.delete(f"Hedge_Fund_Brain:{ticker}:brain")
client.delete(f"Hedge_Fund_Brain:{ticker}:alpha")

# Now calling hedgefundbrain will generate fresh data
brain, alpha = await hedgefundbrain(ticker)
```

### 4. Batch Processing Multiple Tickers

```python
async def analyze_portfolio(tickers: List[str]):
    results = {}
    
    for ticker in tickers:
        print(f"Processing {ticker}...")
        try:
            brain, alpha = await hedgefundbrain(ticker)
            results[ticker] = {
                "brain": brain,
                "alpha": alpha,
                "factor_count": sum(len(brain[l]) for l in brain),
                "alpha_count": len(alpha)
            }
        except Exception as e:
            print(f"❌ Error processing {ticker}: {e}")
            results[ticker] = {"error": str(e)}
    
    return results

# Run batch
portfolio = ["AAPL", "MSFT", "GOOGL", "TGT"]
results = await analyze_portfolio(portfolio)
```

---

## Caching & Update Logic

### Redis Storage

The brain and alpha are stored in Redis with timestamp metadata:

```python
# Storage format
{
    "brain": {...},           # 4-layer brain dict
    "alpha": [...],          # Alpha insights list
    "timestamp": "2025-10-23T10:30:00",  # ISO format
    "ticker": "TGT"
}
```

### Freshness Check (7-Day Window)

```python
async def check_freshness(ticker: str) -> bool:
    """
    Returns True if data exists and is < 7 days old
    Returns False if data is missing or > 7 days old
    """
    client = redis.Redis(...)
    brain_data = client.get(f"Hedge_Fund_Brain:{ticker}:brain")
    
    if not brain_data:
        return False  # No data
    
    data = json.loads(brain_data)
    timestamp = datetime.fromisoformat(data["timestamp"])
    age = datetime.now() - timestamp
    
    return age < timedelta(days=7)  # Fresh if < 7 days
```

### Update Cascade

When `hedgefundbrain()` detects stale data:

1. **Calls `update_pool(ticker)`** → Checks all 6 sub-agents
2. **Each sub-agent checks its own cache:**
   - Financial Metrics: 15-day threshold
   - Market Expectation: 24-hour threshold
   - Earnings & Future: 30-day threshold
   - Others: Event-driven (force update if missing)
3. **Only stale agents re-download data**
4. **Fresh agents return cached data**
5. **Brain pipeline processes the consolidated data**
6. **Results stored in Redis with new timestamp**

---

## Integration Examples

### Example 1: Real-Time Dashboard

```python
import streamlit as st
import asyncio

st.title("Hedge Fund Brain Dashboard")

ticker = st.text_input("Enter Ticker:", "TGT")

if st.button("Analyze"):
    with st.spinner("Generating intelligence..."):
        brain, alpha = asyncio.run(hedgefundbrain(ticker))
    
    # Display brain layers
    for layer in ["Macro", "Sector", "Market", "Micro"]:
        st.subheader(f"{layer} Layer ({len(brain[layer])} factors)")
        for factor in brain[layer]:
            sentiment_color = {
                "Positive": "🟢", 
                "Negative": "🔴", 
                "Neutral": "🟡"
            }[factor["sentiment"]]
            
            st.write(f"{sentiment_color} **{factor['factor']}**")
            st.write(f"_{factor['reasoning']}_")
    
    # Display alpha
    st.subheader(f"💡 Alpha Insights ({len(alpha)})")
    for insight in alpha:
        with st.expander(f"{insight['feature']} ({insight['confidence']:.0%})"):
            st.write(insight["reasoning"])
```

### Example 2: Automated Report Generation

```python
async def generate_investment_memo(ticker: str) -> str:
    brain, alpha = await hedgefundbrain(ticker)
    
    memo = f"""
    INVESTMENT MEMO: {ticker}
    Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
    
    EXECUTIVE SUMMARY
    =================
    Total Factors Identified: {sum(len(brain[l]) for l in brain)}
    Alpha Signals: {len(alpha)}
    
    BRAIN ANALYSIS
    ==============
    
    Macro Environment ({len(brain['Macro'])} factors)
    {format_layer(brain['Macro'])}
    
    Sector Context ({len(brain['Sector'])} factors)
    {format_layer(brain['Sector'])}
    
    Market Sentiment ({len(brain['Market'])} factors)
    {format_layer(brain['Market'])}
    
    Company Specifics ({len(brain['Micro'])} factors)
    {format_layer(brain['Micro'])}
    
    ALPHA INSIGHTS
    ==============
    {format_alpha(alpha)}
    """
    
    return memo

def format_layer(factors):
    lines = []
    for f in factors:
        lines.append(f"  • {f['factor']} ({f['sentiment']})")
        lines.append(f"    {f['reasoning']}")
    return "\n".join(lines)

def format_alpha(insights):
    lines = []
    for i, a in enumerate(insights, 1):
        lines.append(f"{i}. {a['feature']} ({a['confidence']:.0%} confidence)")
        lines.append(f"   Direction: {a['direction']}")
        lines.append(f"   Reasoning: {a['reasoning']}\n")
    return "\n".join(lines)
```

### Example 3: Flask API Endpoint

```python
from flask import Flask, jsonify, request
import asyncio

app = Flask(__name__)

@app.route('/api/brain/<ticker>', methods=['GET'])
def get_brain(ticker):
    try:
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        brain, alpha = loop.run_until_complete(hedgefundbrain(ticker.upper()))
        loop.close()
        
        return jsonify({
            "ticker": ticker,
            "brain": brain,
            "alpha": alpha,
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/brain/<ticker>/summary', methods=['GET'])
def get_summary(ticker):
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        brain, alpha = loop.run_until_complete(hedgefundbrain(ticker.upper()))
        loop.close()
        
        summary = {
            "ticker": ticker,
            "factor_counts": {
                layer: len(factors) 
                for layer, factors in brain.items()
            },
            "alpha_count": len(alpha),
            "sentiment_breakdown": {
                "positive": sum(
                    1 for layer in brain.values() 
                    for f in layer if f["sentiment"] == "Positive"
                ),
                "negative": sum(
                    1 for layer in brain.values() 
                    for f in layer if f["sentiment"] == "Negative"
                ),
                "neutral": sum(
                    1 for layer in brain.values() 
                    for f in layer if f["sentiment"] == "Neutral"
                )
            }
        }
        
        return jsonify(summary)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

---

## Troubleshooting

### Common Issues

#### 1. **ModuleNotFoundError: No module named 'Mid_Agent_Folder'**

**Solution:**
```python
import sys
import os

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
```

#### 2. **Redis Connection Error**

**Solution:**
```bash
# Start Redis server
redis-server

# Test connection
redis-cli ping
# Should return: PONG
```

#### 3. **Empty Brain or Alpha**

**Cause:** Sub-agents failed to download data or LLM extraction failed

**Solution:**
```python
# Check Redis for raw data
import redis
client = redis.Redis(decode_responses=True)

# Check if sub-agents have data
keys = client.keys("Financial_Metrics_INFOS:*")
print(f"Financial Metrics keys: {keys}")

# Force fresh update
client.delete(f"Hedge_Fund_Brain:{ticker}:brain")
client.delete(f"Hedge_Fund_Brain:{ticker}:alpha")

brain, alpha = await hedgefundbrain(ticker)
```

#### 4. **Slow Performance (> 60 seconds)**

**Cause:** All 6 sub-agents are downloading fresh data

**Solution:**
- **Pre-warm cache:** Run `update_pool(ticker)` separately beforehand
- **Batch processing:** Use `asyncio.gather()` for multiple tickers
- **Optimize sub-agents:** Check individual agent update thresholds

```python
# Pre-warm cache
from update_pool import update_pool
await update_pool(ticker)

# Then brain will use cached data
brain, alpha = await hedgefundbrain(ticker)  # Much faster
```

#### 5. **DeepSeek API Rate Limit**

**Solution:**
```python
# Add retry logic with exponential backoff
import time

async def hedgefundbrain_with_retry(ticker: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await hedgefundbrain(ticker)
        except Exception as e:
            if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 1s, 2s, 4s
                print(f"Rate limit hit, waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise
```

---

## Performance Metrics

### Typical Execution Times

| Scenario | Time | Description |
|----------|------|-------------|
| **Fresh Cache (< 7 days)** | ~1-2s | Redis retrieval only |
| **Partial Update** | ~20-40s | 1-2 sub-agents refresh |
| **Full Refresh** | ~60-90s | All 6 sub-agents update |
| **First Run** | ~90-120s | No cache, full pipeline |

### Optimization Tips

1. **Use caching aggressively**: 7-day window means daily queries hit cache
2. **Stagger batch updates**: Process tickers sequentially to avoid rate limits
3. **Monitor sub-agent freshness**: Check Redis keys to see what needs updating
4. **Pre-warm for latency-sensitive apps**: Run `update_pool()` in background

---

## API Reference

### Main Function

```python
async def hedgefundbrain(ticker: str) -> Tuple[Dict, List]:
    """
    Generate or retrieve brain and alpha insights for a ticker.
    
    Args:
        ticker (str): Stock ticker symbol (e.g., "AAPL", "TGT")
        
    Returns:
        Tuple[Dict, List]: (brain, alpha_insights)
            - brain: Dict with keys ["Macro", "Sector", "Market", "Micro"]
            - alpha_insights: List of alpha signal dicts
    
    Raises:
        ValueError: If ticker is invalid or data unavailable
        redis.ConnectionError: If Redis is unavailable
        
    Cache Logic:
        - Returns cached data if < 7 days old
        - Generates fresh data if > 7 days old or missing
        - Stores results in Redis automatically
    """
```

### Helper Functions

```python
async def check_freshness(ticker: str) -> bool:
    """Check if Redis data is < 7 days old"""

async def retrieve_from_redis(ticker: str) -> Tuple[Dict, List]:
    """Retrieve brain and alpha from Redis"""

async def store_to_redis(ticker: str, brain: Dict, alpha: List) -> None:
    """Store brain and alpha to Redis with timestamp"""

async def generate_new_brain(ticker: str) -> Tuple[Dict, List]:
    """Run full pipeline to generate fresh brain and alpha"""
```

---

## Related Documentation

- **`HEDGE_FUND_BRAIN_README.md`**: Architecture deep-dive
- **`USAGE.md`**: Quick usage examples
- **`update_pool.py`**: Sub-agent orchestration
- **`Data_Retrieval/`**: Individual sub-agent documentation

---

## Support & Contributing

### Questions?
- Check `HEDGE_FUND_BRAIN_README.md` for architecture details
- Review sub-agent docs in `Sub_Agent_Folder/`
- Inspect Redis keys: `redis-cli keys "Hedge_Fund_Brain:*"`

### Contributing
- Add new data sources in `Data_Retrieval/`
- Extend brain layers in `extractor_node()`
- Enhance alpha logic in `alpha_node()`

---

**Last Updated:** 2025-10-23  
**Version:** 1.0  
**Author:** Q&Q.AI Development Team

