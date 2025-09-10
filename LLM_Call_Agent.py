#!/usr/bin/env python3
"""
LLM Call Agent
Centralized agent for making calls to various LLM providers (OpenAI, DeepSeek).
"""

# 🔑 CENTRALIZED API KEYS - All agents import from here
OPENAI_API_KEY = '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'
DEEPSEEK_API_KEY = 'sk-43e9043c7ab8480393d34367f2ae997e'

import sys
import os
from pathlib import Path

# Fix import paths for multiprocessing in Streamlit
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Any, Optional, Union
import requests
from dataclasses import dataclass
from pathlib import Path
import re

# Import OpenAI and DeepSeek clients
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: openai not available. Install with: pip install openai")

try:
    from openai import OpenAI as DeepSeekClient
    DEEPSEEK_AVAILABLE = True
except ImportError:
    DEEPSEEK_AVAILABLE = False
    print("Warning: openai not available for DeepSeek. Install with: pip install openai")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('llm_agent.log')
    ]
)

class LLMCallAgent:
    """
    Centralized LLM API calling agent for stock trend analysis.
    """
    
    def __init__(self, 
                 openai_api_key: str = None,
                 deepseek_api_key: str = None,
                 default_provider: str = "deepseek",
                 default_model: str = "deepseek-chat"):
        """
        Initialize the LLM Call Agent.
        
        Args:
            openai_api_key (str): OpenAI API key (if None, will try to get from environment variable)
            deepseek_api_key (str): DeepSeek API key (if None, will try to get from environment variable)
            default_provider (str): Default LLM provider ("openai" or "deepseek")
            default_model (str): Default model to use
        """
        # Get API keys from centralized keys or environment variables
        if not openai_api_key:
            openai_api_key = os.getenv('OPENAI_API_KEY') or OPENAI_API_KEY
            if openai_api_key:
                logging.info("📥 Using OpenAI API key from centralized keys")
            else:
                logging.warning("⚠️ No OpenAI API key provided or found")
        
        if not deepseek_api_key:
            deepseek_api_key = os.getenv('DEEPSEEK_API_KEY') or DEEPSEEK_API_KEY
            if deepseek_api_key:
                logging.info("📥 Using DeepSeek API key from centralized keys")
            else:
                logging.warning("⚠️ No DeepSeek API key provided or found")
        
        self.openai_api_key = openai_api_key
        self.deepseek_api_key = deepseek_api_key
        self.default_provider = default_provider
        self.default_model = default_model
        
        # Initialize clients
        self.openai_client = None
        self.deepseek_client = None
        
        if openai_api_key:
            self.openai_client = OpenAI(api_key=openai_api_key)
            logging.info("✅ OpenAI client initialized")
        
        if deepseek_api_key:
            self.deepseek_client = OpenAI(api_key=deepseek_api_key, base_url="https://api.deepseek.com")
            logging.info("✅ DeepSeek client initialized")
        
        logging.info(f"🤖 LLM Call Agent initialized")
        logging.info(f"   - Default provider: {default_provider}")
        logging.info(f"   - Default model: {default_model}")
        logging.info(f"   - OpenAI: {'Enabled' if openai_api_key else 'Disabled'}")
        logging.info(f"   - DeepSeek: {'Enabled' if deepseek_api_key else 'Disabled'}")
    
    def call_openai(self, 
                    prompt: str, 
                    system_message: str = "You are a knowledgeable financial analyst assistant.",
                    model: str = "gpt-4o",
                    max_tokens: int = 4000,
                    temperature: float = 0.3,
                    functions: List[Dict] = None,
                    function_call: str = "auto") -> str:
        """
        Make a call to OpenAI API.
        
        Args:
            prompt (str): User prompt
            system_message (str): System message
            model (str): Model to use
            max_tokens (int): Maximum tokens
            temperature (float): Temperature for creativity
            functions (List[Dict]): Function definitions for function calling
            function_call (str): Function call mode
            
        Returns:
            str: LLM response
        """
        if not self.openai_client:
            return "❌ OpenAI client not initialized. Please provide OpenAI API key."
        
        try:
            logging.info(f"🔗 Calling OpenAI API")
            logging.info(f"   - Model: {model}")
            logging.info(f"   - Max tokens: {max_tokens}")
            logging.info(f"   - Temperature: {temperature}")
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ]
            
            kwargs = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            if functions:
                kwargs["functions"] = functions
                kwargs["function_call"] = function_call
                logging.info(f"   - Function calling: {len(functions)} functions")
            
            response = self.openai_client.chat.completions.create(**kwargs)
            
            logging.info(f"✅ OpenAI API call successful")
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"❌ OpenAI API call failed: {e}")
            return f"❌ OpenAI API Error: {str(e)}"
    
    def call_deepseek(self, 
                      prompt: str, 
                      system_message: str = "You are a knowledgeable financial analyst assistant.",
                      model: str = "deepseek-chat",
                      max_tokens: int = 4000,
                      temperature: float = 0.3) -> str:
        """
        Make a call to DeepSeek API.
        
        Args:
            prompt (str): User prompt
            system_message (str): System message
            model (str): Model to use
            max_tokens (int): Maximum tokens
            temperature (float): Temperature for creativity
            
        Returns:
            str: LLM response
        """
        if not self.deepseek_client:
            return "❌ DeepSeek client not initialized. Please provide DeepSeek API key."
        
        try:
            logging.info(f"🔗 Calling DeepSeek API")
            logging.info(f"   - Model: {model}")
            logging.info(f"   - Max tokens: {max_tokens}")
            logging.info(f"   - Temperature: {temperature}")
            
            response = self.deepseek_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                stream=False
            )
            
            logging.info(f"✅ DeepSeek API call successful")
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"❌ DeepSeek API call failed: {e}")
            return f"❌ DeepSeek API Error: {str(e)}"
    
    def call_llm(self, 
                 prompt: str, 
                 provider: str = None,
                 system_message: str = "You are a knowledgeable financial analyst assistant.",
                 model: str = None,
                 max_tokens: int = 4000,
                 temperature: float = 0.3,
                 functions: List[Dict] = None,
                 function_call: str = "auto") -> str:
        """
        Make a call to the specified LLM provider.
        
        Args:
            prompt (str): User prompt
            provider (str): LLM provider ("openai" or "deepseek")
            system_message (str): System message
            model (str): Model to use
            max_tokens (int): Maximum tokens
            temperature (float): Temperature for creativity
            functions (List[Dict]): Function definitions for function calling
            function_call (str): Function call mode
            
        Returns:
            str: LLM response
        """
        # Use default provider if not specified
        if not provider:
            provider = self.default_provider
        
        # Use default model if not specified
        if not model:
            model = self.default_model
        
        logging.info(f"🤖 Making LLM call")
        logging.info(f"   - Provider: {provider}")
        logging.info(f"   - Model: {model}")
        
        if provider.lower() == "openai":
            return self.call_openai(
                prompt=prompt,
                system_message=system_message,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                functions=functions,
                function_call=function_call
            )
        elif provider.lower() == "deepseek":
            return self.call_deepseek(
                prompt=prompt,
                system_message=system_message,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            return f"❌ Unknown provider: {provider}. Use 'openai' or 'deepseek'."
    
    def call_with_function_calling(self, 
                                  prompt: str, 
                                  functions: List[Dict],
                                  provider: str = "deepseek",
                                  system_message: str = "You are a knowledgeable financial analyst assistant.",
                                  model: str = "deepseek-chat") -> Dict:
        """
        Make a call with function calling support.
        
        Args:
            prompt (str): User prompt
            functions (List[Dict]): Function definitions
            provider (str): LLM provider
            system_message (str): System message
            model (str): Model to use
            
        Returns:
            Dict: Response with function call information
        """
        if provider.lower() != "openai":
            return {"error": "Function calling is only supported with OpenAI"}
        
        try:
            logging.info(f"🔧 Making function calling request")
            logging.info(f"   - Provider: {provider}")
            logging.info(f"   - Functions: {len(functions)}")
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                functions=functions,
                function_call="auto",
                max_tokens=1500,
                temperature=0.3
            )
            
            result = {
                "content": response.choices[0].message.content,
                "function_call": response.choices[0].message.get("function_call"),
                "success": True
            }
            
            if result["function_call"]:
                logging.info(f"✅ Function call detected: {result['function_call']['name']}")
            
            return result
            
        except Exception as e:
            logging.error(f"❌ Function calling failed: {e}")
            return {"error": str(e), "success": False}
    
    def call_with_follow_up(self, 
                           initial_prompt: str, 
                           function_result: Dict,
                           provider: str = "deepseek",
                           system_message: str = "You are a knowledgeable financial analyst assistant.",
                           model: str = "deepseek-chat") -> str:
        """
        Make a follow-up call after function execution.
        
        Args:
            initial_prompt (str): Original user prompt
            function_result (Dict): Result from function execution
            provider (str): LLM provider
            system_message (str): System message
            model (str): Model to use
            
        Returns:
            str: Final LLM response
        """
        try:
            logging.info(f"🔄 Making follow-up call")
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": initial_prompt},
                {"role": "function", "name": function_result.get("function_name", "unknown"), 
                 "content": json.dumps(function_result.get("result", {}))},
                {"role": "assistant", "content": function_result.get("assistant_message", "")}
            ]
            
            response = self.openai_client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1200,
                temperature=0.3
            )
            
            logging.info(f"✅ Follow-up call successful")
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"❌ Follow-up call failed: {e}")
            return f"❌ Follow-up Error: {str(e)}"
    
    def test_connection(self, provider: str = None) -> Dict:
        """
        Test the connection to the specified LLM provider.
        
        Args:
            provider (str): Provider to test
            
        Returns:
            Dict: Test results
        """
        if not provider:
            provider = self.default_provider
        
        test_prompt = "Hello, this is a connection test. Please respond with 'Connection successful' if you can see this message."
        
        try:
            logging.info(f"🧪 Testing connection to {provider}")
            
            if provider.lower() == "openai":
                if not self.openai_client:
                    return {"success": False, "error": "OpenAI client not initialized"}
                
                response = self.call_openai(test_prompt, max_tokens=50)
                success = "Connection successful" in response or "❌" not in response
                
            elif provider.lower() == "deepseek":
                if not self.deepseek_client:
                    return {"success": False, "error": "DeepSeek client not initialized"}
                
                response = self.call_deepseek(test_prompt, max_tokens=50)
                success = "Connection successful" in response or "❌" not in response
                
            else:
                return {"success": False, "error": f"Unknown provider: {provider}"}
            
            return {
                "success": success,
                "provider": provider,
                "response": response,
                "message": "Connection successful" if success else "Connection failed"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "provider": provider}
    
    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers."""
        providers = []
        if self.openai_client:
            providers.append("openai")
        if self.deepseek_client:
            providers.append("deepseek")
        return providers
    
    def get_structured_llm(self, pydantic_model=None, provider: str = None):
        """
        Get a structured LLM client for Pydantic model output.
        
        Args:
            pydantic_model: Pydantic model class for structured output
            provider (str): LLM provider ("openai" or "deepseek")
            
        Returns:
            Structured LLM client with Pydantic output capability
        """
        try:
            # Determine provider
            if provider is None:
                provider = self.default_provider
            
            if provider == "openai":
                if not self.openai_api_key:
                    raise ValueError("OpenAI API key not available")
                
                # Import OpenAI components
                from langchain_openai import ChatOpenAI
                
                llm = ChatOpenAI(
                    api_key=self.openai_api_key,
                    model="gpt-4o-mini",  # Default OpenAI model
                    temperature=0,
                    timeout=60
                )
                
            elif provider == "deepseek":
                if not self.deepseek_api_key:
                    raise ValueError("DeepSeek API key not available")
                
                # Import DeepSeek components directly
                from langchain_deepseek import ChatDeepSeek
                
                llm = ChatDeepSeek(
                    model="deepseek-chat",
                    temperature=0,
                    api_key=self.deepseek_api_key
                )
            else:
                raise ValueError(f"Unsupported provider: {provider}")
            
            # Add structured output if Pydantic model provided
            if pydantic_model:
                try:
                    return llm.with_structured_output(pydantic_model)
                except Exception as e:
                    logging.warning(f"⚠️ Structured output not available, returning basic LLM: {e}")
                    return llm
            
            return llm
            
        except ImportError as e:
            logging.error(f"❌ LangChain not available: {e}")
            logging.error("Install with: pip install langchain-openai langchain-deepseek")
            raise ImportError("LangChain required for structured output. Install with: pip install langchain-openai langchain-deepseek")
        except Exception as e:
            logging.error(f"❌ Failed to create structured LLM: {e}")
            raise

    def switch_provider(self, new_provider: str):
        """
        Switch the default LLM provider.
        
        Args:
            new_provider (str): New provider ("openai" or "deepseek")
        """
        if new_provider.lower() not in ["openai", "deepseek"]:
            raise ValueError("Provider must be 'openai' or 'deepseek'")
        
        self.default_provider = new_provider.lower()
        logging.info(f"🔄 Switched default provider to: {self.default_provider}")
        
        # Update default model based on provider
        if new_provider.lower() == "openai":
            self.default_model = "gpt-4o-mini"
        else:
            self.default_model = "deepseek-chat"
        
        logging.info(f"🔄 Updated default model to: {self.default_model}")

    def get_provider_status(self):
        """
        Get the status of all providers.
        
        Returns:
            Dict: Status of each provider
        """
        return {
            "openai": {
                "available": bool(self.openai_api_key),
                "client_initialized": bool(self.openai_client),
                "api_key": "✅ Available" if self.openai_api_key else "❌ Missing"
            },
            "deepseek": {
                "available": bool(self.deepseek_api_key),
                "client_initialized": bool(self.deepseek_client),
                "api_key": "✅ Available" if self.deepseek_api_key else "❌ Missing"
            },
            "current_default": self.default_provider,
            "current_model": self.default_model
        }
    
    def extract_ticker_and_info_from_query(self, query: str) -> Dict:
        """
        Extract ticker symbol and information type from natural language query.
        Uses function calling for maximum precision and reliability.
        
        Args:
            query (str): Natural language query
            
        Returns:
            Dict: {"ticker": str, "info_type": str, "json_path": str}
        """
        logging.info(f"🔍 LLM extracting ticker and info from query: '{query}'")
        
        prompt = f"""
Analyze this stock query and extract the ticker symbol and information type:

Query: "{query}"

Available info_types:
- current_trends: Ongoing market trends and patterns
- historical_trends: Past trends and historical analysis  
- price_distribution: Price analysis and distribution
- risk_metrics: Volatility and risk measurements
- trend_comparison: Comparison of different trends
- statistics: Statistical analysis of trends
- all_data: Complete stock information

Available json_paths:
- current_trends: Access current trend data
- historical_trends: Access historical trend data  
- all: Access all available data

Examples:
- "What is AAPL's current trend?" → ticker: "AAPL", info_type: "current_trends", json_path: "current_trends"
- "Show me TSLA's historical trends" → ticker: "TSLA", info_type: "historical_trends", json_path: "historical_trends"
- "What's the price distribution for NVDA?" → ticker: "NVDA", info_type: "price_distribution", json_path: "current_trends"

Return a JSON response with this exact format:
{{
    "ticker": "AAPL",
    "info_type": "current_trends",
    "json_path": "current_trends",
    "confidence": 0.9
}}

Return ONLY the JSON, nothing else:"""

        try:
            # Simple direct API call
            logging.info(f"🔄 Using direct LLM call for {self.default_provider}")
            response = self.call_llm(
                prompt=prompt,
                system_message="You are a stock query analyzer. Extract ticker and information type, return JSON only.",
                max_tokens=200,
                temperature=0.1
            )
            
            # Parse JSON response (handle markdown code blocks)
            import json
            import re
            
            # Clean the response - remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]  # Remove ```
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            
            cleaned_response = cleaned_response.strip()
            
            result = json.loads(cleaned_response)
            
            if result.get("ticker") and result.get("info_type") and result.get("json_path"):
                confidence = result.get("confidence", 0.8)
                logging.info(f"✅ LLM extracted: ticker='{result['ticker']}', info_type='{result['info_type']}', json_path='{result['json_path']}', confidence={confidence}")
                return result
            else:
                logging.error(f"❌ LLM response missing required fields: {result}")
                raise Exception("LLM response missing required fields")
                
        except Exception as e:
            logging.error(f"❌ LLM extraction failed: {e}")
            logging.info("🔄 Falling back to regex extraction...")
            return self._extract_ticker_fallback(query)
    
    def _extract_ticker_fallback(self, query: str) -> Dict:
        """Fallback method using regex when function calling fails"""
        import re
        
        # Extract ticker with regex
        ticker_patterns = [
            r'for\s+([A-Z]{1,5})\b',
            r'([A-Z]{1,5})\s+(?:stock|trend|price)',
            r'\b([A-Z]{1,5})\b'
        ]
        
        ticker = None
        for pattern in ticker_patterns:
            match = re.search(pattern, query.upper())
            if match:
                ticker = match.group(1)
                break
        
        # Determine info type from query
        info_type = "all_data"
        if "current" in query.lower():
            info_type = "current_trends"
        elif "historical" in query.lower():
            info_type = "historical_trends"
        elif "price" in query.lower():
            info_type = "price_distribution"
        elif "risk" in query.lower():
            info_type = "risk_metrics"
        
        json_path = "current_trends" if info_type in ["current_trends", "price_distribution", "risk_metrics"] else "historical_trends"
        if info_type == "all_data":
            json_path = "all"
        
        return {
            "ticker": ticker,
            "info_type": info_type,
            "json_path": json_path,
            "confidence": 0.3  # Lower confidence for regex fallback
        }
    
    def analyze_stock_query_with_llm(self, query: str, stock_data: Dict) -> str:
        """
        Analyze stock data and answer user query using LLM.
        
        Args:
            query (str): User's natural language query
            stock_data (Dict): Stock data from database
            
        Returns:
            str: LLM-generated analysis
        """
        logging.info(f"🤖 LLM analyzing stock query: '{query}'")
        
        # Create a focused prompt for stock analysis
        ticker = stock_data.get('ticker', 'Unknown')
        current_trends = stock_data.get('current_trends', {})
        historical_trends = stock_data.get('historical_trends', {})
        
        prompt = f"""
Analyze this stock data and answer the user's query.

USER QUERY: "{query}"
TICKER: {ticker}

STOCK DATA:
- Current Trends: {len(current_trends)} segments
- Historical Trends: {len(historical_trends)} segments
- Last Updated: {stock_data.get('stored_at', 'Unknown')}

CURRENT TRENDS DATA:
{json.dumps(current_trends, indent=2)[:2000]}...

HISTORICAL TRENDS DATA:
{json.dumps(historical_trends, indent=2)[:2000]}...

Provide a comprehensive analysis that:
1. Directly answers the user's question
2. Uses specific data from the stock trends
3. Includes numerical evidence (returns, slopes, estimates)
4. Explains the current market position
5. Provides actionable insights

Focus on the user's specific query and provide evidence-based analysis."""

        try:
            response = self.call_llm(
                prompt=prompt,
                system_message="You are a specialized stock trend analyst. Provide evidence-based analysis using the provided data.",
                max_tokens=1000,
                temperature=0.2
            )
            
            logging.info(f"✅ LLM analysis completed for {ticker}")
            return response
            
        except Exception as e:
            logging.error(f"❌ LLM analysis failed: {e}")
            return f"❌ Error analyzing stock data: {str(e)}"


def main():
    """Main function for testing the LLM Call Agent."""
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM Call Agent - Test Interface')
    parser.add_argument('--prompt', default="Hello, how are you?", help='Test prompt')
    parser.add_argument('--provider', choices=['openai', 'deepseek'], help='LLM provider')
    parser.add_argument('--model', help='Model to use')
    parser.add_argument('--test-connection', action='store_true', help='Test connection')
    parser.add_argument('--status', action='store_true', help='Show provider status')
    
    args = parser.parse_args()
    
    # Initialize with API keys from centralized keys or environment
    openai_key = os.getenv('OPENAI_API_KEY') or OPENAI_API_KEY
    deepseek_key = os.getenv('DEEPSEEK_API_KEY') or DEEPSEEK_API_KEY
    
    if not openai_key and not deepseek_key:
        print("⚠️ No API keys found in centralized keys or environment variables.")
        return
    
    agent = LLMCallAgent(
        openai_api_key=openai_key,
        deepseek_api_key=deepseek_key,
        default_provider=args.provider or "deepseek"
    )
    
    if args.status:
        status = agent.get_provider_status()
        print("📊 Provider Status:")
        for provider, state in status.items():
            print(f"   - {provider}: {state}")
        return
    
    if args.test_connection:
        result = agent.test_connection(args.provider)
        if result["success"]:
            print(f"✅ {result['message']} for {result['provider']}")
        else:
            print(f"❌ Connection failed: {result['error']}")
        return
    
    # Make a test call
    response = agent.call_llm(
        prompt=args.prompt,
        provider=args.provider,
        model=args.model
    )
    
    print(f"\n🤖 LLM Response:\n{response}")


if __name__ == "__main__":
    # Example usage
    # python LLM_Call_Agent.py --prompt "What is the current trend for AAPL?" --provider deepseek
    # python LLM_Call_Agent.py --test-connection --provider deepseek
    # python LLM_Call_Agent.py --status
    
    main() 