# 🔄 LangGraph Pattern Analysis - Your Codebase

## Overview
Based on `Hedge_Fund_Brain.py`, here's how you structure LangGraph workflows:

---

## 📦 1. State Definition (TypedDict)

You use Python `TypedDict` to define state schemas:

```python
from typing import TypedDict, Optional, List, Dict, Any

class EarningsPipelineState(TypedDict):
    future_development: str
    transcript: str
    qa_pairs: Optional[Dict[str, str]]
    buy_side_focus: Optional[str]

class BrainState(TypedDict):
    Macro: List[Dict[str, Any]]
    Sector: List[Dict[str, Any]]
    Market: List[Dict[str, Any]]
    Micro: List[Dict[str, Any]]
    inputs_to_process: List[Dict[str, str]]
    buy_side_focus: str
    alpha_insights: Dict[str, Any]
    last_updated: str
```

**Key Pattern:**
- `TypedDict` ensures type safety
- Optional fields use `Optional[Type]`
- Complex nested structures use `List[Dict[str, Any]]`

---

## 🔧 2. Node Functions

Each node is a **function that takes state and returns state**:

```python
def extract_qa_pairs(state: EarningsPipelineState) -> EarningsPipelineState:
    """Extract Q&A from transcript"""
    extractor_llm = ChatDeepSeek(model="deepseek-chat", temperature=0.5, max_tokens=2000)
    
    prompt = f"""Extract 2-5 Q&A pairs from this earnings transcript.
Return ONLY valid JSON: {{"Q1": "...", "A1": "...", "Q2": "...", "A2": "..."}}

Transcript: {state['transcript'][:3000]}..."""
    
    response = extractor_llm.invoke(prompt)
    text = response.content.strip()
    
    # Parse JSON
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    
    try:
        qa_json = json.loads(text)
    except:
        qa_json = {"Q1": "Parse error", "A1": "Unable to extract"}
    
    state["qa_pairs"] = qa_json  # Modify state
    return state  # Return modified state


def generate_buy_side_focus(state: EarningsPipelineState) -> EarningsPipelineState:
    """Analyze company strategy"""
    analyst_llm = ChatDeepSeek(model="deepseek-chat", temperature=0.5, max_tokens=800)
    
    prompt = f"""Analyze company strategy and identify top 3 priorities.

Future Development: {state['future_development']}
Q&A: {json.dumps(state['qa_pairs'], indent=2)}

Return 3 bullets (≤2 lines each):
1. [Priority + Action]
2. [Priority + Action]  
3. [Priority + Action]"""
    
    response = analyst_llm.invoke(prompt)
    text = response.content.strip()
    
    if not text.startswith("1."):
        text = "1. " + text
    
    state["buy_side_focus"] = text
    return state
```

**Key Pattern:**
- Function signature: `def node_name(state: StateType) -> StateType:`
- Read from state: `state["field_name"]`
- Modify state: `state["field_name"] = new_value`
- Always return the modified state

---

## 🏗️ 3. Graph Building

Your graph construction follows this pattern:

### Pattern 1: Simple Linear Pipeline

```python
from langgraph.graph import StateGraph, START, END

# Create graph with state type
earnings_graph = StateGraph(EarningsPipelineState)

# Add nodes (node_name, function)
earnings_graph.add_node("extract_qa", extract_qa_pairs)
earnings_graph.add_node("buy_side_focus", generate_buy_side_focus)

# Add edges (from → to)
earnings_graph.add_edge(START, "extract_qa")
earnings_graph.add_edge("extract_qa", "buy_side_focus")
earnings_graph.add_edge("buy_side_focus", END)

# Compile and run
earnings_pipeline = earnings_graph.compile()

# Execute with initial state
initial_state = {
    "future_development": "...",
    "transcript": "...",
    "qa_pairs": None,
    "buy_side_focus": None
}

final_state = earnings_pipeline.invoke(initial_state)
```

**Flow:**
```
START → extract_qa → buy_side_focus → END
```

---

### Pattern 2: Multi-Stage Brain Pipeline

```python
# Create graph
brain_graph = StateGraph(BrainState)

# Add nodes
brain_graph.add_node("extractor", extractor_node)
brain_graph.add_node("reflector", reflect_node)
brain_graph.add_node("alpha", alpha_node)

# Add edges
brain_graph.add_edge(START, "extractor")
brain_graph.add_edge("extractor", "reflector")
brain_graph.add_edge("reflector", "alpha")
brain_graph.add_edge("alpha", END)

# Compile
brain_pipeline = brain_graph.compile()

# Run with initial state
initial_state = {
    "Macro": [],
    "Sector": [],
    "Market": [],
    "Micro": [],
    "inputs_to_process": inputs_list,
    "buy_side_focus": earnings_state["buy_side_focus"],
    "alpha_insights": {},
    "last_updated": str(datetime.now())
}

final_state = brain_pipeline.invoke(initial_state)
```

**Flow:**
```
START → extractor → reflector → alpha → END
```

---

## 🎯 4. Your Three Main Node Types

### Type 1: **Extractor Nodes**
Extract and classify information from raw data.

```python
def extractor_node(state: BrainState) -> BrainState:
    """Process inputs and classify into 4 layers"""
    for input_item in state.get("inputs_to_process", []):
        text = str(input_item.get("text", ""))
        context_name = input_item.get("context_name", "")
        
        if not text.strip():
            continue
        
        # LLM call to classify
        prompt = f"""Classify into Macro/Sector/Market/Micro and extract features.
Return JSON: {{"layer": "Macro", "factor": "...", "features": [...]}}

Context: {context_name}
Text: {text[:1500]}..."""
        
        try:
            result_text = llm_tool(prompt)
            if "```json" in result_text:
                result_text = result_text.split("```json")[-1].split("```")[0].strip()
            result = json.loads(result_text)
            
            layer = result.get("layer")
            if layer in ["Macro", "Sector", "Market", "Micro"]:
                state[layer].append({
                    "factor": result["factor"],
                    "features": result["features"],
                    "context": context_name,
                    "created_at": str(datetime.now())
                })
        except:
            pass
    
    return state
```

**Purpose:** Parse raw inputs → Structured data

---

### Type 2: **Reflector Nodes**
Refine, merge, and optimize extracted data.

```python
def reflect_node(state: BrainState) -> BrainState:
    """Review data, merge duplicates, keep top 16"""
    for layer in ["Macro", "Sector", "Market", "Micro"]:
        if not state.get(layer):
            continue
        
        prompt = f"""Review {layer} data, merge duplicates, keep top 16.
Input: {json.dumps(state[layer], indent=2)}
Output: JSON list (same structure)."""
        
        try:
            result_text = llm_tool(prompt)
            if "```json" in result_text:
                result_text = result_text.split("```json")[-1].split("```")[0].strip()
            refined = json.loads(result_text)
            state[layer] = refined[:16]
        except:
            pass
    
    state["last_updated"] = str(datetime.now())
    return state
```

**Purpose:** Deduplicate → Prioritize → Compress

---

### Type 3: **Alpha Discovery Nodes**
Find hidden insights from processed data.

```python
def alpha_node(state: BrainState) -> BrainState:
    """Find top 3 under-discussed (hidden alpha) features"""
    brain_data = {
        "Macro": state.get("Macro", []),
        "Sector": state.get("Sector", []),
        "Market": state.get("Market", []),
        "Micro": state.get("Micro", [])
    }
    
    prompt = f"""Find top 3 under-discussed (hidden alpha) features.

Brain: {json.dumps(brain_data, indent=2)}
Buy-side focus: {state.get("buy_side_focus", "")}

Return JSON: {{"alpha_insights": [{{"feature": "...", "layer": "...", "reason_alpha": "...", "visibility": "Low", "expected_impact": "High", "confidence": 0.85}}]}}"""
    
    try:
        result_text = llm_tool(prompt)
        if "```json" in result_text:
            result_text = result_text.split("```json")[-1].split("```")[0].strip()
        alpha = json.loads(result_text)
    except:
        alpha = {"alpha_insights": []}
    
    state["alpha_insights"] = alpha
    return state
```

**Purpose:** Synthesize insights → Identify alpha

---

## 🔑 5. Key Patterns from Your Code

### Pattern A: JSON Parsing with Fallback
```python
# Always handle JSON with try-except
if "```json" in text:
    text = text.split("```json")[-1].split("```")[0].strip()

try:
    result = json.loads(text)
except:
    result = {"default": "fallback"}
```

### Pattern B: LLM Helper Function
```python
def llm_tool(prompt: str) -> str:
    response = llm.invoke(prompt)
    return response.content
```

### Pattern C: State Iteration
```python
# Process list of inputs
for input_item in state.get("inputs_to_process", []):
    text = input_item.get("text", "")
    context = input_item.get("context_name", "")
    # ... process each input
```

### Pattern D: Layer-based Organization
```python
# You organize data into 4 layers
for layer in ["Macro", "Sector", "Market", "Micro"]:
    if not state.get(layer):
        continue
    # ... process each layer
```

---

## 📊 6. Complete Example: Building a New Pipeline

Here's how to build a **Firecrawl News Pipeline** following your patterns:

```python
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END

# 1. Define State
class NewsPipelineState(TypedDict):
    company_name: str
    ticker: str
    raw_news: List[Dict[str, str]]
    summarized_news: str
    sentiment: str
    key_events: List[str]

# 2. Define Nodes
def fetch_news_node(state: NewsPipelineState) -> NewsPipelineState:
    """Fetch news using Firecrawl"""
    from firecrawl_utils import search_recent_news
    
    news_result = search_recent_news(
        company_name=state['company_name'],
        ticker=state['ticker'],
        limit=10,
        hours=168  # 7 days
    )
    
    state['raw_news'] = news_result.get('news_list', [])
    return state


def summarize_news_node(state: NewsPipelineState) -> NewsPipelineState:
    """Summarize news with LLM"""
    news_text = "\n".join([
        f"• {news['title']}: {news['snippet']}"
        for news in state['raw_news']
    ])
    
    prompt = f"""Summarize these news articles in 3-4 bullet points:

{news_text}

Return as numbered list."""
    
    summary = llm_tool(prompt)
    state['summarized_news'] = summary
    return state


def analyze_sentiment_node(state: NewsPipelineState) -> NewsPipelineState:
    """Analyze sentiment"""
    prompt = f"""Analyze sentiment from this news summary:

{state['summarized_news']}

Return ONE word: Positive, Negative, or Neutral."""
    
    sentiment = llm_tool(prompt).strip()
    state['sentiment'] = sentiment
    return state


def extract_events_node(state: NewsPipelineState) -> NewsPipelineState:
    """Extract key events"""
    prompt = f"""Extract 3 key events from these news:

{state['summarized_news']}

Return as JSON list: ["event1", "event2", "event3"]"""
    
    result_text = llm_tool(prompt)
    if "```json" in result_text:
        result_text = result_text.split("```json")[-1].split("```")[0].strip()
    
    try:
        events = json.loads(result_text)
    except:
        events = ["Unable to extract events"]
    
    state['key_events'] = events
    return state


# 3. Build Graph
news_graph = StateGraph(NewsPipelineState)

news_graph.add_node("fetch", fetch_news_node)
news_graph.add_node("summarize", summarize_news_node)
news_graph.add_node("sentiment", analyze_sentiment_node)
news_graph.add_node("events", extract_events_node)

news_graph.add_edge(START, "fetch")
news_graph.add_edge("fetch", "summarize")
news_graph.add_edge("summarize", "sentiment")
news_graph.add_edge("sentiment", "events")
news_graph.add_edge("events", END)

news_pipeline = news_graph.compile()

# 4. Run Pipeline
initial_state = {
    "company_name": "Google",
    "ticker": "GOOGL",
    "raw_news": [],
    "summarized_news": "",
    "sentiment": "",
    "key_events": []
}

final_state = news_pipeline.invoke(initial_state)

print(f"Sentiment: {final_state['sentiment']}")
print(f"Summary: {final_state['summarized_news']}")
print(f"Key Events: {final_state['key_events']}")
```

**Flow:**
```
START → fetch → summarize → sentiment → events → END
```

---

## 🎓 7. Best Practices from Your Code

1. **Always use TypedDict** for state definition
2. **Node functions must return state** after modification
3. **Use try-except** for all LLM/JSON parsing
4. **Keep nodes focused** - one responsibility per node
5. **Process lists with iteration** - handle multiple inputs
6. **Use clear naming** - "extract", "reflect", "alpha", etc.
7. **Structure output as JSON** for easy parsing
8. **Add timestamps** - track when data was created/updated

---

## 🚀 8. Ready to Build Your Supervisor Pipeline?

You can apply this pattern to build a **Supervisor + Firecrawl Pipeline**:

```
START → fetch_company_news → analyze_sell_buy → analyze_business_logic → 
        create_sub_queries → END
```

Each node:
- Takes `SupervisorState` as input
- Modifies specific fields
- Returns updated state
- Feeds into next node

Let me know when you want to discuss implementation! 🎯

