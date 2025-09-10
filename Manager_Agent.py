#!/usr/bin/env python3
"""
Manager Agent - Orchestrates multiple specialized agents for comprehensive financial analysis
"""

import importlib
import asyncio
import json
import time
import yfinance as yf
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Import shared clients first
import shared_clients
importlib.reload(shared_clients)
from shared_clients import shared_clients

# Import API keys for error handling
try:
    from LLM_Call_Agent import OPENAI_API_KEY, DEEPSEEK_API_KEY
except ImportError:
    OPENAI_API_KEY = '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'
    DEEPSEEK_API_KEY = 'sk-43e9043c7ab8480393d34367f2ae997e'

# Import and reload all agents
import Market_Expectation_Agent
import Stock_Trend_Read_Agent
import Fundamental_Segmentation_Agent 
import Revenue_Segmentation_Read_Agent
import Financial_Metrics_Analyst_Agent
import Macro_Read_Agent
import Macro_Analyst_Agent
import News_Verification
import LLM_Call_Agent

importlib.reload(Market_Expectation_Agent)
importlib.reload(Stock_Trend_Read_Agent)
importlib.reload(Fundamental_Segmentation_Agent)
importlib.reload(Revenue_Segmentation_Read_Agent)
importlib.reload(Financial_Metrics_Analyst_Agent)
importlib.reload(Macro_Read_Agent)
importlib.reload(Macro_Analyst_Agent)
importlib.reload(News_Verification)
importlib.reload(LLM_Call_Agent)

from Financial_Metrics_Analyst_Agent import FinancialMetricsAnalystAgent
from Macro_Analyst_Agent import MacroAnalystAgent
from LLM_Call_Agent import LLMCallAgent

# Redis Configuration
REDIS_CONFIG = {
    'host': 'redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com',
    'port': 16376,
    'password': 'rl8242B4UItBhFzgHW5APEqZnkYoaEZv'
}

# Global manager instance to avoid re-initialization
_global_manager = None
_manager_lock = asyncio.Lock()

async def get_manager_instance():
    """Get or create a global manager instance with shared clients - THREAD SAFE"""
    global _global_manager
    
    async with _manager_lock:
        if _global_manager is None:
            print("🚀 Creating global Manager Agent instance...")
            _global_manager = ManagerAgent()
            await _global_manager.initialize_shared_clients()
            print("✅ Global Manager Agent instance created and initialized")
        else:
            print("✅ Using existing global Manager Agent instance")
    
    return _global_manager

class Manager_Agent_Result(BaseModel):
    Decision_call_market_expectation: int
    Decision_call_revenue_segmentation: int
    Decision_call_macro_analyst: int
    Decision_call_financial_metrics_analyst: int
    Decision_call_earnings_and_future: int
    query_for_market_expectation: str      
    query_for_revenue_segmentation: str   
    query_for_macro_analyst: str      
    query_for_financial_metrics_analyst: str
    query_for_earnings_and_future: str

class ManagerAgent:
    def __init__(self):
        """Initialize the Manager Agent with shared clients"""
        self.manager_agent = None
        self.structured_llm = None
    
    async def initialize_shared_clients(self):
        """Initialize shared clients for the Manager Agent"""
        # Only initialize if not already initialized
        if not shared_clients.get_status().get('initialized', False):
            print("🚀 Initializing shared clients for Manager Agent...")
            await shared_clients.initialize()
            
            # Show semaphore status after initialization
            print("\n🔒 LLM Concurrency Status:")
            status = shared_clients.get_status()
            print(f"OpenAI Semaphore: {status['openai_semaphore_value']}")
            print(f"DeepSeek Semaphore: {status['deepseek_semaphore_value']}")
            print("✅ Ready for concurrent LLM calls!")
        else:
            print("✅ Shared clients already initialized")
        
        # CRITICAL: Ensure we have a working LLM agent
        self.manager_agent = shared_clients.get_llm_agent()
        
        if self.manager_agent is None:
            raise Exception("❌ CRITICAL ERROR: LLM Call Agent is None in shared clients. Check API keys and network connection.")
        
        # CRITICAL: Ensure we have a working structured LLM
        self.structured_llm = self.manager_agent.get_structured_llm(Manager_Agent_Result)
        
        if self.structured_llm is None:
            raise Exception("❌ CRITICAL ERROR: Structured LLM is None. Check langchain packages and API keys.")
        
        print("✅ Manager Agent LLM components verified and ready")
    
    def diagnose_llm_status(self):
        """Diagnose LLM initialization status for debugging"""
        print("\n🔍 LLM DIAGNOSTIC REPORT:")
        print("=" * 50)
        
        # Check shared clients status
        status = shared_clients.get_status()
        print(f"Shared Clients Initialized: {status.get('initialized', False)}")
        print(f"LLM Call Agent Available: {shared_clients.get_llm_agent() is not None}")
        
        # Check API keys
        print(f"OpenAI API Key: {'✅ Set' if OPENAI_API_KEY else '❌ Missing'}")
        print(f"DeepSeek API Key: {'✅ Set' if DEEPSEEK_API_KEY else '❌ Missing'}")
        
        # Check manager agent
        print(f"Manager Agent: {'✅ Set' if self.manager_agent is not None else '❌ None'}")
        print(f"Structured LLM: {'✅ Set' if self.structured_llm is not None else '❌ None'}")
        
        # Test imports
        try:
            from langchain_deepseek import ChatDeepSeek
            print("LangChain DeepSeek: ✅ Available")
        except ImportError as e:
            print(f"LangChain DeepSeek: ❌ Missing - {e}")
        
        try:
            from langchain_openai import ChatOpenAI
            print("LangChain OpenAI: ✅ Available")
        except ImportError as e:
            print(f"LangChain OpenAI: ❌ Missing - {e}")
        
        print("=" * 50)
    
    async def process_manager_query(self, user_query: str, ticker: str, language: str = "English") -> Manager_Agent_Result:
        """
        Process a user query and intelligently route to appropriate agents
        """
        
        prompt = f"""
        You are a Manager Agent that investigates how events will impact the asset.

        USER QUERY: "{user_query}"
        TICKER: {ticker}

        PURPOSE: Investigate how this event will impact the asset by calling relevant agents.

        AVAILABLE AGENTS:
        1. MARKET EXPECTATION AGENT:
           - Database: Historical stock price patterns, similar events analysis
           - Purpose: Find similar historical events and their stock price impact
           - Call when: Need to understand how similar events affected stock price historically

        2. REVENUE SEGMENTATION AGENT:
           - Database: Revenue breakdown by segments, business model analysis
           - Purpose: Analyze business segment impact
           - Call when: Query involves revenue segments or business model

        3. MACRO ANALYST AGENT:
           - Database: Macroeconomic indicators, policy changes
           - Purpose: Analyze economic environment impact
           - Call when: Query involves economic factors or policies

        4. FINANCIAL METRICS ANALYST AGENT:
           - Database: Financial ratios, valuation metrics
           - Purpose: Analyze financial health and valuation impact
           - Call when: Query involves financial analysis or valuation

        5. EARNINGS AND FUTURE AGENT:
           - Database: Earnings transcripts, future development plans
           - Purpose: Analyze business strategy and future plans impact
           - Call when: Query involves earnings, innovation, or business strategy

        ROUTING RULES:
        1. **ALWAYS call Market Expectation Agent** - to find similar historical events and their stock price impact
        2. **Call 1 additional agent** - based on the main dimension of the query
        3. **Generate 1-2 sentence queries** - focused and specific
        4. **Market Expectation query** - exactly 1 sentence about similar historical events

        EXAMPLES:
        - Query: "Tariff impact on LULU"
          → Market Expectation: "Find similar tariff events and their historical stock price impact on LULU"
          → Macro Analyst: "Analyze current tariff policies and their economic impact on LULU"

        - Query: "Revenue growth drivers"
          → Market Expectation: "Find similar revenue growth events and their historical stock price impact"
          → Revenue Segmentation: "Analyze current revenue segments and growth drivers"

        OUTPUT FORMAT:
        {{
            "Decision_call_market_expectation": 1,
            "Decision_call_revenue_segmentation": 1 or 0,
            "Decision_call_macro_analyst": 1 or 0,
            "Decision_call_financial_metrics_analyst": 1 or 0,
            "Decision_call_earnings_and_future": 1 or 0,
            "query_for_market_expectation": "Find similar [event type] events and their historical stock price impact on [ticker]",
            "query_for_revenue_segmentation": "specific question or N/A",
            "query_for_macro_analyst": "specific question or N/A",
            "query_for_financial_metrics_analyst": "specific question or N/A",
            "query_for_earnings_and_future": "specific question or N/A"
        }}

        IMPORTANT: 
        - Always call Market Expectation Agent (decision = 1)
        - Call exactly 1 additional agent based on query dimension
        - Keep queries short and focused
        - Use "N/A" for agents you don't call

        please output in language: {language} for me, as you are api call that might handle different language in default
        """
        
        try:
            # Use structured output (now works properly with langchain_deepseek)
            result = self.structured_llm.invoke(prompt)
            return result
        except Exception as e:
            raise Exception(f"Manager Agent processing failed: {e}")
    
    
    def create_agent_calling_form(self, result: Manager_Agent_Result) -> Dict[str, Any]:
        """Create the agent calling form based on manager decisions"""
        
        Decision_call_market_expectation = result.Decision_call_market_expectation
        Decision_call_revenue_segmentation = result.Decision_call_revenue_segmentation
        Decision_call_macro_analyst = result.Decision_call_macro_analyst
        Decision_call_financial_metrics = result.Decision_call_financial_metrics_analyst
        Decision_call_earnings_and_future = result.Decision_call_earnings_and_future

        Market_Expectation_Agent_Query = result.query_for_market_expectation
        Revenue_Segmentation_Query = result.query_for_revenue_segmentation
        Macro_Query = result.query_for_macro_analyst
        Financial_Metrics_Query = result.query_for_financial_metrics_analyst
        Earnings_and_Future_Query = result.query_for_earnings_and_future

        Decision_List = [Decision_call_market_expectation, Decision_call_revenue_segmentation, Decision_call_macro_analyst, Decision_call_financial_metrics, Decision_call_earnings_and_future]
        Agent_List = ["Market_Expectation_Agent", "Revenue_Segmentation_Agent", "Macro_Analyst_Agent", "Financial_Metrics_Agent", "Earnings_and_Future_Agent"]
        Query_List = [Market_Expectation_Agent_Query, Revenue_Segmentation_Query, Macro_Query, Financial_Metrics_Query, Earnings_and_Future_Query]

        Agents_Calling_Form = {}
        for i in range(len(Decision_List)):
            if Decision_List[i] == 1:
                Agents_Calling_Form[Agent_List[i]] = 1
                Agents_Calling_Form[Agent_List[i] + "_Query"] = Query_List[i]

        return Agents_Calling_Form, Decision_List, Agent_List, Query_List
    
    async def call_agents_dynamically(self, Decision_List: List[int], Agent_List: List[str], Query_List: List[str], ticker: str, shared_clients=None):
        """
        Concurrently call agents based on decision flags and collect results.
        """
        print("🚀 Starting Dynamic Agent Execution (Shared Clients Optimized)")
        print("=" * 60)
        
        # Show semaphore status before execution
        if shared_clients is not None:
            print(f"🤖 Using shared clients: {'✅' if shared_clients.get_llm_agent() else '❌'}")
            status = shared_clients.get_status()
            print(f"🔒 OpenAI Semaphore: {status['openai_semaphore_value']}")
            print(f"🔒 DeepSeek Semaphore: {status['deepseek_semaphore_value']}")
            print(f"📈 Total Requests: {status['total_requests']}")
        else:
            print("⚠️ No shared clients provided - using individual connections")

        tasks, keys = [], []

        async def run_market(q):
            from Market_Expectation_Agent import MarketExpectationAgent
            if shared_clients:
                a = MarketExpectationAgent(
                    shared_clients=shared_clients
                )
            else:
                a = MarketExpectationAgent(
                    shared_clients=shared_clients,
                    redis_host=REDIS_CONFIG['host'],
                    redis_port=REDIS_CONFIG['port'],
                    redis_password=REDIS_CONFIG['password']
                )
            try:
                # Track timing
                from shared_clients import llm_tracker
                llm_tracker.stamp("Market Agent Start", "Market")
                result = await asyncio.wait_for(a.process_query(q, ticker), timeout=500)
                llm_tracker.stamp("Market Agent End", "Market")
                return result.get('stock_read_result', 'No result')
            except asyncio.TimeoutError:
                print("❌ Market Agent timed out after 400 seconds")
                return "Market Agent timed out"
            except Exception as e:
                print(f"❌ Market Agent error: {e}")
                return f"Market Agent error: {str(e)}"
            finally:
                a.close()

        async def run_revenue(q):
            from Fundamental_Segmentation_Agent import FundamentalSegmentationAgent
            if shared_clients:
                a = FundamentalSegmentationAgent(
                    shared_clients=shared_clients
                )
            else:
                a = FundamentalSegmentationAgent(
                    shared_clients=shared_clients,
                    redis_host=REDIS_CONFIG['host'],
                    redis_port=REDIS_CONFIG['port'],
                    redis_password=REDIS_CONFIG['password']
                )
            try:
                # Track timing
                from shared_clients import llm_tracker
                llm_tracker.stamp("Revenue Agent Start", "Revenue")
                result = await asyncio.wait_for(a.process_query(q, ticker), timeout=500)
                llm_tracker.stamp("Revenue Agent End", "Revenue")
                return result.get('revenue_analysis', 'No result')
            except asyncio.TimeoutError:
                print("❌ Revenue Agent timed out after 300 seconds")
                return "Revenue Agent timed out"
            except Exception as e:
                print(f"❌ Revenue Agent error: {e}")
                return f"Revenue Agent error: {str(e)}"
            finally:
                a.close()

        async def run_macro(q):
            from Macro_Analyst_Agent import MacroAnalystAgent
            import time
            if shared_clients:
                a = MacroAnalystAgent(
                    shared_clients=shared_clients,
                    user_id="default_user"
                )
            else:
                a = MacroAnalystAgent(
                    shared_clients=shared_clients,
                    redis_host=REDIS_CONFIG['host'],
                    redis_port=REDIS_CONFIG['port'],
                    redis_password=REDIS_CONFIG['password'],
                    user_id="default_user"
                )
            try:
                # Track timing
                from shared_clients import llm_tracker
                llm_tracker.stamp("Macro Agent Start", "Macro")
                result = await asyncio.wait_for(a.process_macro_query(q), timeout=500)
                llm_tracker.stamp("Macro Agent End", "Macro")
                return result.get('llm_response', 'No result')
            except asyncio.TimeoutError:
                print("❌ Macro Agent timed out after 150 seconds")
                return "Macro Agent timed out"
            except Exception as e:
                print(f"❌ Macro Agent error: {e}")
                import traceback
                traceback.print_exc()
                return f"Macro Agent error: {str(e)}"
            finally:
                if hasattr(a, 'redis_client') and a.redis_client:
                    a.redis_client.close()

        async def run_financial(q):
            from Financial_Metrics_Analyst_Agent import FinancialMetricsAnalystAgent
            import time
            if shared_clients:
                a = FinancialMetricsAnalystAgent(
                    shared_clients=shared_clients,
                    user_id="default_user",
                    task_id=f"financial_task_{int(time.time())}"
                )
            else:
                a = FinancialMetricsAnalystAgent(
                    shared_clients=shared_clients,
                    redis_host=REDIS_CONFIG['host'],
                    redis_port=REDIS_CONFIG['port'],
                    redis_password=REDIS_CONFIG['password'],
                    user_id="default_user",
                    task_id=f"financial_task_{int(time.time())}"
                )
            try:
                # Track timing
                from shared_clients import llm_tracker
                llm_tracker.stamp("Financial Agent Start", "Financial")
                result = await asyncio.wait_for(a.process_query(q, ticker), timeout=500)
                llm_tracker.stamp("Financial Agent End", "Financial")
                return result.get('llm_response', 'No result')
            except asyncio.TimeoutError:
                print("❌ Financial Agent timed out after 300 seconds")
                return "Financial Agent timed out"
            except Exception as e:
                print(f"❌ Financial Agent error: {e}")
                return f"Financial Agent error: {str(e)}"
            finally:
                a.close()

        async def run_earnings(q):
            from Earnings_and_Future_Agent import EarningsAndFutureAgent
            if shared_clients:
                a = EarningsAndFutureAgent(
                    shared_clients=shared_clients,
                    user_id="default_user"
                )
            else:
                a = EarningsAndFutureAgent(
                    shared_clients=shared_clients,
                    redis_host=REDIS_CONFIG['host'],
                    redis_port=REDIS_CONFIG['port'],
                    redis_password=REDIS_CONFIG['password'],
                    user_id="default_user"
                )
            try:
                # Track timing
                from shared_clients import llm_tracker
                llm_tracker.stamp("Earnings Agent Start", "Earnings")
                result = await asyncio.wait_for(a.process_natural_query(q, ticker), timeout=500)
                llm_tracker.stamp("Earnings Agent End", "Earnings")
                return result.get('earnings_read_result', 'No result')
            except asyncio.TimeoutError:
                print("❌ Earnings Agent timed out after 500 seconds")
                return "Earnings Agent timed out"
            except Exception as e:
                print(f"❌ Earnings Agent error: {e}")
                return f"Earnings Agent error: {str(e)}"
            finally:
                a.close()

        # Schedule all selected agents at once (fan-out)
        for decision, name, q in zip(Decision_List, Agent_List, Query_List):
            if decision != 1:
                print(f"⏭️ Skipping {name} (decision = 0)")
                continue

            print(f"✅ Scheduling {name} ...")
            print(f"📝 Query: {str(q)[:100]}...")

            if name == "Market_Expectation_Agent":
                tasks.append(asyncio.create_task(run_market(q)))
                keys.append(f"{name}_Result")
            elif name == "Revenue_Segmentation_Agent":
                tasks.append(asyncio.create_task(run_revenue(q)))
                keys.append(f"{name}_Result")
            elif name == "Macro_Analyst_Agent":
                tasks.append(asyncio.create_task(run_macro(q)))
                keys.append(f"{name}_Result")
            elif name == "Financial_Metrics_Agent":
                tasks.append(asyncio.create_task(run_financial(q)))
                keys.append(f"{name}_Result")
            elif name == "Earnings_and_Future_Agent":
                tasks.append(asyncio.create_task(run_earnings(q)))
                keys.append(f"{name}_Result")
            else:
                print(f"⚠️ Unknown agent: {name}")

        Agents_Results = {}
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)  # fan-in
            for k, r in zip(keys, results):
                if isinstance(r, Exception):
                    print(f"❌ {k} failed: {r}")
                    Agents_Results[k] = "No result"
                else:
                    print(f"✅ {k} completed")
                    Agents_Results[k] = r
        else:
            print("ℹ️ No agents scheduled.")

        print("\n" + "=" * 60)
        print("📊 Final Results Summary:")
        print("=" * 60)
        for key, value in Agents_Results.items():
            print(f"{key}: {str(value)[:200]}...")

        return Agents_Results
    
    async def run_complete_analysis(self, user_query: str, ticker: str, shared_clients=None, language: str = "English"):
        """
        Run the complete analysis pipeline from user query to final results
        """
        print("🚀 Starting Complete Manager Agent Pipeline...")
        print("=" * 60)
        
        # Step 1: Process manager query
        print("1️⃣ Processing Manager Query...")
        result = await self.process_manager_query(user_query, ticker, language)
        
        print("🤖 Manager Agent Analysis Results:")
        print("=" * 50)
        print(f"User Query: {user_query}")
        print(f"Ticker: {ticker}")
        print("\n📊 Agent Routing Decisions:")
        print(f"Market Expectation Agent: {'✅ CALL' if result.Decision_call_market_expectation else '❌ SKIP'}")
        print(f"Revenue Segmentation Agent: {'✅ CALL' if result.Decision_call_revenue_segmentation else '❌ SKIP'}")
        print(f"Macro Analyst Agent: {'✅ CALL' if result.Decision_call_macro_analyst else '❌ SKIP'}")
        print(f"Financial Metrics Agent: {'✅ CALL' if result.Decision_call_financial_metrics_analyst else '❌ SKIP'}")
        print(f"Earnings and Future Agent: {'✅ CALL' if result.Decision_call_earnings_and_future else '❌ SKIP'}")

        print("\n🔍 Generated Queries:")
        if result.Decision_call_market_expectation:
            print(f"Market: {result.query_for_market_expectation}")
        if result.Decision_call_revenue_segmentation:
            print(f"Revenue: {result.query_for_revenue_segmentation}")
        if result.Decision_call_macro_analyst:
            print(f"Macro: {result.query_for_macro_analyst}")
        if result.Decision_call_financial_metrics_analyst:
            print(f"Financial: {result.query_for_financial_metrics_analyst}")
        if result.Decision_call_earnings_and_future:
            print(f"Earnings: {result.query_for_earnings_and_future}")
        
        # Step 2: Create agent calling form
        print("\n2️⃣ Creating Agent Calling Form...")
        agents_calling_form, decision_list, agent_list, query_list = self.create_agent_calling_form(result)
        print(f"Agents to call: {agents_calling_form}")
        
        # Step 3: Call agents dynamically
        print("\n3️⃣ Calling Agents Dynamically...")
        final_results = await self.call_agents_dynamically(decision_list, agent_list, query_list, ticker)
        
        # Step 4: Create structured output
        print("\n4️⃣ Creating Structured Output...")
        agents_result = ""
        for key, value in final_results.items():
            agents_result += f"{{{key}: {str(value)[:100]}...}} "

        print(f"\n🎯 Final Structured Output:")
        print("=" * 60)
        print(agents_result)

        # Step 5: Performance monitoring
        print(f"\n📊 Results Summary:")
        print(f"Total agents called: {len(final_results)}")
        print(f"Available results: {list(final_results.keys())}")

        # Show performance stats
        from shared_clients import show_performance_stats
        show_performance_stats()
        
        return final_results, agents_result

# Performance monitoring functions
def show_performance_stats():
    """Show performance statistics"""
    from shared_clients import show_performance_stats
    show_performance_stats()

def get_llm_tracker():
    """Get LLM timing tracker"""
    from shared_clients import llm_tracker
    return llm_tracker

# Test function
async def test_manager_agent():
    """Test the Manager Agent with a sample query"""
    try:
        # Use global manager instance (fast - no re-initialization)
        manager = await get_manager_instance()
        
        # Test parameters
        user_question = "Test query for analysis"
        ticker = "TEST"
        
        # Run complete analysis
        final_results, agents_result = await manager.run_complete_analysis(user_question, ticker)
        
        print("\n✅ Manager Agent test completed successfully!")
        return final_results, agents_result
        
    except Exception as e:
        print(f"❌ Error testing Manager Agent: {e}")
        import traceback
        traceback.print_exc()
        return None, None

# ============================================================================
# CONVENIENCE FUNCTIONS (STANDALONE)
# ============================================================================

async def quick_analysis(user_query: str, ticker: str, user_id: str = "default_user", redis_config: Dict = None) -> Dict[str, Any]:
    """
    🎯 ULTRA-SIMPLE: Just input query and ticker, get multiprocessing results automatically
    
    Args:
        user_query: Your question
        ticker: Stock symbol
        user_id: User identifier to pass to all sub-agents
        redis_config: Optional Redis configuration
        
    Returns:
        Complete analysis from all relevant agents with multiprocessing
    """
    try:
        # Use global manager instance (fast - no re-initialization)
        manager = await get_manager_instance()
        
        # Run complete analysis
        final_results, agents_result = await manager.run_complete_analysis(user_query, ticker)
        
        # Create structured result
        complete_result = {
            "user_query": user_query,
            "ticker": ticker,
            "user_id": user_id,
            "agent_results": final_results,
            "agents_result": agents_result,
            "execution_summary": {
                "total_agents_executed": len(final_results),
                "successful_executions": len([r for r in final_results.values() if not str(r).startswith("Error")]),
                "failed_executions": len([r for r in final_results.values() if str(r).startswith("Error")])
            }
        }
        
        return complete_result
        
    except Exception as e:
        print(f"❌ Error in quick_analysis: {e}")
        raise Exception(f"Manager Agent analysis failed: {e}")

def get_manager_result(user_id: str, redis_config: Dict = None) -> Dict[str, Any]:
    """
    Convenience function to retrieve stored Manager Agent result
    
    Args:
        user_id: User identifier
        redis_config: Optional Redis configuration
        
    Returns:
        Stored result data or None if not found
    """
    try:
        # For now, return a placeholder since we're not storing results in Redis
        # You can implement Redis storage if needed
        return {
            "user_id": user_id,
            "status": "no_stored_result",
            "message": "Results are not currently stored in Redis"
        }
    except Exception as e:
        print(f"❌ Error retrieving manager result: {e}")
        return None

def get_manager_progress(user_id: str, redis_config: Dict = None) -> Dict[str, Any]:
    """
    Convenience function to retrieve current Manager Agent progress
    
    Args:
        user_id: User identifier
        redis_config: Optional Redis configuration
        
    Returns:
        Current progress data or None if not found
    """
    try:
        # For now, return a placeholder since we're not storing results in Redis
        # You can implement Redis progress tracking if needed
        return {
            "user_id": user_id,
            "status": "no_progress_tracking",
            "message": "Progress is not currently tracked in Redis"
        }
    except Exception as e:
        print(f"❌ Error retrieving manager progress: {e}")
        return None

# Additional convenience functions for backward compatibility
async def analyze_with_multiprocessing(user_query: str, ticker: str, redis_config: Dict = None, user_id: str = "default_user") -> Dict[str, Any]:
    """
    🚀 MAIN FUNCTION: Complete analysis with AUTOMATIC MULTIPROCESSING
    
    This function does EVERYTHING automatically:
    1. Analyzes your query
    2. Routes to appropriate agents  
    3. Runs ALL agents in parallel
    4. Returns combined results
    
    Args:
        user_query: Your question
        ticker: Stock symbol
        redis_config: Optional Redis config
        user_id: User identifier to pass to all sub-agents
        
    Returns:
        Complete results from all sub-agents
    """
    return await quick_analysis(user_query, ticker, user_id, redis_config)

async def process_manager_query(user_query: str, ticker: str, language: str = "English") -> Manager_Agent_Result:
    """
    Process a user query and intelligently route to appropriate agents
    This function matches the notebook version exactly
    """
    try:
        # Use global manager instance (fast - no re-initialization)
        manager = await get_manager_instance()
        
        # Process the query
        result = await manager.process_manager_query(user_query, ticker, language)
        return result
        
    except Exception as e:
        print(f"❌ Error in process_manager_query: {e}")
        return None

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_manager_agent())

# ============================================================================
# CONCURRENT PROCESSING FUNCTIONS (NEW)
# ============================================================================

async def concurrent_call_quick_analysis(user_query: str, ticker: str, user_id: str = "default_user", 
                                       total_queries: List[str] = None, query_index: int = 0, 
                                       redis_config: Dict = None) -> Manager_Agent_Result:
    """
    Enhanced quick analysis with context awareness for concurrent processing
    """
    try:
        # Use global manager instance (fast - no re-initialization)
        manager = await get_manager_instance()
        
        print(f"🚀 Starting Concurrent Manager Agent Pipeline (Query {query_index + 1}/{len(total_queries) if total_queries else 1})")
        print("=" * 60)
        
        # Add context to the prompt
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
- Be unique and specialized in your agent selection
- Provide different perspective from other queries
"""
        
        # Create enhanced prompt with context
        prompt = f"""
        You are an expert financial analyst specializing in intelligent agent routing for investment analysis.

        TASK: Analyze the user query and determine which specialized agents to call for comprehensive analysis.

        {context_info}

        USER QUERY: {user_query}
        TICKER: {ticker}

        AVAILABLE AGENTS:
        1. Market Expectation Agent: Analyzes historical price patterns, market sentiment, and price impact under similar events
        2. Revenue Segmentation Agent: Analyzes revenue streams, business segments, and growth drivers
        3. Macro Analyst Agent: Analyzes macroeconomic factors, interest rates, and sector trends
        4. Financial Metrics Agent: Analyzes valuation ratios, financial health, and metrics
        5. Earnings and Future Agent: Analyzes product development, innovation strategies, business plans, and future development roadmap

        ROUTING LOGIC:
        - Query mentions revenue/growth → Call: Revenue + Financial
        - Query mentions price/market → Call: Market + Financial
        - Query mentions macro/economic → Call: Macro + Financial
        - Query mentions valuation/ratios → Call: Financial + Market
        - Query mentions competition/regulatory → Call: Market + Revenue
        - Query mentions earnings/guidance → Call: Earnings + Financial
        - Query mentions future/development → Call: Earnings + Revenue
        - Query mentions product development/innovation → Call: Earnings + Revenue
        - Query mentions business plan/strategy → Call: Earnings + Financial
        - Query mentions segment/business → Call: Revenue + Financial
        - Query mentions interest rates → Call: Macro + Financial
        - Query mentions market sentiment → Call: Market + Macro
        - Query mentions financial health → Call: Financial + Revenue
        - Query mentions earnings transcript → Call: Earnings + Market

        EXAMPLES:
        - Query: "Revenue growth of 20%" 
          → Call: Revenue (growth drivers), Financial (impact on metrics)
        
        - Query: "Credit scoring segment surge" 
          → Call: Revenue (segment analysis), Financial (impact on metrics)
        
        - Query: "Interest rate impact" 
          → Call: Macro (economic factors), Financial (sensitivity)
        
        - Query: "Historical price patterns" 
          → Call: Market (trend analysis), Financial (valuation context)
        
        - Query: "Revenue breakdown by segment" 
          → Call: Revenue (segment analysis), Market (price impact)
        
        - Query: "P/E ratio and valuation" 
          → Call: Financial (valuation metrics), Market (price context)
        
        - Query: "Product development roadmap" 
          → Call: Earnings (innovation strategy), Revenue (growth impact)
        
        - Query: "Business plan and future strategy" 
          → Call: Earnings (strategic initiatives), Financial (financial impact)
        
        - Query: "Innovation and R&D investment" 
          → Call: Earnings (development plans), Revenue (growth potential)
        
        OUTPUT FORMAT:
        Return a JSON object with exactly these fields:
        {{
            "Decision_call_market_expectation": 1 or 0,
            "Decision_call_revenue_segmentation": 1 or 0,
            "Decision_call_macro_analyst": 1 or 0,
            "Decision_call_financial_metrics_analyst": 1 or 0,
            "Decision_call_earnings_and_future": 1 or 0,
            "query_for_market_expectation": "specific focused question or N/A",
            "query_for_revenue_segmentation": "specific focused question or N/A",
            "query_for_macro_analyst": "specific focused question or N/A",
            "query_for_financial_metrics_analyst": "specific focused question or N/A",
            "query_for_earnings_and_future": "specific focused question or N/A"
        }}
        
        IMPORTANT: 
        - Only return the JSON object, no other text
        - Use "N/A" for agents you don't call (decision = 0)
        - Make questions specific and actionable (1 sentence max)
        - Focus on the 2 most relevant aspects of the user query
        - CRITICAL: For ANY query, call 2 agents minimum (notice, Market Expectation will return price impact under any events)
        - SPECIALIZATION: Choose agents that provide unique perspective from other queries
        """
        
        # Use structured output with enhanced prompt
        result = manager.structured_llm.invoke(prompt)
        return result
        
    except Exception as e:
        raise Exception(f"Concurrent Manager Agent processing failed: {e}")

async def concurrent_call_quick_analysis_auto(ticker: str, user_id: str = "default_user", 
                                             total_queries: List[str] = None, query_index: int = 0, 
                                             redis_config: Dict = None) -> Dict[str, Any]:
    """
    Enhanced quick analysis with automatic query assignment from total_queries list
    """
    try:
        # Automatically get the query from total_queries based on query_index
        if not total_queries or query_index >= len(total_queries):
            raise Exception(f"Invalid query_index {query_index} for total_queries length {len(total_queries) if total_queries else 0}")
        
        user_query = total_queries[query_index]
        
        print(f"🚀 Starting Concurrent Manager Agent Pipeline (Query {query_index + 1}/{len(total_queries)})")
        print(f"📝 Assigned Query: {user_query[:50]}...")
        print("=" * 60)
        
        # Use the existing quick_analysis function with the assigned query
        result = await quick_analysis(
            user_query=user_query,
            ticker=ticker,
            user_id=user_id,
            redis_config=redis_config
        )
        
        return result
        
    except Exception as e:
        raise Exception(f"Concurrent Manager Agent processing failed: {e}")

async def concurrent_call_quick_analysis_full_auto(ticker: str, user_id: str = "default_user", 
                                                 total_queries: List[str] = None, query_index: int = 0, 
                                                 redis_config: Dict = None) -> Dict[str, Any]:
    """
    Full concurrent analysis pipeline with automatic query assignment
    """
    try:
        # Use global manager instance (fast - no re-initialization)
        manager = await get_manager_instance()
        
        # Automatically get the query from total_queries based on query_index
        if not total_queries or query_index >= len(total_queries):
            raise Exception(f"Invalid query_index {query_index} for total_queries length {len(total_queries) if total_queries else 0}")
        
        user_query = total_queries[query_index]
        
        print(f"🚀 Starting Complete Concurrent Manager Agent Pipeline (Query {query_index + 1}/{len(total_queries)})")
        print(f"📝 Assigned Query: {user_query[:50]}...")
        print("=" * 60)
        
        # Step 1: Process manager query with context
        print("1️⃣ Processing Manager Query with Context...")
        manager_result = await concurrent_call_quick_analysis(user_query, ticker, user_id, total_queries, query_index, redis_config)
        
        # Step 2: Create agent calling form
        print("2️⃣ Creating Agent Calling Form...")
        agents_form, decision_list, agent_list, query_list = manager.create_agent_calling_form(manager_result)
        print(f"Agents to call: {agents_form}")
        
        # Step 3: Call agents dynamically
        print("3️⃣ Calling Agents Dynamically...")
        agent_results = await manager.call_agents_dynamically(decision_list, agent_list, query_list, ticker, shared_clients)
        
        # Step 4: Create structured output
        print("4️⃣ Creating Structured Output...")
        agents_result = ""
        for key, value in agent_results.items():
            agents_result += f"{{{key}: {str(value)[:100]}...}} "

        print(f"\n🎯 Final Structured Output:")
        print("=" * 60)
        print(agents_result)
        
        return {
            "manager_analysis": manager_result,
            "agent_results": agent_results,
            "final_output": agents_result,
            "assigned_query": user_query,
            "context": {
                "total_queries_count": len(total_queries) if total_queries else 1,
                "query_index": query_index,
                "specialization_required": True
            }
        }
        
    except Exception as e:
        print(f"❌ Error in concurrent_call_quick_analysis_full_auto: {e}")
        return None
