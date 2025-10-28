# 🧠 Hedge Fund Brain - Developer Documentation

## **Overview**

The **Hedge Fund Brain** is an AI-powered investment analysis system that:
1. Collects comprehensive data from 6 specialized agents
2. Extracts earnings call Q&A and buy-side focus
3. Builds a multi-layered "brain" organizing insights by analytical scope
4. Discovers hidden alpha opportunities through LLM analysis
5. Stores results in Redis for fast retrieval

---

## **Table of Contents**

1. [Architecture Overview](#architecture-overview)
2. [Complete Workflow](#complete-workflow)
3. [Data Collection Layer](#data-collection-layer)
4. [Earnings Q&A Pipeline](#earnings-qa-pipeline)
5. [Brain Building Pipeline](#brain-building-pipeline)
6. [Redis Storage System](#redis-storage-system)
7. [Usage Examples](#usage-examples)
8. [API Reference](#api-reference)

---

## **Architecture Overview**

```
┌─────────────────────────────────────────────────────────────┐
│                    HEDGE FUND BRAIN                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ Data Layer   │ → │ Q&A Pipeline │ → │ Brain Build  │  │
│  └──────────────┘   └──────────────┘   └──────────────┘  │
│         ↓                  ↓                    ↓          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐  │
│  │ 6 Agents     │   │ Buy-Side     │   │ 4 Layers +   │  │
│  │ Data Pool    │   │ Focus        │   │ Alpha        │  │
│  └──────────────┘   └──────────────┘   └──────────────┘  │
│                                                             │
│                         ↓                                   │
│                 ┌──────────────┐                           │
│                 │ Redis Store  │                           │
│                 └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## **Complete Workflow**

### **High-Level Flow**

```python
run_hedge_fund_brain("TGT")
  │
  ├─> Step 1: update_pool() 
  │   └─> Check 6 agents for freshness, update only stale data
  │
  ├─> Step 2: get_*_data()
  │   └─> Retrieve: sector, earnings, financial, market, macro, revenue
  │
  ├─> Step 3: Earnings Q&A Pipeline (LangGraph)
  │   ├─> extract_qa_pairs: Parse transcript → Q&A JSON
  │   └─> generate_buy_side_focus: Analyze strategy → 3 priorities
  │
  ├─> Step 4: Brain Building Pipeline (LangGraph)
  │   ├─> extractor_node: Classify & extract features
  │   ├─> reflect_node: Merge duplicates, refine
  │   └─> alpha_node: Find hidden opportunities
  │
  └─> Step 5: store_to_redis()
      └─> Save brain + alpha to Redis
```

---

## **Data Collection Layer**

### **1. Smart Update Pool**

**Function:** `update_pool(ticker, agents_list)`

**Logic:**
```python
For each agent:
  1. Check Redis for existing data
  2. Check timestamp against threshold:
     - Market_Expectation: 24 hours
     - Financial_Metrics: Daily (after 6 PM)
     - Earnings: 24 hours
     - Macro: 7 days
     - Sector: 30 days
     - Revenue: Earnings date or 24 hours
  3. If stale → Update concurrently
  4. If fresh → Skip update
```

**Benefits:**
- ⚡ Fast: Only updates what's needed
- 💰 Cost-effective: Avoids redundant API calls
- 🔄 Concurrent: Updates multiple agents in parallel

### **2. Data Retrieval Functions**

**Pattern:** All follow same structure (dataclass + helper methods)

```python
result = await get_sector_data(ticker)
  ↓
Returns: SectorResult dataclass with:
  - Direct attributes: result.ticker, result.competitor_summary
  - Helper methods: result.get_answer(key), result.get_competitors_list()
  - Properties: result.reasoning, result.confidence_score
  - Raw data: result.raw_data (full dict)
```

**Available Functions:**
| Function | Returns | Key Fields |
|----------|---------|------------|
| `get_earnings_data(ticker)` | EarningsResult | transcript, future_development, earning_date |
| `get_sector_data(ticker)` | SectorResult | asset_relative, competitor_summary, answer_collection |
| `get_financial_metrics_data(ticker)` | FinancialMetricsResult | dcf_value, financial_metrics, price_data |
| `get_market_expectation_data(ticker)` | MarketExpectationResult | current_trends, historical_trends |
| `get_macro_data()` | MacroResult | analysis, indicators, macro_data |
| `get_revenue_segmentation_data(ticker)` | RevenueSegmentationResult | business_segments, cost_segments, supplier_segments |

---

## **Earnings Q&A Pipeline**

### **LangGraph Workflow**

```
extract_qa_pairs → generate_buy_side_focus
```

### **Node 1: extract_qa_pairs**

**Input State:**
```python
{
  "transcript": "Full earnings call transcript...",
  "future_development": "Company strategy...",
  "qa_pairs": None,
  "buy_side_focus": None
}
```

**Processing:**
1. **LLM Prompt:**
   ```
   "Extract 2-5 Q&A pairs from earnings transcript"
   Expected format: {"Q1": "...", "A1": "...", "Q2": "...", "A2": "..."}
   ```

2. **Parse JSON:**
   - Try `json.loads(response)`
   - If fails → Use regex to extract Q&A patterns
   - If still fails → Fallback to summary format

3. **Output:**
   ```python
   state["qa_pairs"] = {
     "Q1": "What are growth priorities?",
     "A1": "Focus on digital expansion...",
     "Q2": "How will margins evolve?",
     "A2": "Cost controls improving..."
   }
   ```

### **Node 2: generate_buy_side_focus**

**Input:** Q&A pairs + future development

**LLM Prompt:**
```
"Analyze company strategy + Q&A.
Identify top 3 strategic priorities:
- How to grow revenue
- How to improve sales  
- How executives are working

Return 3 bullet points."
```

**Output:**
```python
state["buy_side_focus"] = """
1. Recapture merchandising authority through style leadership
2. Elevate guest experience and leverage technology
3. Execute with urgency on category transformations
"""
```

**Why This Matters:**
- Buy-side focus = What investors ACTUALLY care about
- Used in alpha discovery to find under-discussed opportunities

---

## **Brain Building Pipeline**

### **The 4-Layer Brain Structure**

```
┌─────────────────────────────────────────────────┐
│ MACRO Layer                                     │
│ - Economy-wide factors (GDP, rates, employment) │
│ - Affects ALL companies                         │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│ SECTOR Layer                                    │
│ - Industry trends (digitization, regulations)   │
│ - Affects companies in same industry            │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│ MARKET Layer                                    │
│ - Competitive positioning (market share, rivals)│
│ - Company vs competitors                        │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│ MICRO Layer                                     │
│ - Company-specific (revenue mix, costs, moats)  │
│ - Unique to this ticker                         │
└─────────────────────────────────────────────────┘
```

### **LangGraph Workflow**

```
extractor_node → reflect_node → alpha_node
```

---

### **Node 1: extractor_node**

**Purpose:** Process all input data and extract structured features.

**Input:**
```python
inputs_to_process = [
  {"text": "Macro analysis...", "context_name": "Macro environment"},
  {"text": "Sector trends...", "context_name": "Industry trend"},
  {"text": "Competitive landscape...", "context_name": "Competitive landscape"},
  {"text": "Revenue segments...", "context_name": "Revenue breakdown"},
  {"text": "Cost structure...", "context_name": "Cost structure"},
  {"text": "Suppliers...", "context_name": "Supplier analysis"},
  ...
]
```

**Processing (For Each Input):**

1. **LLM Classification:**
   ```
   Prompt: "Classify this text into Macro/Sector/Market/Micro layer"
   
   Returns:
   {
     "layer": "Micro",
     "factor": "Revenue concentration and diversification",
     "features": [
       {
         "statement": "85-90% revenue from large-format retail",
         "evidence": "General Merchandise accounts for $90-95B annually",
         "confidence": 0.9
       },
       ...
     ]
   }
   ```

2. **Feature Extraction:**
   - Each feature has: statement (what), evidence (proof), confidence (0-1)
   - 2-5 features per input
   - All features are unique truths or structural insights

3. **Layer Assignment:**
   ```python
   state["Micro"].append({
     "factor": "Revenue concentration",
     "features": [...],
     "context": "Revenue breakdown",
     "created_at": "2025-10-21T..."
   })
   ```

**Output:**
```python
state = {
  "Macro": [factor1],          # 1 factor, 4 features
  "Sector": [factor1],         # 1 factor, 4 features
  "Market": [factor1],         # 1 factor, 4 features
  "Micro": [factor1, factor2, factor3]  # 3 factors, 12 features
}
```

---

### **Node 2: reflect_node**

**Purpose:** Clean, merge, and refine extracted features.

**Processing (For Each Layer):**

1. **LLM Reflection:**
   ```
   Prompt: "Review these factors, merge duplicates, keep top 16"
   
   Input: All factors from one layer
   
   LLM analyzes:
   - Are there duplicate insights?
   - Can we merge similar features?
   - Which have highest confidence?
   - Is reasoning clear?
   ```

2. **Refinement:**
   ```python
   # Before reflection:
   Micro: [
     {factor: "Cost efficiency", features: [...]},
     {factor: "Cost structure", features: [...]},  # Duplicate!
     {factor: "Revenue mix", features: [...]}
   ]
   
   # After reflection:
   Micro: [
     {factor: "Cost efficiency & structure", features: [...]},  # Merged
     {factor: "Revenue concentration", features: [...]}
   ]
   ```

3. **Limit to Top 16:**
   - Sorts by confidence
   - Keeps only top 16 factors per layer
   - Prevents information overload

**Output:** Clean, non-redundant brain

---

### **Node 3: alpha_node**

**Purpose:** Find hidden opportunities (low visibility + high impact).

**Input:** Complete brain + buy-side focus

**LLM Analysis:**

1. **Identify Priced-In Features:**
   ```
   "Which features are widely discussed?"
   
   Example: E-commerce growth challenges
   → High visibility (everyone talks about it)
   → Likely already priced into stock
   ```

2. **Identify Hidden Alpha:**
   ```
   "Which features are under-discussed but important?"
   
   Example: Retail media network revenue
   → Low visibility (not widely covered)
   → High impact (3-5% revenue, high margins)
   → ALPHA OPPORTUNITY
   ```

3. **Rank by Alpha Potential:**
   ```
   Criteria:
   - Visibility: Low (market doesn't see it)
   - Expected Impact: High (matters to earnings)
   - Confidence: >0.8 (high conviction)
   ```

**Output:**
```python
{
  "alpha_insights": [
    {
      "feature": "Retail media network monetization",
      "layer": "Micro",
      "reason_alpha": "3-5% revenue, high margins, undervalued by market",
      "visibility": "Low",
      "expected_impact": "High",
      "confidence": 0.87
    },
    {
      "feature": "Operational cost improvements",
      "layer": "Micro",
      "reason_alpha": "COGS -2%, SG&A -10.8%, market misses margin story",
      "visibility": "Low",
      "expected_impact": "High",
      "confidence": 0.85
    },
    {
      "feature": "Supplier ecosystem moat",
      "layer": "Micro",
      "reason_alpha": "Partnerships drive traffic, undervalued vs e-commerce",
      "visibility": "Low",
      "expected_impact": "Medium",
      "confidence": 0.82
    }
  ]
}
```

---

## **Redis Storage System**

### **Storage Architecture**

```
Redis Database: Stock Trend Redis
Host: redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com
Port: 16376

Key Structure:
  Hedge_Fund_Brain:{TICKER}:brain   → Brain data (4 layers)
  Hedge_Fund_Brain:{TICKER}:alpha   → Alpha insights
```

### **Data Structures**

**Brain Storage:**
```json
{
  "ticker": "TGT",
  "brain": {
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
        "created_at": "2025-10-21T00:26:52.574493"
      }
    ],
    "Sector": [...],
    "Market": [...],
    "Micro": [...]
  },
  "stored_at": "2025-10-21T00:30:00.000000",
  "total_factors": 6
}
```

**Alpha Storage:**
```json
{
  "ticker": "TGT",
  "alpha_insights": [
    {
      "feature": "Retail media network monetization",
      "layer": "Micro",
      "reason_alpha": "3-5% revenue, high margins, undervalued",
      "visibility": "Low",
      "expected_impact": "High",
      "confidence": 0.87
    },
    ...
  ],
  "stored_at": "2025-10-21T00:30:00.000000",
  "insight_count": 3
}
```

### **Storage Functions**

**store_to_redis(ticker, brain, insights)**
```python
Purpose: Save brain + alpha to Redis
  
Logic:
  1. Create brain package with metadata
  2. Store to: Hedge_Fund_Brain:{TICKER}:brain
  3. Create alpha package with metadata
  4. Store to: Hedge_Fund_Brain:{TICKER}:alpha
  5. Return: True/False

No expiration - data persists until overwritten
```

**get_from_redis(ticker)**
```python
Purpose: Retrieve brain + alpha from Redis
  
Logic:
  1. Fetch both keys
  2. Parse JSON
  3. Return: {brain, alpha, status}
  
Returns:
  - status="success" if both found
  - status="not_found" if missing
  - status="error" if exception
```

---

## **Usage Examples**

### **Example 1: Run Complete Analysis**

```python
from Mid_Agent_Folder.Hedge_Fund_Brain import run_hedge_fund_brain

# Run complete workflow
result = await run_hedge_fund_brain("TGT")

# Access results
brain = result["brain"]
insights = result["alpha_insights"]

# Display alpha opportunities
for insight in insights:
    print(f"{insight['feature']}: {insight['reason_alpha']}")
```

### **Example 2: Retrieve from Redis**

```python
from Mid_Agent_Folder.Hedge_Fund_Brain import get_from_redis

# Get stored analysis
data = await get_from_redis("TGT")

if data["status"] == "success":
    brain = data["brain"]["brain"]
    alpha = data["alpha"]["alpha_insights"]
    
    print(f"Macro factors: {len(brain['Macro'])}")
    print(f"Alpha insights: {len(alpha)}")
```

### **Example 3: Command Line**

```bash
# Run analysis and store to Redis
python Hedge_Fund_Brain.py TGT

# Retrieve existing analysis
python Hedge_Fund_Brain.py TGT --retrieve
```

### **Example 4: Jupyter Notebook**

```python
# In notebook
import sys
sys.path.insert(0, '../')

from Mid_Agent_Folder.Hedge_Fund_Brain import run_hedge_fund_brain

result = await run_hedge_fund_brain("AAPL")
```

---

## **API Reference**

### **Main Function**

**`run_hedge_fund_brain(ticker: str) -> Dict`**

**Parameters:**
- `ticker` (str): Stock ticker symbol (e.g., "TGT", "AAPL")

**Returns:**
```python
{
  "ticker": str,
  "brain": {
    "Macro": [factor_dict, ...],
    "Sector": [factor_dict, ...],
    "Market": [factor_dict, ...],
    "Micro": [factor_dict, ...]
  },
  "alpha_insights": [insight_dict, ...],
  "buy_side_focus": str,
  "status": "success" | "failed"
}
```

**Factor Dictionary Structure:**
```python
{
  "factor": "Factor name",
  "features": [
    {
      "statement": "What the feature is",
      "evidence": "Supporting data/proof",
      "confidence": 0.85  # 0-1 scale
    }
  ],
  "context": "Source of this factor",
  "created_at": "ISO timestamp"
}
```

**Alpha Insight Structure:**
```python
{
  "feature": "Opportunity name",
  "layer": "Macro|Sector|Market|Micro",
  "reason_alpha": "Why it's hidden alpha",
  "visibility": "Low|Medium|High",
  "expected_impact": "Low|Medium|High",
  "confidence": 0.85  # 0-1 scale
}
```

---

### **Storage Functions**

**`store_to_redis(ticker, brain, insights) -> bool`**

Stores brain and alpha insights to Redis.

**Parameters:**
- `ticker` (str): Stock ticker
- `brain` (dict): Brain with 4 layers
- `insights` (list): Alpha insights list

**Returns:** `True` if successful, `False` otherwise

**Redis Keys Created:**
- `Hedge_Fund_Brain:{TICKER}:brain`
- `Hedge_Fund_Brain:{TICKER}:alpha`

---

**`get_from_redis(ticker) -> dict`**

Retrieves brain and alpha from Redis.

**Parameters:**
- `ticker` (str): Stock ticker

**Returns:**
```python
{
  "brain": {...},      # Brain package with metadata
  "alpha": {...},      # Alpha package with metadata
  "status": "success" | "not_found" | "error"
}
```

---

## **Data Flow Diagram**

```
INPUT SOURCES:
├─ Macro Analysis     → Economic indicators, business cycle
├─ Sector Trends      → Industry transformation, digitization
├─ Competitive Data   → Market share, competitor positioning
├─ Earnings Call      → Transcript, Q&A, future strategy
├─ Revenue Data       → Segments, cost structure, suppliers
└─ Financial Metrics  → DCF, ratios, price data

         ↓ (Extract & Classify)

4-LAYER BRAIN:
├─ MACRO:  Economic factors affecting all stocks
├─ SECTOR: Industry trends affecting sector
├─ MARKET: Competitive factors affecting rivals
└─ MICRO:  Company-specific factors

         ↓ (Reflect & Refine)

CLEANED BRAIN:
├─ Remove duplicates
├─ Merge similar factors
├─ Keep top 16 per layer
└─ Clarify reasoning

         ↓ (Alpha Discovery)

ALPHA INSIGHTS:
├─ Feature 1: Low visibility + High impact
├─ Feature 2: Low visibility + High impact
└─ Feature 3: Low visibility + Medium impact

         ↓ (Store)

REDIS:
├─ Hedge_Fund_Brain:{TICKER}:brain
└─ Hedge_Fund_Brain:{TICKER}:alpha
```

---

## **Key Design Decisions**

### **1. Why 4 Layers?**

**Macro → Sector → Market → Micro** follows investment analysis hierarchy:
- **Macro**: Top-down macro environment (affects all)
- **Sector**: Industry-level trends (affects sector peers)
- **Market**: Competitive dynamics (affects market position)
- **Micro**: Company fundamentals (affects only this ticker)

This structure mirrors how professional analysts think.

### **2. Why LangGraph?**

**Benefits:**
- **State management**: Clean data flow between nodes
- **Modularity**: Easy to add/remove steps
- **Error isolation**: One node fails, others continue
- **Debuggability**: Clear execution path

### **3. Why Reflection Node?**

**Without reflection:**
- Duplicates: "Cost efficiency" + "Cost structure" = redundant
- Noise: Too many low-confidence features
- Unclear: Vague statements without strong evidence

**With reflection:**
- Merged factors
- Top 16 by confidence only
- Clear, actionable insights

### **4. Why Separate Brain + Alpha Storage?**

**Brain** = Complete knowledge base (large, detailed)
**Alpha** = Actionable insights (small, focused)

Allows:
- Quick alpha retrieval without loading full brain
- Independent updates
- Flexible querying patterns

---

## **Performance Characteristics**

### **Typical Execution Time**

| Step | Time | Notes |
|------|------|-------|
| Update Pool | 1-120s | Depends on how many agents need updates |
| Data Retrieval | 2-5s | Fast if data is cached |
| Q&A Extraction | 10-15s | LLM processing transcript |
| Brain Building | 30-45s | 8 LLM calls (extraction) |
| Reflection | 15-20s | 4 LLM calls (merge) |
| Alpha Discovery | 10-15s | 1 LLM call |
| Redis Storage | <1s | Fast write |
| **Total** | **70-180s** | **~1-3 minutes** |

### **Cost (Estimated)**

Using DeepSeek (very cheap):
- Input tokens: ~50K tokens
- Output tokens: ~15K tokens
- Cost: ~$0.03 per ticker analysis

### **Data Volume**

| Component | Size |
|-----------|------|
| Raw collected data | ~500KB |
| Brain (4 layers) | ~20KB |
| Alpha insights | ~2KB |
| Total Redis storage | ~25KB per ticker |

---

## **Error Handling**

### **Graceful Degradation**

```python
If agent data unavailable:
  → Skip that input, continue with others

If JSON parsing fails:
  → Use regex fallback or skip

If LLM call fails:
  → Return previous state, log error

If Redis storage fails:
  → Return results anyway, log warning
```

### **Common Issues**

**Issue 1: Empty Q&A extraction**
```
Cause: Transcript too long (>60K chars)
Fix: Truncate to 3000 chars in prompt (line 92)
```

**Issue 2: JSON parsing errors**
```
Cause: LLM returns markdown fences
Fix: Clean with split("```json")
```

**Issue 3: Module not found**
```
Cause: Path issues in different environments
Fix: sys.path.insert(0, parent_dir)
```

---

## **Extension Guide**

### **Add New Data Source**

1. Create `get_new_data.py` in `Data_Retrieval/`
2. Add to imports in `Hedge_Fund_Brain.py`
3. Add to `inputs_list` with context_name
4. Done! Brain will automatically process it

### **Add New Layer**

1. Update `BrainState` TypedDict:
   ```python
   class BrainState(TypedDict):
       Macro: List
       Sector: List
       Market: List
       Micro: List
       Technical: List  # NEW LAYER
   ```

2. Update extractor, reflector, alpha nodes to include new layer

3. Update Redis storage structure

### **Customize Alpha Discovery**

Edit `alpha_node` prompt to focus on:
- Different investment styles (value, growth, momentum)
- Specific risk factors
- Time horizons (short-term catalysts vs long-term moats)

---

## **Best Practices**

### **For Production Use**

1. **Add Error Logging:**
   ```python
   import logging
   logging.basicConfig(filename='brain.log', level=logging.INFO)
   ```

2. **Add Retry Logic:**
   ```python
   for attempt in range(3):
       try:
           result = llm_tool(prompt)
           break
       except:
           if attempt == 2:
               raise
   ```

3. **Add Data Validation:**
   ```python
   if len(brain["Macro"]) == 0:
       raise ValueError("No macro factors extracted")
   ```

4. **Add Performance Monitoring:**
   ```python
   start_time = time.time()
   # ... workflow ...
   duration = time.time() - start_time
   log_performance(ticker, duration)
   ```

### **For Development**

1. **Test with sample ticker first** (e.g., "TGT")
2. **Check Redis after each run** to verify storage
3. **Review alpha insights** for quality
4. **Adjust LLM temperature** if output too random/too rigid

---

## **Troubleshooting**

### **Debug Mode**

Add to any cell:
```python
# Check what's in each layer
for layer in ["Macro", "Sector", "Market", "Micro"]:
    print(f"\n{layer}:")
    for factor in final_state[layer]:
        print(f"  - {factor['factor']}")
        print(f"    Features: {len(factor['features'])}")
```

### **Verify Redis Storage**

```python
import redis

client = redis.Redis(
    host="redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
    port=16376,
    username="default",
    password="rl8242B4UItBhFzgHW5APEqZnkYoaEZv",
    decode_responses=True
)

# Check if keys exist
brain_key = "Hedge_Fund_Brain:TGT:brain"
alpha_key = "Hedge_Fund_Brain:TGT:alpha"

print(f"Brain exists: {client.exists(brain_key)}")
print(f"Alpha exists: {client.exists(alpha_key)}")

# Get data
brain_data = client.get(brain_key)
print(json.loads(brain_data) if brain_data else "No brain data")
```

---

## **FAQ**

**Q: How often should I run this?**
A: When new earnings are released or when agent data becomes stale (based on update_pool thresholds).

**Q: Can I customize the layers?**
A: Yes, edit the BrainState TypedDict and update all nodes to handle the new layer.

**Q: What if LLM is slow?**
A: Use `temperature=0` for faster, more deterministic responses. Or switch to faster model.

**Q: How do I add more alpha criteria?**
A: Edit the `alpha_node` prompt to include your specific investment criteria.

**Q: Can I use this for multiple tickers?**
A: Yes, just loop through tickers. Each stores independently in Redis.

---

## **Version History**

- **v1.0** (2025-10-21): Initial release
  - 4-layer brain structure
  - Earnings Q&A extraction
  - Alpha discovery via LLM
  - Redis storage

---

## **Credits**

Built with:
- LangChain / LangGraph (Workflow orchestration)
- DeepSeek (LLM provider)
- Redis (Data persistence)
- 6 Specialized Agents (Data collection)

---

## **License**

Internal use only.

---

**For questions or issues, contact the development team.**

