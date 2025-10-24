# =============================================================================
# HEDGE FUND ANALYST GRAPH - Cost-Aware Impact Chain Analysis with Sentiment
# =============================================================================

from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, START, END
from langchain_deepseek import ChatDeepSeek
import json
import os

# Setup LLM
os.environ["DEEPSEEK_API_KEY"] = "sk-43e9043c7ab8480393d34367f2ae997e"
analyst_llm = ChatDeepSeek(model="deepseek-chat", temperature=0.3, max_tokens=800)
reflection_llm = ChatDeepSeek(model="deepseek-chat", temperature=0.2, max_tokens=600)

# =============================================================================
# COST CONFIGURATION
# =============================================================================

REFLECT_REWARD = 0.2  # Low reward for reflecting (costly)
NO_REFLECT_REWARD = 0.8  # High reward for not reflecting (efficient)
MAX_REFLECTIONS = 1  # Maximum 1 reflection per news item

# =============================================================================
# STATE DEFINITION
# =============================================================================

class AnalystState(TypedDict):
    brain: Dict[str, Any]  # 4-layer brain (Macro, Sector, Market, Micro)
    alpha: List[Dict[str, Any]]  # Alpha insights
    news_list: List[str]  # List of news/information items
    impact_chains: List[Dict[str, Any]]  # Generated impact chains
    current_news_index: int  # Current news being processed
    reasoning_hint: str  # Deeper reasoning hint from reflection
    continue_thinking: str  # "yes" or "no" - continue iteration?
    think_count: int  # Number of iterations
    current_impact: Dict[str, Any]  # Current impact being processed

# =============================================================================
# NODE FUNCTIONS
# =============================================================================

def analyze_news_impact_node(state: AnalystState) -> AnalystState:
    """
    Analyze news item and generate impact chain
    Uses reasoning_hint if available from previous reflection
    """
    
    brain = state.get("brain", {})
    alpha = state.get("alpha", [])
    news_list = state.get("news_list", [])
    current_index = state.get("current_news_index", 0)
    reasoning_hint = state.get("reasoning_hint", "")
    think_count = state.get("think_count", 0)
    
    # Get current news
    if current_index >= len(news_list):
        state["continue_thinking"] = "no"
        return state
    
    news = news_list[current_index]
    
    # Format brain and alpha as system context
    brain_summary = f"""
BRAIN CONTEXT:
- Macro: {len(brain.get('Macro', []))} factors
- Sector: {len(brain.get('Sector', []))} factors  
- Market: {len(brain.get('Market', []))} factors
- Micro: {len(brain.get('Micro', []))} factors

ALPHA INSIGHTS:
{json.dumps(alpha, indent=2)[:500]}...
"""
    
    # Add reasoning hint if this is a refinement iteration
    hint_context = ""
    if reasoning_hint:
        hint_context = f"\n\nDEEPER REASONING HINT (from reflection):\n{reasoning_hint}\n"
    
    print(f"📊 Analyzing news {current_index + 1}/{len(news_list)} (Think iteration: {think_count})...")
    
    prompt = f"""You are a hedge fund analyst with deep company knowledge.

{brain_summary}
{hint_context}

NEW INFORMATION:
{news}

TASK: Analyze how this news impacts financial statements.

OUTPUT FORMAT (JSON):
{{
    "impact_chain": "News summary → Direct impact → Financial metric",
    "affected_metric": "COGS | Sales | Operating Expenses | Revenue | Gross Margin | etc.",
    "direction": "Increase | Decrease | Neutral",
    "sentiment": "Positive | Negative | Neutral",
    "confidence": 0.85,
    "expectation_reasoning": "10-20 words explaining potential impact"
}}

SENTIMENT RULES (Is this good or bad for the company?):
- Revenue/Sales INCREASE → Positive (more money coming in)
- Revenue/Sales DECREASE → Negative (less money coming in)
- Costs (COGS/Operating Expenses) INCREASE → Negative (spending more)
- Costs (COGS/Operating Expenses) DECREASE → Positive (spending less)
- Gross Margin INCREASE → Positive (better profitability)
- Gross Margin DECREASE → Negative (worse profitability)
- Net Income INCREASE → Positive
- Net Income DECREASE → Negative

EXAMPLE:
{{
    "impact_chain": "Supply chain disruption → Higher input costs → COGS increase",
    "affected_metric": "COGS",
    "direction": "Increase",
    "sentiment": "Negative",
    "confidence": 0.78,
    "expectation_reasoning": "Raw material shortage likely to increase cost by 3-5% in Q2"
}}

Return ONLY valid JSON."""
    
    try:
        response = analyst_llm.invoke(prompt)
        result_text = response.content.strip()
        
        # Parse JSON
        if "```json" in result_text:
            result_text = result_text.split("```json")[-1].split("```")[0].strip()
        
        impact_data = json.loads(result_text)
        
        # Add metadata
        impact_data["news_index"] = current_index + 1
        impact_data["news_snippet"] = news[:100] + "..." if len(news) > 100 else news
        impact_data["think_count"] = think_count
        
        # Store in state (will be passed to reflection)
        state["current_impact"] = impact_data
        
        sentiment_emoji = "✅" if impact_data.get('sentiment') == 'Positive' else "❌" if impact_data.get('sentiment') == 'Negative' else "⚪"
        print(f"   {sentiment_emoji} {impact_data['affected_metric']} | {impact_data['direction']} | {impact_data.get('sentiment', 'Unknown')} (confidence: {impact_data['confidence']})")
        
    except Exception as e:
        print(f"   ❌ Error parsing response: {e}")
        # Fallback
        state["current_impact"] = {
            "news_index": current_index + 1,
            "news_snippet": news[:100] + "..." if len(news) > 100 else news,
            "impact_chain": "Unable to analyze",
            "affected_metric": "Unknown",
            "direction": "Unknown",
            "sentiment": "Neutral",
            "confidence": 0.0,
            "expectation_reasoning": "Error occurred during analysis",
            "think_count": think_count,
            "error": str(e)
        }
    
    return state


def reflection_node(state: AnalystState) -> AnalystState:
    """
    Cost-aware reflection: Prefer NOT to reflect (reward 0.8) unless critical issues found
    Max 1 reflection per news item
    """
    
    current_impact = state.get("current_impact", {})
    think_count = state.get("think_count", 0)
    brain = state.get("brain", {})
    confidence = current_impact.get("confidence", 0.0)
    
    print(f"🤔 Cost-aware reflection (iteration {think_count}, confidence: {confidence})...")
    
    # Enforce MAX 1 reflection
    if think_count >= MAX_REFLECTIONS:
        print(f"   ⏭️  Max reflections reached ({MAX_REFLECTIONS}), moving on (reward: {NO_REFLECT_REWARD})")
        state["continue_thinking"] = "no"
        state["reasoning_hint"] = f"Max {MAX_REFLECTIONS} reflection reached"
        
        # Finalize current impact
        if current_impact and "news_index" in current_impact:
            impact_chains = state.get("impact_chains", [])
            impact_chains.append(current_impact)
            state["impact_chains"] = impact_chains
        
        # Move to next news
        state["current_news_index"] = state.get("current_news_index", 0) + 1
        state["think_count"] = 0
        state["reasoning_hint"] = ""
        state["current_impact"] = {}
        return state
    
    # Cost-aware decision prompt
    prompt = f"""You are a COST-AWARE analyst. Reflection is EXPENSIVE (reward: {REFLECT_REWARD}), not reflecting is EFFICIENT (reward: {NO_REFLECT_REWARD}).

CURRENT ANALYSIS:
{json.dumps(current_impact, indent=2)}

COST-AWARE DECISION RULES:
1. If confidence >= 0.75 → DO NOT REFLECT (reward: {NO_REFLECT_REWARD})
2. If reasoning is specific and actionable → DO NOT REFLECT (reward: {NO_REFLECT_REWARD})
3. If impact_chain has clear causality → DO NOT REFLECT (reward: {NO_REFLECT_REWARD})
4. ONLY reflect if critical flaw detected (reward: {REFLECT_REWARD})

CRITICAL FLAWS (worth reflecting):
- Confidence < 0.6 AND reasoning too vague
- Impact chain has logical gaps
- Affected metric doesn't match reasoning
- Sentiment doesn't match direction/metric logic

OUTPUT FORMAT (JSON):
{{
    "reasoning_hint": "Specific guidance if reflecting, or empty if not",
    "continue": "yes | no",
    "expected_reward": {REFLECT_REWARD} or {NO_REFLECT_REWARD}
}}

BIAS: Prefer "continue": "no" (reward {NO_REFLECT_REWARD}) unless absolutely necessary.

Return ONLY valid JSON."""
    
    try:
        response = reflection_llm.invoke(prompt)
        result_text = response.content.strip()
        
        if "```json" in result_text:
            result_text = result_text.split("```json")[-1].split("```")[0].strip()
        
        reflection = json.loads(result_text)
        
        reasoning_hint = reflection.get("reasoning_hint", "")
        continue_decision = reflection.get("continue", "no").lower()
        expected_reward = reflection.get("expected_reward", NO_REFLECT_REWARD)
        
        state["reasoning_hint"] = reasoning_hint
        state["continue_thinking"] = continue_decision
        
        if continue_decision == "yes":
            print(f"   💰 Reflecting (reward: {REFLECT_REWARD}, cost justified)")
            print(f"   🔄 Hint: {reasoning_hint}")
            state["think_count"] = think_count + 1
        else:
            print(f"   💰 NOT reflecting (reward: {NO_REFLECT_REWARD}, efficient choice)")
            
            # Finalize current impact
            if current_impact and "news_index" in current_impact:
                impact_chains = state.get("impact_chains", [])
                impact_chains.append(current_impact)
                state["impact_chains"] = impact_chains
                print(f"   ✅ Impact chain finalized")
            
            # Move to next news
            state["current_news_index"] = state.get("current_news_index", 0) + 1
            state["think_count"] = 0
            state["reasoning_hint"] = ""
            state["current_impact"] = {}
        
    except Exception as e:
        print(f"   ❌ Reflection error: {e}, defaulting to NO REFLECT (reward: {NO_REFLECT_REWARD})")
        
        state["continue_thinking"] = "no"
        state["reasoning_hint"] = "Error in reflection"
        
        if current_impact and "news_index" in current_impact:
            impact_chains = state.get("impact_chains", [])
            impact_chains.append(current_impact)
            state["impact_chains"] = impact_chains
        
        state["current_news_index"] = state.get("current_news_index", 0) + 1
        state["think_count"] = 0
        state["current_impact"] = {}
    
    return state


def should_continue_thinking(state: AnalystState) -> str:
    """Routing function: decide next node based on continue_thinking"""
    if state.get("continue_thinking") == "yes":
        return "analyze_impact"  # Loop back to analysis
    else:
        # Check if there are more news to process
        current_index = state.get("current_news_index", 0)
        news_list = state.get("news_list", [])
        if current_index < len(news_list):
            return "analyze_impact"  # Process next news
        else:
            return "end"  # All done

# =============================================================================
# BUILD GRAPH
# =============================================================================

def build_analyst_graph():
    """Build the cost-aware hedge fund analyst graph"""
    graph = StateGraph(AnalystState)
    
    # Add nodes
    graph.add_node("analyze_impact", analyze_news_impact_node)
    graph.add_node("reflection", reflection_node)
    
    # Add edges
    graph.add_edge(START, "analyze_impact")
    graph.add_edge("analyze_impact", "reflection")
    
    # Conditional edge: reflection → analyze_impact (if continue="yes") OR end
    graph.add_conditional_edges(
        "reflection",
        should_continue_thinking,
        {
            "analyze_impact": "analyze_impact",
            "end": END
        }
    )
    
    # Compile
    pipeline = graph.compile()
    return pipeline

# =============================================================================
# USAGE FUNCTION
# =============================================================================

def analyze_news_impact(brain: Dict, alpha: List, news_list: List[str]) -> List[Dict[str, Any]]:
    """
    Cost-aware analysis of news impact on financial statements
    
    Args:
        brain: 4-layer brain dict (Macro, Sector, Market, Micro)
        alpha: List of alpha insights
        news_list: List of news/information strings
    
    Returns:
        List of impact chain dicts with:
        - impact_chain: str (News → Impact → Financial Metric)
        - affected_metric: str (COGS, Sales, etc.)
        - direction: str (Increase, Decrease, Neutral)
        - sentiment: str (Positive, Negative, Neutral) - Is this good or bad for company?
        - confidence: float (0-1)
        - expectation_reasoning: str (10-20 words)
        - think_count: int (number of reflection iterations, max 1)
    
    Cost Model:
        - Reflect: Reward = 0.2 (expensive, only if necessary)
        - No Reflect: Reward = 0.8 (efficient, preferred)
        - Max Reflections: 1 per news item
    """
    
    print(f"🚀 Starting COST-AWARE hedge fund analyst pipeline...")
    print(f"   💰 Reflection reward: {REFLECT_REWARD} (discouraged)")
    print(f"   💰 No-reflection reward: {NO_REFLECT_REWARD} (preferred)")
    print(f"   🔄 Max reflections: {MAX_REFLECTIONS} per news")
    print(f"   📰 News items: {len(news_list)}")
    print(f"   🧠 Brain layers: {', '.join(brain.keys())}")
    print(f"   💡 Alpha insights: {len(alpha)}\n")
    
    # Build graph
    pipeline = build_analyst_graph()
    
    # Initial state
    initial_state = {
        "brain": brain,
        "alpha": alpha,
        "news_list": news_list,
        "impact_chains": [],
        "current_news_index": 0,
        "reasoning_hint": "",
        "continue_thinking": "yes",
        "think_count": 0,
        "current_impact": {}
    }
    
    # Run pipeline
    final_state = pipeline.invoke(initial_state)
    
    # Calculate total reward
    total_reflections = sum(chain.get("think_count", 0) for chain in final_state["impact_chains"])
    total_no_reflections = len(final_state["impact_chains"]) - total_reflections
    total_reward = (total_reflections * REFLECT_REWARD) + (total_no_reflections * NO_REFLECT_REWARD)
    
    # Count sentiment distribution
    positive_count = sum(1 for chain in final_state["impact_chains"] if chain.get("sentiment") == "Positive")
    negative_count = sum(1 for chain in final_state["impact_chains"] if chain.get("sentiment") == "Negative")
    neutral_count = len(final_state["impact_chains"]) - positive_count - negative_count
    
    print(f"\n✅ Analysis complete!")
    print(f"   📊 Generated {len(final_state['impact_chains'])} impact chains")
    print(f"   ✅ Positive impacts: {positive_count}")
    print(f"   ❌ Negative impacts: {negative_count}")
    print(f"   ⚪ Neutral impacts: {neutral_count}")
    print(f"   🔄 Total reflections: {total_reflections}")
    print(f"   ⚡ No reflections: {total_no_reflections}")
    print(f"   💰 Total reward: {total_reward:.2f}")
    
    return final_state["impact_chains"]

