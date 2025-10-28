# 🧠 Hedge Fund Brain - Simple Usage Guide

## **One-Line Interface**

```python
from Mid_Agent_Folder.Hedge_Fund_Brain import hedgefundbrain

brain, alpha = await hedgefundbrain("TGT")
```

That's it! ✅

---

## **What It Does Automatically**

### **Smart 7-Day Caching Logic:**

```
hedgefundbrain("TGT")
    ↓
Check Redis: Hedge_Fund_Brain:TGT:brain
    ↓
Is data < 7 days old?
    ├─ YES → ✅ Retrieve from Redis (instant)
    │         Return cached brain + alpha
    │
    └─ NO  → 🔄 Generate fresh analysis
              ├─ Update 6 agents (only stale ones)
              ├─ Extract earnings Q&A
              ├─ Build 4-layer brain
              ├─ Discover alpha insights
              ├─ Store to Redis
              └─ Return new brain + alpha
```

**Benefits:**
- ⚡ Fast if data is fresh (< 1 second)
- 🔄 Auto-updates if stale (1-3 minutes)
- 💾 Cached in Redis for 7 days
- 🎯 No configuration needed

---

## **What You Get Back**

### **Brain (Dict):**
```python
brain = {
    "Macro": [
        {
            "factor": "Business Cycle Phase Transition",
            "features": [
                {
                    "statement": "Economy shows mixed signals...",
                    "evidence": "GDP 0.95%, unemployment rising 2.38%",
                    "confidence": 0.88
                },
                ...
            ],
            "context": "Macro environment",
            "created_at": "2025-10-21T..."
        }
    ],
    "Sector": [...],   # Industry-level factors
    "Market": [...],   # Competitive factors
    "Micro": [...]     # Company-specific factors
}
```

### **Alpha (List):**
```python
alpha = [
    {
        "feature": "Retail media network monetization",
        "layer": "Micro",
        "reason_alpha": "3-5% revenue, high margins, undervalued by market",
        "visibility": "Low",      # Under-discussed
        "expected_impact": "High", # High potential
        "confidence": 0.87
    },
    {...},  # Insight 2
    {...}   # Insight 3
]
```

---

## **Usage Examples**

### **Example 1: Basic Usage (Jupyter/IPython)**

```python
# Import
from Mid_Agent_Folder.Hedge_Fund_Brain import hedgefundbrain

# Get brain + alpha
brain, alpha = await hedgefundbrain("TGT")

# Access brain layers
print(f"Macro factors: {len(brain['Macro'])}")
print(f"Sector factors: {len(brain['Sector'])}")
print(f"Market factors: {len(brain['Market'])}")
print(f"Micro factors: {len(brain['Micro'])}")

# Access alpha insights
for insight in alpha:
    print(f"✨ {insight['feature']}")
    print(f"   Why: {insight['reason_alpha']}")
```

### **Example 2: Command Line**

```bash
python Hedge_Fund_Brain.py TGT
```

Output:
```
✅ Fresh data found for TGT (< 7 days old)
   Retrieved from Redis: 6 factors, 3 insights

🧠 BRAIN SUMMARY:
  Macro: 1 factors
  Sector: 1 factors
  Market: 1 factors
  Micro: 3 factors

💡 ALPHA INSIGHTS:
  1. Retail media network monetization
  2. Operational cost improvements
  3. Supplier ecosystem moat
```

### **Example 3: Multiple Tickers**

```python
tickers = ["TGT", "WMT", "COST"]

for ticker in tickers:
    brain, alpha = await hedgefundbrain(ticker)
    print(f"\n{ticker}:")
    print(f"  Alpha opportunities: {len(alpha)}")
```

### **Example 4: Force Fresh Update**

```python
# Delete from Redis to force fresh generation
import redis

client = redis.Redis(
    host="redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
    port=16376,
    username="default",
    password="rl8242B4UItBhFzgHW5APEqZnkYoaEZv",
    decode_responses=True
)

# Delete existing data
client.delete(f"Hedge_Fund_Brain:TGT:brain")
client.delete(f"Hedge_Fund_Brain:TGT:alpha")

# Now run - will generate fresh
brain, alpha = await hedgefundbrain("TGT")
```

---

## **What's Inside Each Layer**

### **Macro Layer**
Economy-wide factors affecting ALL stocks:
- GDP growth, interest rates, unemployment
- Federal Reserve policy, inflation
- Business cycle phase

**Example:**
```python
for factor in brain["Macro"]:
    print(f"Factor: {factor['factor']}")
    for feature in factor['features']:
        print(f"  - {feature['statement']}")
```

### **Sector Layer**
Industry trends affecting sector peers:
- Digitization, regulatory changes
- Consumer behavior shifts
- Technology disruption

### **Market Layer**
Competitive dynamics:
- Market share distribution
- Competitor positioning
- Competitive advantages

### **Micro Layer**
Company-specific insights:
- Revenue mix, cost structure
- Strategic initiatives
- Operational efficiency

---

## **Understanding Alpha Insights**

### **What Makes Something "Alpha"?**

Alpha = **Low Visibility + High Impact**

```python
insight = {
    "feature": "Retail media network",
    "visibility": "Low",      # ← Market doesn't discuss it much
    "expected_impact": "High", # ← But it matters for earnings
    "confidence": 0.87        # ← 87% confident this is alpha
}
```

**Why Low Visibility Matters:**
- If everyone knows → Already priced into stock
- If few know → Opportunity for alpha

**Why High Impact Matters:**
- Will affect future earnings
- Creates trading opportunity

### **How to Use Alpha Insights:**

```python
for insight in alpha:
    if insight['confidence'] > 0.85 and insight['expected_impact'] == "High":
        print(f"🎯 HIGH CONVICTION ALPHA:")
        print(f"   {insight['feature']}")
        print(f"   {insight['reason_alpha']}")
        # → Consider this in your investment thesis
```

---

## **Performance**

### **Cached Data (< 7 days old):**
- ⚡ Speed: < 1 second
- 💰 Cost: $0 (no API calls)
- 📊 Data: Same as last run

### **Fresh Generation (> 7 days or missing):**
- ⏱️ Speed: 1-3 minutes
- 💰 Cost: ~$0.03 (DeepSeek API)
- 📊 Data: Latest information

---

## **Redis Storage**

### **Keys:**
```
Hedge_Fund_Brain:{TICKER}:brain   → Brain data (4 layers)
Hedge_Fund_Brain:{TICKER}:alpha   → Alpha insights
```

### **Retention:**
- Data persists indefinitely
- Overwritten on each update
- 7-day freshness threshold

---

## **Troubleshooting**

### **Issue: "No fresh data, generating new" every time**

**Cause:** Redis data missing or corrupted

**Fix:**
```python
# Check Redis manually
import redis
client = redis.Redis(...)
print(client.exists("Hedge_Fund_Brain:TGT:brain"))  # Should be 1
```

### **Issue: Empty brain or alpha**

**Cause:** Agent data not available

**Fix:**
```python
# Run update_pool first to ensure data exists
from update_pool import update_pool
await update_pool("TGT", ["Sector_Analyst_Agent", ...])
```

### **Issue: Function hangs**

**Cause:** LLM timeout or network issue

**Fix:** Wait or retry. DeepSeek typically responds in 5-10 seconds.

---

## **Advanced Usage**

### **Check Freshness Without Running:**

```python
from Mid_Agent_Folder.Hedge_Fund_Brain import check_freshness

is_fresh = await check_freshness("TGT")
print(f"Data is fresh: {is_fresh}")
```

### **Manual Redis Retrieval:**

```python
from Mid_Agent_Folder.Hedge_Fund_Brain import retrieve_from_redis

brain, alpha = await retrieve_from_redis("TGT")

if brain:
    print("Data found in Redis")
else:
    print("No data in Redis")
```

### **Force New Generation:**

```python
from Mid_Agent_Folder.Hedge_Fund_Brain import generate_new_brain

# Bypass cache, always generate fresh
brain, alpha = await generate_new_brain("TGT")
```

---

## **Integration Examples**

### **In Your Trading System:**

```python
async def analyze_portfolio(tickers: list):
    """Analyze multiple tickers for alpha opportunities"""
    
    results = {}
    
    for ticker in tickers:
        brain, alpha = await hedgefundbrain(ticker)
        
        # Filter high-conviction alpha
        high_conviction = [
            a for a in alpha 
            if a['confidence'] > 0.85 and a['expected_impact'] == "High"
        ]
        
        results[ticker] = {
            "brain": brain,
            "high_conviction_alpha": high_conviction
        }
    
    return results


# Run
portfolio = ["TGT", "WMT", "COST", "AMZN"]
analysis = await analyze_portfolio(portfolio)
```

### **In a Scheduler:**

```python
import schedule
import asyncio

async def daily_brain_update():
    """Run every morning to refresh stale data"""
    
    tickers = ["TGT", "WMT", "AAPL", "TSLA"]
    
    for ticker in tickers:
        brain, alpha = await hedgefundbrain(ticker)
        print(f"✅ Updated {ticker}")

# Schedule for 6 AM daily
schedule.every().day.at("06:00").do(lambda: asyncio.run(daily_brain_update()))
```

---

## **API Quick Reference**

### **Main Function**

**`hedgefundbrain(ticker: str) -> Tuple[Dict, List]`**

**Returns:**
- `brain` (Dict): 4-layer knowledge structure
- `alpha` (List): 3 alpha insights

**Auto-updates:** If data > 7 days old

---

### **Helper Functions**

**`check_freshness(ticker: str) -> bool`**

Returns `True` if data < 7 days old

---

**`retrieve_from_redis(ticker: str) -> Tuple[Dict, List]`**

Manual Redis retrieval

---

**`generate_new_brain(ticker: str) -> Tuple[Dict, List]`**

Force fresh generation (bypass cache)

---

## **That's It!**

One import, one function call:

```python
from Mid_Agent_Folder.Hedge_Fund_Brain import hedgefundbrain

brain, alpha = await hedgefundbrain("TGT")
```

**Simple. Fast. Smart.** 🚀


