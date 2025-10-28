import asyncio
import json
from typing import Dict, Any
from pydantic import BaseModel, Field

# Import shared clients
import shared_clients
from shared_clients import shared_clients

# Define the Pydantic model
class ChainOfThoughtConclusionResult(BaseModel):
    short_term_impact: str = Field(description="Detailed analysis of short-term impact (50 words with clear safe or not safe in current position price)")
    long_term_outlook: str = Field(description="Detailed analysis of long-term outlook (50 words with clear safe or not safe in current position price)")
    Dynamic_Rating: str = Field(description="Short-term Risk/Reward VS Long-term Risk/Reward (ex: Short term: Risk High, Reward Low, Long term: Risk Low, Reward High)")
    Catalyst: str = Field(description="From all u have read and analyst what id the three things that chanage (in the chains), then the whole story change (50 words)")
    short_term_percentage: str = Field(description="Short-term percentage impact (format: 'XX%')")
    long_term_percentage: str = Field(description="Long-term percentage impact (format: 'XX%')")

class ChainOfThoughtConclusionAgent:
    def __init__(self):
        """Initialize the Chain of Thought Conclusion Agent"""
        self.llm_agent = None
        self.structured_llm = None
        
        # Initialize LLM agent from shared clients
        self.llm_agent = shared_clients.get_llm_agent()
        
        if self.llm_agent is None:
            raise Exception("❌ CRITICAL ERROR: LLM Call Agent is None in shared clients. Check API keys and network connection.")
        
        # Create structured LLM (same as Manager Agent)
        self.structured_llm = self.llm_agent.get_structured_llm(ChainOfThoughtConclusionResult)
    
    async def analyze_impact(self, business_logic: str, chain_of_thought: str) -> Dict[str, Any]:
        """
        Analyze short-term vs long-term impact based on business logic and chain of thought
        
        Args:
            business_logic: The business logic/moat analysis
            chain_of_thought: The current sell/buy chain of thought result
            
        Returns:
            Dictionary with analysis results
        """
        
        prompt = f"""
        You are an expert financial analyst specializing in short-term vs long-term impact analysis.

        TASK: Analyze the impact on the company based on business logic (moat) and current sell/buy chain of thought.

        BUSINESS LOGIC (MOAT): {business_logic}

        CHAIN OF THOUGHT RESULT: {chain_of_thought}

        ANALYSIS FRAMEWORK:
        1. **SHORT-TERM IMPACT ANALYSIS**:
           - Identify immediate challenges, troubles, or potential bubbles
           - Assess market sentiment and short-term headwinds
           - Evaluate temporary vs structural issues
           - Consider cyclical vs secular factors
           - Extract percentage impact from chain of thought data

        2. **LONG-TERM OUTLOOK ANALYSIS**:
           - Evaluate company's ability to overcome short-term troubles or maintain the business sustainability (success)
           - Assess competitive advantages and moat sustainability
           - Analyze strategic positioning for long-term success
           - Consider fundamental business model strength
           - Extract percentage impact from chain of thought data

        3. **DYNAMIC RATING ANALYSIS**:
           - Assess short-term risk vs reward
           - Assess long-term risk vs reward
           - Compare short-term vs long-term perspectives

        4. **CATALYST IDENTIFICATION**:
           - Identify the three key things that could change the whole story
           - Focus on factors that would significantly alter the chain of thought

        5. **PERCENTAGE EXTRACTION**:
           - Extract quantitative percentage impacts from the chain of thought
           - Look for specific percentage numbers mentioned in the analysis
           - Provide clean percentage outputs for short-term and long-term

        OUTPUT REQUIREMENTS:
        - Be specific and data-driven
        - Distinguish between temporary and permanent factors
        - Provide clear investment implications
        - Use professional financial analysis language
        - Keep responses concise but comprehensive
        - Extract actual percentage numbers from the input data
        - DO NOT GUESS percentages - must reference actual numbers from chain of thought

        Return your analysis in the following JSON format:
        {{
            "short_term_impact": "Detailed analysis of short-term impact (50 words with clear safe or not safe in current position price)",
            "long_term_outlook": "Detailed analysis of long-term outlook (50 words with clear safe or not safe in current position price)", 
            "Dynamic_Rating": "Short-term Risk/Reward VS Long-term Risk/Reward (ex: Short term: Risk High, Reward Low, Long term: Risk Low, Reward High)",
            "Catalyst": "From all u have read and analyst what id the three things that chanage (in the chains), then the whole story change (50 words)",
            "short_term_percentage": "XX%",
            "long_term_percentage": "XX%"
        }}
        """
        
        try:
            # Use structured LLM invoke method (same as Manager Agent)
            result = self.structured_llm.invoke(prompt)
            return result.dict()  # Convert Pydantic model to dict
            
        except Exception as e:
            raise Exception(f"Chain of Thought Conclusion analysis failed: {e}")

# Convenience function
async def analyze_chain_conclusion(business_logic: str, chain_of_thought: str) -> Dict[str, Any]:
    """
    Convenience function to analyze chain of thought conclusion
    
    Args:
        business_logic: The business logic/moat analysis
        chain_of_thought: The current sell/buy chain of thought result
        
    Returns:
        Dictionary with analysis results
    """
    try:
        agent = ChainOfThoughtConclusionAgent()
        result = await agent.analyze_impact(business_logic, chain_of_thought)
        return result
    except Exception as e:
        print(f"❌ Error in analyze_chain_conclusion: {e}")
        return {
            "short_term_impact": f"Analysis failed: {e}",
            "long_term_outlook": "Analysis failed",
            "Dynamic_Rating": "Analysis failed",
            "Catalyst": "Analysis failed",
            "short_term_percentage": "0%",
            "long_term_percentage": "0%"
        }

# Test function
async def test_chain_conclusion():
    """Test the Chain of Thought Conclusion Agent"""
    business_logic = "Strong brand moat, premium pricing power, loyal customer base"
    chain_of_thought = "Short-term: Supply chain issues causing margin pressure. Long-term: International expansion driving growth."
    
    result = await analyze_chain_conclusion(business_logic, chain_of_thought)
    print("Chain of Thought Conclusion Result:")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(test_chain_conclusion())
