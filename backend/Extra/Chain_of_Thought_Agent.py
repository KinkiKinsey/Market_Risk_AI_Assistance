import json
import re
import asyncio
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from LLM_Call_Agent import LLMCallAgent

class ChainOfThoughtResult(BaseModel):
    initial_query: str = Field(description="The original user question")
    ticker: str = Field(description="Stock ticker symbol")
    impact_chain: str = Field(description="Linear chain: A → B → C → D → Final")
    final_direction: str = Field(description="Final impact direction: 'Dimension + Positive/Negative' (e.g., 'Macro Positive', 'Competitor Negative')")
    dimension: str = Field(description="Analysis dimension: Macro, Micro, Sector, Competitor, Financial, etc.", default="General")
    sentiment: str = Field(description="Impact sentiment: 'Positive' or 'Negative'", default="Neutral")
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
    def clean_event_text(event_text):
        """Clean event text and ensure English-only output for Mermaid"""
        # Remove field names like "initial_query:", "ticker:", etc.
        if ': ' in event_text:
            clean_event = event_text.split(': ')[-1]
        else:
            clean_event = event_text
        
        # Translate common Chinese terms to English for Mermaid consistency
        chinese_to_english = {
            '短期上涨': 'Short Term Up',
            '短期下跌': 'Short Term Down', 
            '长期上涨': 'Long Term Up',
            '长期下跌': 'Long Term Down',
            '上涨': 'Up',
            '下跌': 'Down',
            '上升': 'Up',
            '下降': 'Down',
            '短期': 'Short Term',
            '长期': 'Long Term',
            '影响': 'Impact',
            '分析': 'Analysis',
            '结果': 'Result',
            '决策': 'Decision',
            '事件': 'Event',
            '市场': 'Market',
            '股票': 'Stock',
            '价格': 'Price',
            '收益': 'Revenue',
            '利润': 'Profit',
            '风险': 'Risk',
            '机会': 'Opportunity'
        }
        
        # Replace Chinese terms with English equivalents
        for chinese, english in chinese_to_english.items():
            clean_event = clean_event.replace(chinese, english)
        
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
        
        return clean_event
    
    clean_events = []
    for event in events[:node_count]:
        clean_events.append(clean_event_text(event))
    
    # ✅ TRULY DYNAMIC MERMAID CODE - Adapts to any number of nodes
    mermaid_code = "graph LR\n"
    mermaid_code += f"    title[\"Chain {node_count}: {clean_events[0][:30]}...\"]\n"
    
    # ✅ FIXED - Create separate node for each event
    for i in range(node_count):
        node_id = node_ids[i]
        if i < len(clean_events):
            # ✅ LAST NODE - Show the final decision (Dimension + Positive/Negative)
            if i == node_count - 1:  # Last node
                # Extract dimension and sentiment from the last event
                last_event = clean_events[i]
                
                # Extract dimension
                dimension = None
                for dim in ['Macro', 'Micro', 'Sector', 'Competitor', 'Financial', 'General']:
                    if dim in last_event or dim.lower() in last_event.lower():
                        dimension = dim
                        break
                
                # Extract sentiment
                sentiment = None
                if "Positive" in last_event or "positive" in last_event.lower() or "积极" in last_event or "正面" in last_event:
                    sentiment = "Positive"
                elif "Negative" in last_event or "negative" in last_event.lower() or "消极" in last_event or "负面" in last_event:
                    sentiment = "Negative"
                
                # Fallback: Check for old format (Up/Down) and convert
                if not sentiment:
                    if "Up" in last_event or "up" in last_event.lower() or "上涨" in last_event or "上升" in last_event:
                        sentiment = "Positive"
                    elif "Down" in last_event or "down" in last_event.lower() or "下跌" in last_event or "下降" in last_event:
                        sentiment = "Negative"
                
                # Construct final event text
                if dimension and sentiment:
                    event_text = f"{dimension} {sentiment}"
                elif sentiment:
                    event_text = f"Impact {sentiment}"
                else:
                    event_text = last_event[:50]  # Use truncated original if can't extract
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
    except (json.JSONDecodeError, AttributeError, KeyError) as e:
        pass  # Fall through to chain parsing
    
    # ✅ TRULY DYNAMIC - Look for ANY chain pattern, not just 5 nodes
    try:
        # Look for ANY chain pattern: A → B → C or A → B → C → D or A → B → C → D → E → F
        chain_match = re.search(r'([^→]+(?:→[^→]+)*)', response)
        if chain_match:
            chain_text = chain_match.group(1)
            chain_parts = [part.strip() for part in chain_text.split("→")]
            
            # ✅ DYNAMIC - Handle any number of parts
            if len(chain_parts) >= 2:  # At least 2 parts for a chain
                # Determine final direction with Dimension + Positive/Negative format
                last_event = chain_parts[-1]
                
                # Extract dimension
                dimension = "General"
                for dim in ['Macro', 'Micro', 'Sector', 'Competitor', 'Financial']:
                    if dim in last_event or dim.lower() in last_event.lower():
                        dimension = dim
                        break
                
                # Extract sentiment
                sentiment = "Positive"
                if "Positive" in last_event or "positive" in last_event.lower():
                    sentiment = "Positive"
                elif "Negative" in last_event or "negative" in last_event.lower():
                    sentiment = "Negative"
                elif "Up" in last_event:
                    sentiment = "Positive"
                elif "Down" in last_event:
                    sentiment = "Negative"
                
                final_direction = f"{dimension} {sentiment}"
                
                return {
                    "impact_chain": chain_text,
                    "final_direction": final_direction,
                    "dimension": dimension,
                    "sentiment": sentiment,
                    "node_count": len(chain_parts),  # ✅ DYNAMIC
                    "edge_count": len(chain_parts) - 1,  # ✅ DYNAMIC
                    "events": chain_parts
                }
    except (AttributeError, IndexError, ValueError) as e:
        pass  # Return None if parsing fails
    
    return None

class ChainOfThoughtAgent:
    def __init__(self):
        """Initialize the Chain of Thought Agent"""
        self.llm_agent = LLMCallAgent(
            default_provider="deepseek",
            default_model="deepseek-chat"
        )
        self.structured_llm = self.llm_agent.get_structured_llm(ChainOfThoughtResult)
    
    def _ensure_english_direction(self, direction: str) -> str:
        """Ensure final_direction is always in English with [Dimension] [Positive/Negative] format"""
        direction = str(direction).strip()
        
        # Dimension mapping (Chinese to English)
        dimension_map = {
            '宏观': 'Macro',
            '微观': 'Micro',
            '行业': 'Sector',
            '竞争': 'Competitor',
            '财务': 'Financial',
            'macro': 'Macro',
            'micro': 'Micro',
            'sector': 'Sector',
            'competitor': 'Competitor',
            'financial': 'Financial'
        }
        
        # Sentiment mapping (Chinese to English)
        sentiment_map = {
            '积极': 'Positive',
            '消极': 'Negative',
            '正面': 'Positive',
            '负面': 'Negative',
            'positive': 'Positive',
            'negative': 'Negative',
            'pos': 'Positive',
            'neg': 'Negative'
        }
        
        # Try to parse existing format "[Dimension] [Positive/Negative]"
        if ' ' in direction:
            parts = direction.split()
            if len(parts) >= 2:
                dim_part = parts[0].lower()
                sent_part = parts[1].lower()
                
                # Extract dimension
                dimension = None
                for key, value in dimension_map.items():
                    if key.lower() in dim_part.lower():
                        dimension = value
                        break
                
                # Extract sentiment
                sentiment = None
                for key, value in sentiment_map.items():
                    if key.lower() in sent_part.lower():
                        sentiment = value
                        break
                
                if dimension and sentiment:
                    return f"{dimension} {sentiment}"
        
        # Fallback: Try to extract from direction string
        dimension = None
        sentiment = None
        
        # Extract dimension
        for key, value in dimension_map.items():
            if key.lower() in direction.lower():
                dimension = value
                break
        
        # Extract sentiment
        for key, value in sentiment_map.items():
            if key.lower() in direction.lower():
                sentiment = value
                break
        
        # If still not found, try common patterns
        if not sentiment:
            if 'positive' in direction.lower() or '积极' in direction or '正面' in direction or 'up' in direction.lower():
                sentiment = 'Positive'
            elif 'negative' in direction.lower() or '消极' in direction or '负面' in direction or 'down' in direction.lower():
                sentiment = 'Negative'
        
        # Default values if not found
        if not dimension:
            dimension = 'General'
        if not sentiment:
            sentiment = 'Positive'
        
        return f"{dimension} {sentiment}"
    
    def _extract_dimension_from_query(self, query: str) -> str:
        """Extract dimension from query text"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['macro', 'macroeconomic', 'economic', 'policy', 'fed', 'interest', 'government', '宏观']):
            return 'Macro'
        elif any(word in query_lower for word in ['competitor', 'competition', 'rival', 'market share', 'vs', '竞争']):
            return 'Competitor'
        elif any(word in query_lower for word in ['sector', 'industry', 'market', 'trend', '行业']):
            return 'Sector'
        elif any(word in query_lower for word in ['valuation', 'financial', 'metrics', 'ratio', 'profit', '财务']):
            return 'Financial'
        elif any(word in query_lower for word in ['business', 'product', 'company', 'internal', 'operation', '微观', '公司']):
            return 'Micro'
        else:
            return 'General'
    
    async def generate_impact_chain(
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
        You are a DEEP RESEARCH FINANCIAL ANALYST with expertise in rigorous impact analysis and fact-finding for institutional client reporting.

        TASK: Conduct DEEP RESEARCH and DEEP REASONING to DIG OUT THE FACTS on how the starting event creates cascading impacts. Write a comprehensive logical impact chain showing how Event A impacts Event B, then Event C, leading to final stock price impact.

        DEEP RESEARCH REQUIREMENTS:
        1. **DIG DEEP INTO FACTS** - Extract specific data points, percentages, ratios, and quantitative evidence
        2. **DEEP REASONING** - Apply sophisticated financial logic and market dynamics analysis
        3. **DEEP ANALYSIS** - Uncover hidden connections, secondary effects, and long-term implications
        4. **FACT-BASED EVIDENCE** - Every step must be supported by concrete data from agent analysis results
        5. **COMPREHENSIVE IMPACT ASSESSMENT** - Consider all dimensions: financial, operational, competitive, market sentiment

        INPUT DATA:
        - Ticker: {ticker}
        - Starting Event (User Query): {user_question}
        - Agent Analysis Results: {agent_analysis_results}

        CRITICAL REQUIREMENT - DISTINGUISH DATA TYPES:
        **UNDERSTAND DATA TYPES**: Distinguish between CURRENT MARKET DATA and HISTORICAL REFERENCE DATA.

        DATA TYPE CLASSIFICATION:
        1. **CURRENT MARKET DATA** (from Sector Analyst, Earnings Agent):
           - Current performance metrics (e.g., "xxx% YoY growth", "xx% revenue increase")
           - Current market conditions (e.g., "xx-xx% market share", "xx.x% revenue from reserves")
           - Current financial metrics (e.g., "operating margin xx.xx%", "revenue $xxxM")
           - **USE AS**: Evidence of current performance, NOT as historical precedent

        2. **HISTORICAL REFERENCE DATA** (from Market Expectation Agent):
           - Historical trend segments with specific date ranges (e.g., "xxxx-xx-xx to xxxx-xx-xx")
           - Historical return percentages with verified dates
           - **USE AS**: Historical precedent for similar events

        3. **FORBIDDEN PRACTICES**:
           - Do NOT convert current market data into fake historical references
           - Do NOT add fake date ranges to current performance data
           - Do NOT use current metrics as "historical precedent"

        DEEP RESEARCH & RIGOROUS LOGIC REQUIREMENTS:
        1. **START WITH USER QUERY** - The starting event from the user query
        2. **DEEP FACT EXTRACTION** - DIG OUT specific numbers, percentages, ratios, financial metrics, and concrete data points
        3. **REFERENCE MARKET DATA** - Use return rates and date ranges from Market Expectation Agent as reference points
        4. **DEEP REASONING PROGRESSION** - Each event must logically cause the next event with sophisticated financial analysis
        5. **QUANTITATIVE EVIDENCE** - Reference percentages, return rates, financial ratios, and concrete metrics from agent analysis results
        6. **DEEP IMPACT ANALYSIS** - Uncover secondary effects, competitive responses, operational changes, and market dynamics
        7. **MAINTAIN SAME DIRECTION** - CRITICAL: If the starting event is positive/good news, show how it creates POSITIVE impact throughout the chain. If the starting event is negative/bad news, show how it creates NEGATIVE impact throughout the chain. DO NOT REVERSE THE IMPACT DIRECTION.
        8. **COMPREHENSIVE RESEARCH** - Consider financial, operational, competitive, regulatory, and market sentiment impacts
        9. **FACT-BASED REASONING** - Every connection must be supported by concrete evidence and data

        CHAIN STRUCTURE WITH DEEP RESEARCH:
        Starting Event → Deep Fact Extraction (specific data points) → Market Data Reference (X% return from date1 to date2) → Deep Analysis Event 1 → Deep Analysis Event 2 → Comprehensive Final Impact

        DEEP RESEARCH ELEMENTS FOR COMPREHENSIVE ANALYSIS:
        - **Current Performance Metrics**: Use current market data (e.g., "xxx% YoY growth", "xx% revenue increase") as evidence of current performance
        - **Historical Trend Data**: Use only verified historical data with specific date ranges from Market Expectation Agent
        - **Financial Metrics**: Extract current P/E ratios, revenue growth rates, margin changes, debt levels
        - **Operational Data**: Reference current capacity utilization, customer concentration, market share changes
        - **Competitive Analysis**: Include current competitor responses, market positioning, pricing dynamics
        - **Market Evidence**: Use current market data to support logical connections, not as historical precedent
        - **Fact-Based Support**: Use concrete current and historical data to support every logical connection

        DIMENSION + SENTIMENT DECISION RULES:
        
        **DIMENSIONS** (Extract from query context):
        - **Macro**: Macroeconomic factors, policy changes, interest rates, economic indicators, government actions
        - **Micro**: Company-specific developments, internal operations, product launches, business milestones
        - **Sector**: Industry trends, sector growth, market dynamics, technology adoption
        - **Competitor**: Competitive landscape, rival companies' moves, market share battles
        - **Financial**: Valuation metrics, financial health, profitability, cost structure
        
        **SENTIMENT RULES** (Determine impact direction):
        - **Positive**: Growth opportunities, competitive advantages, favorable developments, structural improvements
        - **Negative**: Threats, challenges, competitive pressures, adverse developments, structural risks
        
        **OUTPUT FORMAT**: "[Dimension] [Positive/Negative]"
        - Examples: "Macro Positive", "Competitor Negative", "Micro Positive", "Sector Negative", "Financial Positive"

        EXAMPLE CHAINS (PROPER DATA USAGE):
        
        POSITIVE EXAMPLE (Micro Positive):
        "New product launch → Current market shows xxx% YoY growth in similar products → Increased demand (+xx% revenue) → Market share growth → Micro Positive"
        
        NEGATIVE EXAMPLE (Financial Negative):
        "Operating cost pressure → Current data shows -xx.xx% operating margin → Cash flow pressure → Financial stability risk → Financial Negative"
        
        HISTORICAL REFERENCE EXAMPLE (Sector Positive):
        "Regulatory approval → Historical data shows +x.xxx% return from xxxx-xx-xx to xxxx-xx-xx for similar events → Institutional adoption → Revenue growth → Sector Positive"
        
        **CRITICAL RULES**:
        - Use CURRENT market data as evidence of current performance
        - Use HISTORICAL data only if it contains verified date ranges
        - Do NOT convert current data into fake historical references
        
        **SPECIFIC WARNING**: 
        - "xxx% YoY growth" is CURRENT market data, NOT historical precedent
        - Do NOT create fake references like "类似事件导致xxx%年增长率从xxxx到xxxx"
        - Use current data as evidence of current performance, not as historical trend

        OUTPUT FORMAT:
        {{
            "initial_query": "{user_question}",
            "ticker": "{ticker}",
            "impact_chain": "Event A → Market Data Reference (X% return from date1 to date2) → Event B (XX% impact) → Event C (XX% impact) → Final Direction (in {language})",
            "final_direction": "Human-readable direction in {language} combining dimension and sentiment",
            "dimension": "MUST BE ENGLISH ONLY - ONE OF: 'Macro', 'Micro', 'Sector', 'Competitor', or 'Financial'",
            "sentiment": "MUST BE ENGLISH ONLY - ONE OF: 'Positive' or 'Negative'",
            "chain_explanation": "Brief explanation in {language} including the return rate and date range from market data reference",
            "node_count": <number of events>,
            "edge_count": <number of connections>,
            "events": ["Event A", "Market Data Reference (X% return from date1 to date2)", "Event B (XX% impact)", "Event C (XX% impact)", "Final Direction (in {language})"]
        }}
        
        **CRITICAL LANGUAGE RULES**:
        - dimension: ALWAYS English ('Macro', 'Micro', 'Sector', 'Competitor', 'Financial')
        - sentiment: ALWAYS English ('Positive', 'Negative')
        - final_direction: Can be in {language} but should clearly indicate dimension and sentiment
        - impact_chain: In {language}
        - chain_explanation: In {language}
        - events: In {language}

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
        - Use only actual percentage returns from verified data
        - Use only real date ranges from verified data
        - Numeric data from Market Expectation Agent

        CRITICAL DIRECTION RULE:
        - **POSITIVE STARTING EVENT** (good news, positive development, growth opportunity) → MUST lead to **POSITIVE IMPACT** → Sentiment should be "Positive"
        - **NEGATIVE STARTING EVENT** (bad news, negative development, threat, problem) → MUST lead to **NEGATIVE IMPACT** → Sentiment should be "Negative"
        - **NEVER REVERSE**: If something is good news, don't turn it into negative impact. If something is bad news, don't turn it into positive impact.
        - **DIMENSION EXTRACTION**: Extract the dimension from the query context (Macro, Micro, Sector, Competitor, Financial)

        IMPORTANT:
        - Start with the user query as the first event
        - Include return rates and date ranges from Market Expectation Agent as reference
        - Follow rigorous logical progression with quantitative evidence
        - Use return rates and date ranges from market data as supporting evidence
        - Final direction MUST be FORMAT: "[Dimension] [Positive/Negative]" - Examples: "Macro Positive", "Competitor Negative", "Micro Positive"
        - Dimension MUST be one of: "Macro", "Micro", "Sector", "Competitor", "Financial"
        - Sentiment MUST be one of: "Positive", "Negative"
        - Focus on logical chain progression with market data as reference points
        - DO NOT include "estimated", "return over", "last", "past", "previous" in the output
        - CRITICAL: dimension and sentiment fields MUST be in English; other fields adapt to {language}
        
        DEEP RESEARCH FINAL INSTRUCTIONS:
        - **DIG DEEP INTO FACTS**: Extract specific numbers, percentages, ratios, financial metrics, and concrete data points
        - **DEEP REASONING**: Apply sophisticated financial logic and market dynamics analysis  
        - **COMPREHENSIVE ANALYSIS**: Consider financial, operational, competitive, regulatory, and market sentiment impacts
        - **FACT-BASED REASONING**: Every connection must be supported by concrete evidence and data
        - **DEEP IMPACT ANALYSIS**: Uncover secondary effects, competitive responses, operational changes, and market dynamics
        - **COMPREHENSIVE RESEARCH**: Dig out the facts on the impact with thorough analysis
        """
        
        # Add language instruction only if not English
        if language.lower() != "english":
            prompt += f"\n        CRITICAL: Output ALL text in {language} language only. Do NOT use any other language."
        
        try:
            # Try structured output first
            result = await asyncio.to_thread(self.structured_llm.invoke, prompt)
            
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
                # Post-process to ensure proper dimension and sentiment extraction
                if hasattr(result, 'dimension') and hasattr(result, 'sentiment'):
                    # If dimension/sentiment not provided or empty, extract from query and final_direction
                    if not result.dimension or result.dimension == "General":
                        result.dimension = self._extract_dimension_from_query(user_question)
                    
                    if not result.sentiment or result.sentiment == "Neutral":
                        # Extract sentiment from final_direction
                        if 'positive' in str(result.final_direction).lower() or 'up' in str(result.final_direction).lower():
                            result.sentiment = "Positive"
                        elif 'negative' in str(result.final_direction).lower() or 'down' in str(result.final_direction).lower():
                            result.sentiment = "Negative"
                
                # Ensure final_direction is properly formatted
                if hasattr(result, 'final_direction'):
                    # If final_direction doesn't contain dimension info, add it
                    if result.dimension not in str(result.final_direction):
                        result.final_direction = f"{result.dimension} {result.sentiment}"
                
                return result
        except Exception as e:
            # Fallback to regular LLM call
            try:
                response = await asyncio.to_thread(self.llm_agent.call_deepseek, prompt)
                parsed = parse_llm_response(response)
                
                if parsed:
                    # Extract dimension and sentiment
                    dimension = parsed.get("dimension", self._extract_dimension_from_query(user_question))
                    sentiment = parsed.get("sentiment", "Positive")
                    
                    # If sentiment not provided, extract from final_direction
                    if sentiment == "Positive" or sentiment == "Neutral":
                        if 'negative' in str(parsed.get("final_direction", "")).lower() or 'down' in str(parsed.get("final_direction", "")).lower():
                            sentiment = "Negative"
                    
                    # Ensure final_direction is properly formatted
                    final_direction = parsed.get("final_direction", "")
                    if not final_direction or dimension not in final_direction:
                        final_direction = f"{dimension} {sentiment}"
                    
                    return ChainOfThoughtResult(
                        initial_query=user_question,
                        ticker=ticker,
                        impact_chain=parsed.get("impact_chain", ""),
                        final_direction=final_direction,
                        dimension=dimension,
                        sentiment=sentiment,
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
        You are a DEEP RESEARCH FINANCIAL ANALYST with expertise in rigorous impact analysis and fact-finding for institutional client reporting.

        TASK: Conduct DEEP RESEARCH and DEEP REASONING to DIG OUT THE FACTS on how the starting event creates cascading impacts. Write a comprehensive logical impact chain showing how Event A impacts Event B, then Event C, leading to final stock price impact.

        {context_info}

        INPUT DATA:
        - Ticker: {ticker}
        - Starting Event (User Query): {user_question}
        - Agent Analysis Results: {agent_analysis_results}

        CRITICAL REQUIREMENT - DISTINGUISH DATA TYPES:
        **UNDERSTAND DATA TYPES**: Distinguish between CURRENT MARKET DATA and HISTORICAL REFERENCE DATA.

        DATA TYPE CLASSIFICATION:
        1. **CURRENT MARKET DATA** (from Sector Analyst, Earnings Agent):
           - Current performance metrics (e.g., "xxx% YoY growth", "xx% revenue increase")
           - Current market conditions (e.g., "xx-xx% market share", "xx.x% revenue from reserves")
           - Current financial metrics (e.g., "operating margin xx.xx%", "revenue $xxxM")
           - **USE AS**: Evidence of current performance, NOT as historical precedent

        2. **HISTORICAL REFERENCE DATA** (from Market Expectation Agent):
           - Historical trend segments with specific date ranges (e.g., "xxxx-xx-xx to xxxx-xx-xx")
           - Historical return percentages with verified dates
           - **USE AS**: Historical precedent for similar events

        3. **FORBIDDEN PRACTICES**:
           - Do NOT convert current market data into fake historical references
           - Do NOT add fake date ranges to current performance data
           - Do NOT use current metrics as "historical precedent"

        RIGOROUS LOGIC REQUIREMENTS:
        1. **START WITH USER QUERY** - The starting event from the user query
        2. **REFERENCE MARKET DATA** - Use return rates and date ranges from Market Expectation Agent as reference points
        3. **FOLLOW LOGICAL PROGRESSION** - Each event must logically cause the next event
        4. **USE QUANTITATIVE EVIDENCE** - Reference percentages and return rates from agent analysis results
        5. **MAINTAIN SAME DIRECTION** - CRITICAL: If the starting event is positive/good news, show how it creates POSITIVE impact throughout the chain. If the starting event is negative/bad news, show how it creates NEGATIVE impact throughout the chain. DO NOT REVERSE THE IMPACT DIRECTION.
        6. **ANALYSIS FOCUS** - Focus on logical chain progression with market data as supporting evidence
        7. **SPECIALIZATION** - Focus on YOUR specific query area. Don't duplicate analysis from other queries.
        8. **REFERENCE FOCUS** - Use market data as reference points, not as primary extraction targets.

        CHAIN STRUCTURE WITH MARKET DATA REFERENCE:
        Starting Event → Market Data Reference (X% return from date1 to date2) → Intermediate Event 1 → Intermediate Event 2 → Final Stock Price Impact

        MARKET EXPECTATION ELEMENTS (PROPER DATA CLASSIFICATION):
        - **Current Market Data**: Use current performance metrics (e.g., "xxx% YoY growth") as evidence of current market conditions
        - **Historical Trend Data**: Use only verified historical data with specific date ranges from Market Expectation Agent
        - **Data Context**: Clearly distinguish between current performance evidence and historical precedent
        - **Analysis Support**: Use appropriate data type to support logical chain progression

        DIMENSION + SENTIMENT DECISION RULES:
        
        **DIMENSIONS** (Extract from query context):
        - **Macro**: Macroeconomic factors, policy changes, interest rates, economic indicators, government actions
        - **Micro**: Company-specific developments, internal operations, product launches, business milestones
        - **Sector**: Industry trends, sector growth, market dynamics, technology adoption
        - **Competitor**: Competitive landscape, rival companies' moves, market share battles
        - **Financial**: Valuation metrics, financial health, profitability, cost structure
        
        **SENTIMENT RULES** (Determine impact direction):
        - **Positive**: Growth opportunities, competitive advantages, favorable developments, structural improvements
        - **Negative**: Threats, challenges, competitive pressures, adverse developments, structural risks
        
        **OUTPUT FORMAT**: "[Dimension] [Positive/Negative]"
        - Examples: "Macro Positive", "Competitor Negative", "Micro Positive", "Sector Negative", "Financial Positive"

        EXAMPLE CHAINS (PROPER DATA USAGE):
        
        POSITIVE EXAMPLE (Micro Positive):
        "New product launch → Current market shows xxx% YoY growth in similar products → Increased demand (+xx% revenue) → Market share growth → Micro Positive"
        
        NEGATIVE EXAMPLE (Financial Negative):
        "Operating cost pressure → Current data shows -xx.xx% operating margin → Cash flow pressure → Financial stability risk → Financial Negative"
        
        HISTORICAL REFERENCE EXAMPLE (Sector Positive):
        "Regulatory approval → Historical data shows +x.xxx% return from xxxx-xx-xx to xxxx-xx-xx for similar events → Institutional adoption → Revenue growth → Sector Positive"
        
        **CRITICAL RULES**:
        - Use CURRENT market data as evidence of current performance
        - Use HISTORICAL data only if it contains verified date ranges
        - Do NOT convert current data into fake historical references
        
        **SPECIFIC WARNING**: 
        - "xxx% YoY growth" is CURRENT market data, NOT historical precedent
        - Do NOT create fake references like "类似事件导致xxx%年增长率从xxxx到xxxx"
        - Use current data as evidence of current performance, not as historical trend

        OUTPUT FORMAT:
        {{
            "initial_query": "{user_question}",
            "ticker": "{ticker}",
            "impact_chain": "Event A → Market Data Reference (X% return from date1 to date2) → Event B (XX% impact) → Event C (XX% impact) → Final Direction (in {language})",
            "final_direction": "Human-readable direction in {language} combining dimension and sentiment",
            "dimension": "MUST BE ENGLISH ONLY - ONE OF: 'Macro', 'Micro', 'Sector', 'Competitor', or 'Financial'",
            "sentiment": "MUST BE ENGLISH ONLY - ONE OF: 'Positive' or 'Negative'",
            "chain_explanation": "Brief explanation in {language} including the return rate and date range from market data reference",
            "node_count": <number of events>,
            "edge_count": <number of connections>,
            "events": ["Event A", "Market Data Reference (X% return from date1 to date2)", "Event B (XX% impact)", "Event C (XX% impact)", "Final Direction (in {language})"]
        }}
        
        **CRITICAL LANGUAGE RULES**:
        - dimension: ALWAYS English ('Macro', 'Micro', 'Sector', 'Competitor', 'Financial')
        - sentiment: ALWAYS English ('Positive', 'Negative')
        - final_direction: Can be in {language} but should clearly indicate dimension and sentiment
        - impact_chain: In {language}
        - chain_explanation: In {language}
        - events: In {language}

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
        - Use only actual percentage returns from verified data
        - Use only real date ranges from verified data
        - Numeric data from Market Expectation Agent

        CRITICAL DIRECTION RULE:
        - **POSITIVE STARTING EVENT** (good news, positive development, growth opportunity) → MUST lead to **POSITIVE IMPACT** → Sentiment should be "Positive"
        - **NEGATIVE STARTING EVENT** (bad news, negative development, threat, problem) → MUST lead to **NEGATIVE IMPACT** → Sentiment should be "Negative"
        - **NEVER REVERSE**: If something is good news, don't turn it into negative impact. If something is bad news, don't turn it into positive impact.
        - **DIMENSION EXTRACTION**: Extract the dimension from the query context (Macro, Micro, Sector, Competitor, Financial)

        IMPORTANT:
        - Start with the user query as the first event
        - Include return rates and date ranges from Market Expectation Agent as reference
        - Follow rigorous logical progression with quantitative evidence
        - Use return rates and date ranges from market data as supporting evidence
        - Final direction MUST be FORMAT: "[Dimension] [Positive/Negative]" - Examples: "Macro Positive", "Competitor Negative", "Micro Positive"
        - Dimension MUST be one of: "Macro", "Micro", "Sector", "Competitor", "Financial"
        - Sentiment MUST be one of: "Positive", "Negative"
        - Focus on logical chain progression with market data as reference points
        - DO NOT include "estimated", "return over", "last", "past", "previous" in the output
        - CRITICAL: dimension and sentiment fields MUST be in English; other fields adapt to {language}
        
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
                "dimension": chain_result.dimension,
                "sentiment": chain_result.sentiment,
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

async def concurrent_call_generate_impact_chain_auto(
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
        return await agent.generate_impact_chain(
            ticker=ticker,
            user_question=user_question,
            verification_links=verification_links,
            verification_reasoning=verification_reasoning,
            agent_analysis_results=agent_analysis_results,
            language=language
        )
        
    except Exception as e:
        raise Exception(f"Concurrent Chain of Thought processing failed: {e}")

async def concurrent_call_generate_impact_chain_with_mermaid_auto(
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
        chain_result = await concurrent_call_generate_impact_chain_auto(
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
                "dimension": chain_result.dimension,
                "sentiment": chain_result.sentiment,
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
