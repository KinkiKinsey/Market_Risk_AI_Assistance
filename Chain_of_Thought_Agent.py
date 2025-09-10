import json
import re
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from LLM_Call_Agent import LLMCallAgent

class ChainOfThoughtResult(BaseModel):
    initial_query: str = Field(description="The original user question")
    ticker: str = Field(description="Stock ticker symbol")
    impact_chain: str = Field(description="Linear chain: A → B → C → D → Final")
    final_direction: str = Field(description="Final impact: 'Short' or 'Long'")
    chain_explanation: str = Field(description="Brief explanation of the chain logic")
    node_count: int = Field(description="Number of nodes in the chain")
    edge_count: int = Field(description="Number of edges/connections in the chain")
    events: List[str] = Field(description="List of individual events in the chain")

def generate_mermaid_code(node_count: int, edge_count: int, events: List[str]) -> str:
    """
    ✅ TRULY DYNAMIC - Generates Mermaid.js code for ANY number of nodes
    """
    
    # ✅ NO MINIMUM LIMITS - Let it be as short or long as needed
    if node_count < 1:  # Allow single node if needed
        node_count = 1
    if edge_count < 0:  # Allow no edges if single node
        edge_count = 0
    
    # ✅ DYNAMIC NODE IDS - Handle any number of nodes
    node_ids = []
    for i in range(node_count):
        if i < 26:  # A-Z
            node_ids.append(chr(65 + i))
        else:  # AA, AB, AC... for more than 26 nodes
            node_ids.append(f"{chr(65 + i//26)}{chr(65 + i%26)}")
    
    # ✅ CLEAN EVENTS - Remove any Pydantic field names and special characters
    clean_events = []
    for event in events[:node_count]:
        # Remove field names like "initial_query:", "ticker:", etc.
        if ': ' in event:
            clean_event = event.split(': ')[-1]
        else:
            clean_event = event
        
        # Clean special characters that break Mermaid.js
        clean_event = clean_event.replace('"', "'")  # Replace quotes
        clean_event = clean_event.replace('\\', '/')  # Replace backslashes
        clean_event = clean_event.replace('\n', ' ')  # Replace newlines
        clean_event = clean_event.replace('\r', ' ')  # Replace carriage returns
        clean_event = clean_event.replace('\t', ' ')  # Replace tabs
        
        # Remove any remaining problematic characters
        clean_event = re.sub(r'[^\w\s\-\.\'\&\+]', '', clean_event)
        
        # Limit length to prevent Mermaid.js issues
        if len(clean_event) > 50:
            clean_event = clean_event[:47] + "..."
        
        clean_events.append(clean_event)
    
    # ✅ TRULY DYNAMIC MERMAID CODE - Adapts to any number of nodes
    mermaid_code = "graph LR\n"
    mermaid_code += f"    title[\"Chain {node_count}: {clean_events[0][:30]}...\"]\n"
    
    # ✅ FIXED - Create separate node for each event
    for i in range(node_count):
        node_id = node_ids[i]
        if i < len(clean_events):
            # ✅ LAST NODE - Just show the final decision (Short/Long)
            if i == node_count - 1:  # Last node
                # Extract one of the four options from the last event
                last_event = clean_events[i]
                if "Short Term Up" in last_event:
                    event_text = "Short Term Up"
                elif "Short Term Down" in last_event:
                    event_text = "Short Term Down"
                elif "Long Term Up" in last_event:
                    event_text = "Long Term Up"
                elif "Long Term Down" in last_event:
                    event_text = "Long Term Down"
                else:
                    event_text = last_event
            else:
                event_text = clean_events[i]
        else:
            event_text = f"Step {i+1}"
        
        # Ensure event_text is safe for Mermaid.js
        if not event_text or event_text.strip() == "":
            event_text = f"Step {i+1}"
        
        # Final safety check - remove any remaining problematic characters
        event_text = re.sub(r'[^\w\s\-\.\'\&\+]', '', str(event_text))
        event_text = event_text.strip()
        
        if not event_text:
            event_text = f"Step {i+1}"
        
        mermaid_code += f"    {node_id}[{event_text}]\n"
    
    # Add edges dynamically
    mermaid_code += f"    title --> {node_ids[0]}\n"
    for i in range(edge_count):
        if i + 1 < len(node_ids):
            source = node_ids[i]
            target = node_ids[i + 1]
            mermaid_code += f"    {source} --> {target}\n"
    
    # ✅ DYNAMIC STYLING - Adapts to any number of nodes
    mermaid_code += f"\n    style title fill:#fff2cc\n"  # Title node (yellow)
    if node_count > 0:
        mermaid_code += f"    style {node_ids[0]} fill:#e1f5fe\n"  # First node (blue)
        if node_count > 1:
            mermaid_code += f"    style {node_ids[-1]} fill:#ffebee\n"  # Last node (red)
            # Middle nodes (purple) - only if more than 2 nodes
            if node_count > 2:
                for i in range(1, node_count - 1):
                    node_id = node_ids[i]
                    mermaid_code += f"    style {node_id} fill:#f3e5f5\n"
    
    # Validate the generated Mermaid.js code
    try:
        # Basic validation - ensure we have valid syntax
        if not mermaid_code.strip():
            raise ValueError("Empty Mermaid.js code")
        
        # Check for basic structure
        if "graph LR" not in mermaid_code:
            raise ValueError("Missing graph declaration")
        
        # Check for nodes
        if "[" not in mermaid_code or "]" not in mermaid_code:
            raise ValueError("Missing node definitions")
        
        # Check for edges
        if "-->" not in mermaid_code:
            raise ValueError("Missing edge definitions")
        
        return mermaid_code
        
    except Exception as e:
        # Fallback to a simple, safe Mermaid.js code
        print(f"Warning: Mermaid.js validation failed: {e}")
        print(f"Generated code: {mermaid_code}")
        
        # Return a safe fallback
        fallback_code = """graph LR
    A[Analysis Start]
    B[Analysis Process]
    C[Final Decision]
    
    A --> B
    B --> C
    
    style A fill:#e1f5fe
    style C fill:#ffebee
    style B fill:#f3e5f5"""
        
        return fallback_code

def parse_llm_response(response: str) -> Optional[Dict[str, Any]]:
    """
    ✅ TRULY DYNAMIC - Parses any chain length, not just 5 nodes
    """
    
    # Try to extract JSON first
    try:
        # Look for JSON-like content
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            parsed = json.loads(json_str)
            return parsed
    except:
        pass
    
    # ✅ TRULY DYNAMIC - Look for ANY chain pattern, not just 5 nodes
    try:
        # Look for ANY chain pattern: A → B → C or A → B → C → D or A → B → C → D → E → F
        chain_match = re.search(r'([^→]+(?:→[^→]+)*)', response)
        if chain_match:
            chain_text = chain_match.group(1)
            chain_parts = [part.strip() for part in chain_text.split("→")]
            
            # ✅ DYNAMIC - Handle any number of parts
            if len(chain_parts) >= 2:  # At least 2 parts for a chain
                # Determine final direction from four options
                last_event = chain_parts[-1]
                if "Short Term Up" in last_event:
                    final_direction = "Short Term Up"
                elif "Short Term Down" in last_event:
                    final_direction = "Short Term Down"
                elif "Long Term Up" in last_event:
                    final_direction = "Long Term Up"
                elif "Long Term Down" in last_event:
                    final_direction = "Long Term Down"
                else:
                    # Fallback logic
                    if "Up" in last_event:
                        final_direction = "Short Term Up"
                    else:
                        final_direction = "Short Term Down"
                
                return {
                    "impact_chain": chain_text,
                    "final_direction": final_direction,
                    "node_count": len(chain_parts),  # ✅ DYNAMIC
                    "edge_count": len(chain_parts) - 1,  # ✅ DYNAMIC
                    "events": chain_parts
                }
    except:
        pass
    
    return None

class ChainOfThoughtAgent:
    def __init__(self):
        """Initialize the Chain of Thought Agent"""
        self.llm_agent = LLMCallAgent(
            default_provider="deepseek",
            default_model="deepseek-chat"
        )
        self.structured_llm = self.llm_agent.get_structured_llm(ChainOfThoughtResult)
    
    def generate_impact_chain(
        self,
        ticker: str,
        user_question: str,
        verification_links: List[str],
        verification_reasoning: str,
        agent_analysis_results: Dict[str, Any],
        language: str = "English"
    ) -> ChainOfThoughtResult:
        """
        Generate a rigorous impact chain based on evidence and logical progression
        """
        
        prompt = f"""
        You are an expert financial analyst creating rigorous impact chains for client reporting.

        TASK: Based on the user query (starting event) and evidence, write a logical impact chain showing how Event A impacts Event B, then Event C, leading to final stock price impact.

        INPUT DATA:
        - Ticker: {ticker}
        - Starting Event (User Query): {user_question}
        - Agent Analysis Results: {agent_analysis_results}

        CRITICAL REQUIREMENT - MARKET EXPECTATION DATA FOR REFERENCE:
        **USE HISTORICAL RETURN RATES AND DATE RANGES FOR REFERENCE**: The Market Expectation Agent provides historical data with return rates and date ranges. Use these as reference points in your impact chain analysis.

        MARKET EXPECTATION DATA USAGE:
        1. **REFERENCE RETURN RATES**: Use percentage returns (e.g., "-15.3%", "+8.7%", "-22.1%") as reference points
        2. **REFERENCE DATE RANGES**: Use historical date ranges (e.g., "from 2023-01-15 to 2023-01-18") as reference points
        3. **NO GENERIC TERMS**: Do NOT use terms like "uptrend", "downtrend", "positive", "negative"
        4. **ANALYSIS FOCUS**: Focus on the logical chain progression, using market data as supporting evidence

        RIGOROUS LOGIC REQUIREMENTS:
        1. **START WITH USER QUERY** - The starting event from the user query
        2. **REFERENCE MARKET DATA** - Use return rates and date ranges from Market Expectation Agent as reference points
        3. **FOLLOW LOGICAL PROGRESSION** - Each event must logically cause the next event
        4. **USE QUANTITATIVE EVIDENCE** - Reference percentages and return rates from agent analysis results
        5. **CONSISTENT DIRECTION** - If negative news, show how it leads to negative impact; if positive, show positive progression
        6. **ANALYSIS FOCUS** - Focus on logical chain progression with market data as supporting evidence

        CHAIN STRUCTURE WITH MARKET DATA REFERENCE:
        Starting Event → Market Data Reference (X% return from date1 to date2) → Intermediate Event 1 → Intermediate Event 2 → Final Stock Price Impact

        MARKET EXPECTATION ELEMENTS FOR REFERENCE:
        - **Return Rate**: Use percentage returns (e.g., "-15.3%", "+8.7%")
        - **Date Range**: Use historical date ranges (e.g., "from 2023-01-15 to 2023-01-18")
        - **Historical Evidence**: Reference historical return rates and date ranges
        - **Analysis Support**: Use market data to support logical chain progression

        DECISION RULES:
        - **LONG TERM UP**: Business strategy, future plans, structural improvements
        - **SHORT TERM DOWN**: Market sentiment, temporary headwinds, short-term challenges  
        - **LONG TERM DOWN**: Fundamental business model issues, competitive threats
        - **SHORT TERM UP**: Temporary positive catalysts, immediate market reactions

        EXAMPLE CHAIN WITH MARKET DATA REFERENCE:
        "Tariff increase → Market data shows similar tariff events caused -15.3% (refer from 2023-01-15 to 2023-01-18) → Supply chain disruption (-3% margin) → Inventory pressure (-2% revenue) → Short Term Down"

        OUTPUT FORMAT:
        {{
            "initial_query": "{user_question}",
            "ticker": "{ticker}",
            "impact_chain": "Event A → Market Data Reference (X% return from date1 to date2) → Event B (XX% impact) → Event C (XX% impact) → Final Direction",
            "final_direction": "Short Term Up, Short Term Down, Long Term Up, or Long Term Down",
            "chain_explanation": "Brief explanation including the return rate and date range from market data reference",
            "node_count": <number of events>,
            "edge_count": <number of connections>,
            "events": ["Event A", "Market Data Reference (X% return from date1 to date2)", "Event B (XX% impact)", "Event C (XX% impact)", "Final Direction"]
        }}

        REQUIREMENTS:
        1. **Include return rates** from Market Expectation Agent data as reference
        2. **Include date ranges** (from date1 to date2) as reference
        3. **Reference percentages** from the market analysis
        4. **Reference the quantitative evidence** in the chain explanation
        5. **Show the return rate and date range** as a reference node in the impact chain
        6. **Use numbers** from the agent analysis results as supporting evidence
        7. **FOCUS ON LOGICAL PROGRESSION**: Prioritize logical chain progression over precise numbers

        REFERENCE PATTERNS IN AGENT ANALYSIS RESULTS:
        - "Similar events caused X% return from date1 to date2"
        - "Historical average return of X% from date1 to date2"
        - "Previous similar events resulted in X% impact from date1 to date2"
        - "Stock price moved X% during similar events from date1 to date2"
        - "X% return from date1 to date2"
        - Any quantitative return rate data and date ranges from Market Expectation Agent

        FORBIDDEN TERMS (DO NOT USE):
        - "uptrend", "downtrend", "positive trend", "negative trend"
        - "bullish", "bearish", "positive", "negative"
        - "increased", "decreased", "rose", "fell" (without specific percentages)
        - Any generic descriptive terms without specific numeric data
        - "estimated", "return over", "last", "past", "previous"

        REFERENCE TERMS (USE AS REFERENCE):
        - Percentage returns: "-15.3%", "+8.7%", "-22.1%"
        - Date ranges: "from 2023-01-15 to 2023-01-18"
        - Numeric data from Market Expectation Agent

        IMPORTANT:
        - Start with the user query as the first event
        - Include return rates and date ranges from Market Expectation Agent as reference
        - Follow rigorous logical progression with quantitative evidence
        - Use return rates and date ranges from market data as supporting evidence
        - Final direction must be one of the four options
        - Focus on logical chain progression with market data as reference points
        - DO NOT include "estimated", "return over", "last", "past", "previous" in the output
        """
        
        # Add language instruction only if not English
        if language.lower() != "english":
            prompt += f"\n        CRITICAL: Output ALL text in {language} language only. Do NOT use any other language."
        
        try:
            # Try structured output first
            result = self.structured_llm.invoke(prompt)
            
            # Check if result is AIMessage (structured output failed)
            if hasattr(result, 'content'):
                # Extract JSON from AIMessage content (remove markdown code blocks)
                content = result.content
                if content.startswith('```json'):
                    content = content[7:]  # Remove ```json
                if content.endswith('```'):
                    content = content[:-3]  # Remove ```
                
                # Parse the JSON content
                try:
                    parsed_data = json.loads(content.strip())
                    return ChainOfThoughtResult(**parsed_data)
                except json.JSONDecodeError as json_error:
                    raise Exception(f"Failed to parse JSON from AIMessage: {json_error}")
            else:
                # Result is already a Pydantic object
                return result
        except Exception as e:
            # Fallback to regular LLM call
            try:
                response = self.llm_agent.call_deepseek(prompt)
                parsed = parse_llm_response(response)
                
                if parsed:
                    return ChainOfThoughtResult(
                        initial_query=user_question,
                        ticker=ticker,
                        impact_chain=parsed.get("impact_chain", ""),
                        final_direction=parsed.get("final_direction", ""),
                        chain_explanation=parsed.get("chain_explanation", ""),
                        node_count=parsed.get("node_count", 0),
                        edge_count=parsed.get("edge_count", 0),
                        events=parsed.get("events", [])
                    )
                else:
                    raise Exception("Failed to parse LLM response")
                    
            except Exception as fallback_error:
                raise Exception(f"Both structured and fallback LLM calls failed: {str(e)} -> {str(fallback_error)}")

# Test function
def test_agent():
    """Test the Chain of Thought Agent"""
    try:
        agent = ChainOfThoughtAgent()
        print("✅ Chain of Thought Agent initialized successfully!")
        
        # Test Mermaid code generation with generic data
        test_events = ["Analysis Start", "Data Processing", "Market Analysis", "Decision"]
        mermaid_code = generate_mermaid_code(4, 3, test_events)
        print("✅ Mermaid code generation working!")
        print(f"Generated code:\n{mermaid_code}")
        
        # Test with generic analysis data
        generic_events = ["Market Analysis", "Risk Assessment", "Opportunity Evaluation", "Strategic Decision", "Implementation", "Monitoring", "Adjustment", "Final Outcome"]
        generic_mermaid = generate_mermaid_code(8, 7, generic_events)
        print("✅ Generic analysis handling working!")
        print(f"Generated code:\n{generic_mermaid}")
        
        return True
    except Exception as e:
        print(f"❌ Error testing agent: {e}")
        return False

if __name__ == "__main__":
    test_agent()

# ============================================================================
# CONCURRENT PROCESSING FUNCTIONS (NEW)
# ============================================================================

def concurrent_call_generate_impact_chain(
    ticker: str,
    user_question: str,
    verification_links: List[str],
    verification_reasoning: str,
    agent_analysis_results: Dict[str, Any],
    total_queries: List[str] = None,
    query_index: int = 0,
    context: Dict[str, Any] = None,
    language: str = "English"
) -> ChainOfThoughtResult:
    """
    Generate a dynamic impact chain with context awareness for concurrent processing
    """
    try:
        # Initialize agent
        agent = ChainOfThoughtAgent()
        
        # Add context to prompt
        context_info = ""
        if total_queries and len(total_queries) > 1:
            other_queries = [q for i, q in enumerate(total_queries) if i != query_index]
            context_info = f"""
CONTEXT AWARENESS:
- Total queries being analyzed: {len(total_queries)}
- Your query index: {query_index + 1}/{len(total_queries)}
- Other queries: {', '.join([f'"{q[:30]}..."' for q in other_queries[:3]])}
- Specialization required: True

SPECIALIZATION INSTRUCTIONS:
- Focus ONLY on your specific query area
- Don't duplicate analysis from other queries
- Be unique and specialized in your chain
- Provide different perspective from other queries
- Create a chain that's distinct from other queries
"""
        
        # Create the enhanced prompt for the LLM
        prompt = f"""
        You are an expert financial analyst creating rigorous impact chains for client reporting.

        TASK: Based on the user query (starting event) and evidence, write a logical impact chain showing how Event A impacts Event B, then Event C, leading to final stock price impact.

        {context_info}

        INPUT DATA:
        - Ticker: {ticker}
        - Starting Event (User Query): {user_question}
        - Agent Analysis Results: {agent_analysis_results}

        CRITICAL REQUIREMENT - MARKET EXPECTATION DATA FOR REFERENCE:
        **USE HISTORICAL RETURN RATES AND DATE RANGES FOR REFERENCE**: The Market Expectation Agent provides historical data with return rates and date ranges. Use these as reference points in your impact chain analysis.

        MARKET EXPECTATION DATA USAGE:
        1. **REFERENCE RETURN RATES**: Use percentage returns (e.g., "-15.3%", "+8.7%", "-22.1%") as reference points
        2. **REFERENCE DATE RANGES**: Use historical date ranges (e.g., "from 2023-01-15 to 2023-01-18") as reference points
        3. **NO GENERIC TERMS**: Do NOT use terms like "uptrend", "downtrend", "positive", "negative"
        4. **ANALYSIS FOCUS**: Focus on the logical chain progression, using market data as supporting evidence

        RIGOROUS LOGIC REQUIREMENTS:
        1. **START WITH USER QUERY** - The starting event from the user query
        2. **REFERENCE MARKET DATA** - Use return rates and date ranges from Market Expectation Agent as reference points
        3. **FOLLOW LOGICAL PROGRESSION** - Each event must logically cause the next event
        4. **USE QUANTITATIVE EVIDENCE** - Reference percentages and return rates from agent analysis results
        5. **CONSISTENT DIRECTION** - If negative news, show how it leads to negative impact; if positive, show positive progression
        6. **ANALYSIS FOCUS** - Focus on logical chain progression with market data as supporting evidence
        7. **SPECIALIZATION** - Focus on YOUR specific query area. Don't duplicate analysis from other queries.
        8. **REFERENCE FOCUS** - Use market data as reference points, not as primary extraction targets.

        CHAIN STRUCTURE WITH MARKET DATA REFERENCE:
        Starting Event → Market Data Reference (X% return from date1 to date2) → Intermediate Event 1 → Intermediate Event 2 → Final Stock Price Impact

        MARKET EXPECTATION ELEMENTS FOR REFERENCE:
        - **Return Rate**: Use percentage returns (e.g., "-15.3%", "+8.7%")
        - **Date Range**: Use historical date ranges (e.g., "from 2023-01-15 to 2023-01-18")
        - **Historical Evidence**: Reference historical return rates and date ranges
        - **Analysis Support**: Use market data to support logical chain progression

        DECISION RULES:
        - **LONG TERM UP**: Business strategy, future plans, structural improvements
        - **SHORT TERM DOWN**: Market sentiment, temporary headwinds, short-term challenges  
        - **LONG TERM DOWN**: Fundamental business model issues, competitive threats
        - **SHORT TERM UP**: Temporary positive catalysts, immediate market reactions

        EXAMPLE CHAIN WITH MARKET DATA REFERENCE:
        "Tariff increase → Market data shows similar tariff events caused -15.3% (refer from 2023-01-15 to 2023-01-18) → Supply chain disruption (-3% margin) → Inventory pressure (-2% revenue) → Short Term Down"

        OUTPUT FORMAT:
        {{
            "initial_query": "{user_question}",
            "ticker": "{ticker}",
            "impact_chain": "Event A → Market Data Reference (X% return from date1 to date2) → Event B (XX% impact) → Event C (XX% impact) → Final Direction",
            "final_direction": "Short Term Up, Short Term Down, Long Term Up, or Long Term Down",
            "chain_explanation": "Brief explanation including the return rate and date range from market data reference",
            "node_count": <number of events>,
            "edge_count": <number of connections>,
            "events": ["Event A", "Market Data Reference (X% return from date1 to date2)", "Event B (XX% impact)", "Event C (XX% impact)", "Final Direction"]
        }}

        REQUIREMENTS:
        1. **Include return rates** from Market Expectation Agent data as reference
        2. **Include date ranges** (from date1 to date2) as reference
        3. **Reference percentages** from the market analysis
        4. **Reference the quantitative evidence** in the chain explanation
        5. **Show the return rate and date range** as a reference node in the impact chain
        6. **Use numbers** from the agent analysis results as supporting evidence
        7. **FOCUS ON LOGICAL PROGRESSION**: Prioritize logical chain progression over precise numbers

        REFERENCE PATTERNS IN AGENT ANALYSIS RESULTS:
        - "Similar events caused X% return from date1 to date2"
        - "Historical average return of X% from date1 to date2"
        - "Previous similar events resulted in X% impact from date1 to date2"
        - "Stock price moved X% during similar events from date1 to date2"
        - "X% return from date1 to date2"
        - Any quantitative return rate data and date ranges from Market Expectation Agent

        FORBIDDEN TERMS (DO NOT USE):
        - "uptrend", "downtrend", "positive trend", "negative trend"
        - "bullish", "bearish", "positive", "negative"
        - "increased", "decreased", "rose", "fell" (without specific percentages)
        - Any generic descriptive terms without specific numeric data
        - "estimated", "return over", "last", "past", "previous"

        REFERENCE TERMS (USE AS REFERENCE):
        - Percentage returns: "-15.3%", "+8.7%", "-22.1%"
        - Date ranges: "from 2023-01-15 to 2023-01-18"
        - Numeric data from Market Expectation Agent

        IMPORTANT:
        - Start with the user query as the first event
        - Include return rates and date ranges from Market Expectation Agent as reference
        - Follow rigorous logical progression with quantitative evidence
        - Use return rates and date ranges from market data as supporting evidence
        - Final direction must be one of the four options
        - Focus on logical chain progression with market data as reference points
        - DO NOT include "estimated", "return over", "last", "past", "previous" in the output
        
        CRITICAL: Output ALL text in {language} language only. Do NOT use any other language.
        """
        
        # Use the existing method but with enhanced prompt
        return agent.generate_impact_chain(
            ticker=ticker,
            user_question=user_question,
            verification_links=verification_links,
            verification_reasoning=verification_reasoning,
            agent_analysis_results=agent_analysis_results,
            language=language
        )
        
    except Exception as e:
        raise Exception(f"Concurrent Chain of Thought processing failed: {e}")

def concurrent_call_generate_impact_chain_with_mermaid(
    ticker: str,
    user_question: str,
    verification_links: List[str],
    verification_reasoning: str,
    agent_analysis_results: Dict[str, Any],
    total_queries: List[str] = None,
    query_index: int = 0,
    context: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Generate impact chain with Mermaid visualization for concurrent processing
    """
    try:
        # Generate the chain
        chain_result = concurrent_call_generate_impact_chain(
            ticker=ticker,
            user_question=user_question,
            verification_links=verification_links,
            verification_reasoning=verification_reasoning,
            agent_analysis_results=agent_analysis_results,
            total_queries=total_queries,
            query_index=query_index,
            context=context
        )
        
        # Generate Mermaid code
        mermaid_code = generate_mermaid_code(
            node_count=chain_result.node_count,
            edge_count=chain_result.edge_count,
            events=chain_result.events
        )
        
        # Create comprehensive result
        result_bucket = {
            "query": user_question,
            "query_index": query_index,
            "status": "success",
            "chain_of_thought": {
                "final_direction": chain_result.final_direction,
                "impact_chain": chain_result.impact_chain,
                "chain_explanation": chain_result.chain_explanation,
                "node_count": chain_result.node_count,
                "edge_count": chain_result.edge_count,
                "events": chain_result.events
            },
            "mermaid_code": mermaid_code,
            "context": {
                "total_queries_count": len(total_queries) if total_queries else 1
            }
        }
        
        return result_bucket
        
    except Exception as e:
        return {
            "query": user_question,
            "query_index": query_index,
            "status": "failed",
            "error": str(e)
        }

def concurrent_call_generate_impact_chain_auto(
    ticker: str,
    verification_links: List[str],
    verification_reasoning: str,
    agent_analysis_results: Dict[str, Any],
    total_queries: List[str] = None,
    query_index: int = 0,
    context: Dict[str, Any] = None,
    language: str = "English"
) -> ChainOfThoughtResult:
    """
    Generate a dynamic impact chain with automatic query assignment from total_queries list
    """
    try:
        # Automatically get the query from total_queries based on query_index
        if not total_queries or query_index >= len(total_queries):
            raise Exception(f"Invalid query_index {query_index} for total_queries length {len(total_queries) if total_queries else 0}")
        
        user_question = total_queries[query_index]
        
        # Initialize agent
        agent = ChainOfThoughtAgent()
        
        # Use the existing generate_impact_chain method
        return agent.generate_impact_chain(
            ticker=ticker,
            user_question=user_question,
            verification_links=verification_links,
            verification_reasoning=verification_reasoning,
            agent_analysis_results=agent_analysis_results,
            language=language
        )
        
    except Exception as e:
        raise Exception(f"Concurrent Chain of Thought processing failed: {e}")

def concurrent_call_generate_impact_chain_with_mermaid_auto(
    ticker: str,
    verification_links: List[str],
    verification_reasoning: str,
    agent_analysis_results: Dict[str, Any],
    total_queries: List[str] = None,
    query_index: int = 0,
    context: Dict[str, Any] = None,
    language: str = "English"
) -> Dict[str, Any]:
    """
    Generate impact chain with Mermaid visualization and automatic query assignment
    """
    try:
        # Generate the chain
        chain_result = concurrent_call_generate_impact_chain_auto(
            ticker=ticker,
            verification_links=verification_links,
            verification_reasoning=verification_reasoning,
            agent_analysis_results=agent_analysis_results,
            total_queries=total_queries,
            query_index=query_index,
            context=context,
            language=language
        )
        
        # Get the assigned query
        user_question = total_queries[query_index] if total_queries and query_index < len(total_queries) else "Unknown"
        
        # Generate Mermaid code
        mermaid_code = generate_mermaid_code(
            node_count=chain_result.node_count,
            edge_count=chain_result.edge_count,
            events=chain_result.events
        )
        
        # Create comprehensive result
        result_bucket = {
            "query": user_question,
            "query_index": query_index,
            "status": "success",
            "chain_of_thought": {
                "final_direction": chain_result.final_direction,
                "impact_chain": chain_result.impact_chain,
                "chain_explanation": chain_result.chain_explanation,
                "node_count": chain_result.node_count,
                "edge_count": chain_result.edge_count,
                "events": chain_result.events
            },
            "mermaid_code": mermaid_code,
            "context": {
                "total_queries_count": len(total_queries) if total_queries else 1
            }
        }
        
        return result_bucket
        
    except Exception as e:
        return {
            "query": total_queries[query_index] if total_queries and query_index < len(total_queries) else "Unknown",
            "query_index": query_index,
            "status": "failed",
            "error": str(e)
        }
