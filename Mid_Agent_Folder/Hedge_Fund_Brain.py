#!/usr/bin/env python3
"""
Hedge Fund Brain - Simple Interface

Usage:
    from Mid_Agent_Folder.Hedge_Fund_Brain import hedgefundbrain
    
    brain, alpha = await hedgefundbrain("TGT")

Auto-updates: Checks Redis, if data > 7 days old, runs fresh analysis.
"""

import sys
import os
from pathlib import Path

# Add paths
current_dir = Path(__file__).parent.absolute()
parent_dir = current_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

import json
import asyncio
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Any, TypedDict, Optional, Tuple

# LangChain & LangGraph
from langchain_deepseek import ChatDeepSeek
from langgraph.graph import StateGraph, START, END

# Custom imports
from update_pool import update_pool
from Data_Retrieval import (
    get_earnings_data,
    get_sector_data,
    get_financial_metrics_data,
    get_market_expectation_data,
    get_macro_data,
    get_revenue_segmentation_data
)

# ==============================================================
# LLM Setup
# ==============================================================

os.environ["DEEPSEEK_API_KEY"] = "sk-43e9043c7ab8480393d34367f2ae997e"

llm = ChatDeepSeek(model="deepseek-chat", temperature=0.3, max_tokens=4000)

def llm_tool(prompt: str) -> str:
    response = llm.invoke(prompt)
    return response.content

# ==============================================================
# State Definitions
# ==============================================================

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

# ==============================================================
# Pipeline Nodes
# ==============================================================

def extract_qa_pairs(state: EarningsPipelineState) -> EarningsPipelineState:
    extractor_llm = ChatDeepSeek(model="deepseek-chat", temperature=0.5, max_tokens=2000)
    prompt = f"""Extract 2-5 Q&A pairs from this earnings transcript.
Return ONLY valid JSON: {{"Q1": "...", "A1": "...", "Q2": "...", "A2": "..."}}

Transcript: {state['transcript'][:3000]}..."""
    
    response = extractor_llm.invoke(prompt)
    text = response.content.strip()
    if "```json" in text:
        text = text.split("```json")[-1].split("```")[0].strip()
    
    try:
        qa_json = json.loads(text)
    except:
        qa_json = {"Q1": "Parse error", "A1": "Unable to extract"}
    
    state["qa_pairs"] = qa_json
    return state


def generate_buy_side_focus(state: EarningsPipelineState) -> EarningsPipelineState:
    analyst_llm = ChatDeepSeek(model="deepseek-chat", temperature=0.5, max_tokens=800)
    prompt = f"""Analyze company strategy and identify top 3 priorities (revenue growth, sales improvement, execution).

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


def extractor_node(state: BrainState) -> BrainState:
    for input_item in state.get("inputs_to_process", []):
        text = str(input_item.get("text", ""))
        context_name = input_item.get("context_name", "")
        
        if not text.strip():
            continue
        
        prompt = f"""Classify into Macro/Sector/Market/Micro and extract features.
Return JSON: {{"layer": "Macro", "factor": "...", "features": [{{"statement": "...", "evidence": "...", "confidence": 0.85}}]}}

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


def reflect_node(state: BrainState) -> BrainState:
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


def alpha_node(state: BrainState) -> BrainState:
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

# ==============================================================
# Redis Functions
# ==============================================================

def get_redis_client():
    return redis.Redis(
        host="redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
        port=16376,
        username="default",
        password="rl8242B4UItBhFzgHW5APEqZnkYoaEZv",
        decode_responses=True
    )


async def check_freshness(ticker: str) -> bool:
    """Check if brain data is fresh (< 7 days)"""
    try:
        redis_client = get_redis_client()
        brain_key = f"Hedge_Fund_Brain:{ticker.upper()}:brain"
        
        brain_data = redis_client.get(brain_key)
        if not brain_data:
            return False
        
        brain = json.loads(brain_data)
        stored_at = brain.get("stored_at")
        
        if not stored_at:
            return False
        
        stored_datetime = datetime.fromisoformat(stored_at)
        age_days = (datetime.now() - stored_datetime).days
        
        return age_days < 7
        
    except:
        return False


async def retrieve_from_redis(ticker: str) -> Tuple[Dict, List]:
    """Retrieve brain and alpha from Redis"""
    try:
        redis_client = get_redis_client()
        
        brain_key = f"Hedge_Fund_Brain:{ticker.upper()}:brain"
        alpha_key = f"Hedge_Fund_Brain:{ticker.upper()}:alpha"
        
        brain_data = redis_client.get(brain_key)
        alpha_data = redis_client.get(alpha_key)
        
        if brain_data and alpha_data:
            brain = json.loads(brain_data)["brain"]
            alpha = json.loads(alpha_data)["alpha_insights"]
            return brain, alpha
        else:
            return None, None
            
    except:
        return None, None


async def store_to_redis(ticker: str, brain: Dict, alpha: List):
    """Store brain and alpha to Redis"""
    try:
        redis_client = get_redis_client()
        
        brain_key = f"Hedge_Fund_Brain:{ticker.upper()}:brain"
        brain_package = {
            "ticker": ticker.upper(),
            "brain": brain,
            "stored_at": datetime.now().isoformat(),
            "total_factors": sum(len(brain.get(l, [])) for l in ["Macro", "Sector", "Market", "Micro"])
        }
        redis_client.set(brain_key, json.dumps(brain_package))
        
        alpha_key = f"Hedge_Fund_Brain:{ticker.upper()}:alpha"
        alpha_package = {
            "ticker": ticker.upper(),
            "alpha_insights": alpha,
            "stored_at": datetime.now().isoformat(),
            "insight_count": len(alpha)
        }
        redis_client.set(alpha_key, json.dumps(alpha_package))
        
    except Exception as e:
        print(f"⚠️ Redis storage failed: {e}")


async def generate_new_brain(ticker: str) -> Tuple[Dict, List]:
    """Generate fresh brain and alpha analysis"""
    
    # Update all agents
    await update_pool(ticker, [
        "Market_Expectation_Agent",
        "Sector_Analyst_Agent",
        "Financial_Metrics_Agent",
        "Macro_Analyst_Agent",
        "Earning_and_Future_Agent",
        "Fundamental_Segmentation_Agent"
    ])
    
    # Retrieve all data
    sector_result = await get_sector_data(ticker)
    earnings_result = await get_earnings_data(ticker)
    macro_result = await get_macro_data()
    revenue_result = await get_revenue_segmentation_data(ticker)
    
    # Extract Q&A and buy-side focus
    earnings_graph = StateGraph(EarningsPipelineState)
    earnings_graph.add_node("extract_qa", extract_qa_pairs)
    earnings_graph.add_node("buy_side_focus", generate_buy_side_focus)
    earnings_graph.add_edge(START, "extract_qa")
    earnings_graph.add_edge("extract_qa", "buy_side_focus")
    earnings_graph.add_edge("buy_side_focus", END)
    earnings_pipeline = earnings_graph.compile()
    
    earnings_state = earnings_pipeline.invoke({
        "future_development": earnings_result.future_development,
        "transcript": earnings_result.transcript,
        "qa_pairs": None,
        "buy_side_focus": None
    })
    
    # Build brain
    inputs_list = [
        {"text": str(macro_result.analysis), "context_name": "Macro environment"},
        {"text": sector_result.get_answer("sector_trend"), "context_name": "Industry trend"},
        {"text": sector_result.get_answer("company_competitor_landscape"), "context_name": "Competitive landscape"},
        {"text": sector_result.competitor_summary, "context_name": "Competitor summary"},
        {"text": earnings_result.future_development, "context_name": "Company future plan"},
        {"text": str(revenue_result.business_segments), "context_name": "Revenue breakdown"},
        {"text": str(revenue_result.cost_segments), "context_name": "Cost structure"},
        {"text": str(revenue_result.supplier_segments), "context_name": "Supplier analysis"},
    ]
    
    brain_graph = StateGraph(BrainState)
    brain_graph.add_node("extractor", extractor_node)
    brain_graph.add_node("reflector", reflect_node)
    brain_graph.add_node("alpha", alpha_node)
    brain_graph.add_edge(START, "extractor")
    brain_graph.add_edge("extractor", "reflector")
    brain_graph.add_edge("reflector", "alpha")
    brain_graph.add_edge("alpha", END)
    brain_pipeline = brain_graph.compile()
    
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
    
    brain = {
        "Macro": final_state["Macro"],
        "Sector": final_state["Sector"],
        "Market": final_state["Market"],
        "Micro": final_state["Micro"]
    }
    alpha = final_state["alpha_insights"].get("alpha_insights", [])
    
    # Store to Redis
    await store_to_redis(ticker, brain, alpha)
    
    return brain, alpha


# ==============================================================
# Main Function - Simple Interface
# ==============================================================

async def hedgefundbrain(ticker: str) -> Tuple[Dict, List]:
    """
    Get brain and alpha for a ticker.
    
    Logic:
    - If Redis data < 7 days old → return cached data
    - If Redis data > 7 days old OR missing → generate new
    
    Args:
        ticker (str): Stock ticker symbol
        
    Returns:
        Tuple[Dict, List]: (brain, alpha_insights)
        
    Example:
        brain, alpha = await hedgefundbrain("TGT")
        
        # Access brain
        print(brain["Macro"])  # Macro factors
        print(brain["Sector"]) # Sector factors
        print(brain["Market"]) # Market factors
        print(brain["Micro"])  # Micro factors
        
        # Access alpha
        for insight in alpha:
            print(insight["feature"])
    """
    
    # Check if data is fresh
    is_fresh = await check_freshness(ticker)
    
    if is_fresh:
        # Data < 7 days old, retrieve from Redis
        print(f"✅ Fresh data found for {ticker} (< 7 days old)")
        brain, alpha = await retrieve_from_redis(ticker)
        
        if brain and alpha:
            print(f"   Retrieved from Redis: {sum(len(brain[l]) for l in ['Macro', 'Sector', 'Market', 'Micro'])} factors, {len(alpha)} insights")
            return brain, alpha
    
    # Data is stale or missing, generate new
    print(f"🔄 Generating fresh analysis for {ticker}...")
    brain, alpha = await generate_new_brain(ticker)
    print(f"✅ Generated: {sum(len(brain[l]) for l in ['Macro', 'Sector', 'Market', 'Micro'])} factors, {len(alpha)} insights")
    
    return brain, alpha


# ==============================================================
# Main Entry
# ==============================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Hedge Fund Brain')
    parser.add_argument('ticker', help='Stock ticker (e.g., TGT)')
    args = parser.parse_args()
    
    brain, alpha = await hedgefundbrain(args.ticker)
    
    print("\n🧠 BRAIN SUMMARY:")
    print(f"  Macro: {len(brain['Macro'])} factors")
    print(f"  Sector: {len(brain['Sector'])} factors")
    print(f"  Market: {len(brain['Market'])} factors")
    print(f"  Micro: {len(brain['Micro'])} factors")
    
    print("\n💡 ALPHA INSIGHTS:")
    for i, insight in enumerate(alpha, 1):
        print(f"  {i}. {insight.get('feature', 'N/A')}")


if __name__ == "__main__":
    asyncio.run(main())
