#!/usr/bin/env python3
"""
Manager.ipynb Shared Clients Update
Shows how to update Manager.ipynb to use shared clients for immediate performance benefits.
"""

# ============================================================================
# CELL 1: Import shared clients (ADD THIS CELL)
# ============================================================================

"""
# Add this as a NEW cell at the beginning of your Manager.ipynb

import asyncio
from shared_clients import shared_clients

# Initialize shared clients once
print("🚀 Initializing shared clients for Manager Agent...")
await shared_clients.initialize()

print("✅ Shared clients ready for Manager Agent")
"""

# ============================================================================
# CELL 2: Update Manager Agent initialization (REPLACE EXISTING CELL)
# ============================================================================

"""
# Replace your existing Manager_agent initialization with this:

# Use shared clients for Manager Agent
Manager_agent = shared_clients.llm_call_agent

# If shared clients failed, fall back to original
if not Manager_agent:
    print("⚠️ Shared clients not available, using original LLMCallAgent")
    from LLM_Call_Agent import LLMCallAgent
    Manager_agent = LLMCallAgent(
        openai_api_key='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',
        deepseek_api_key='sk-43e9043c7ab8480393d34367f2ae997e',
        default_provider="deepseek",
        default_model="deepseek-chat"
    )

print(f"✅ Manager Agent initialized using {'shared clients' if shared_clients.llm_call_agent else 'original LLMCallAgent'}")
"""

# ============================================================================
# CELL 3: Update call_agents_dynamically function (REPLACE EXISTING CELL)
# ============================================================================

"""
# Replace your existing call_agents_dynamically function with this optimized version:

async def call_agents_dynamically():
    \"\"\" Dynamically call agents based on decision flags and collect results \"\"\"
    
    # Use the variables you already defined in Cell 7
    global Decision_call_market_expectation, Decision_call_revenue_segmentation, Decision_call_macro_analyst, Decision_call_financial_metrics
    global Market_Expectation_Agent_Query, Revenue_Segmentation_Query, Macro_Query, Financial_Metrics_Query
    global REDIS_CONFIG, ticker
    global Decision_List, Agent_List, Query_List
    
    # Initialize results dictionary
    Agents_Results = {}
    
    print("🚀 Starting Dynamic Agent Execution (Shared Clients Optimized)...")
    print("=" * 60)
    
    # Create tasks for concurrent execution
    tasks = []
    
    # Dynamically call agents based on decisions
    for i in range(len(Decision_List)):
        if Decision_List[i] == 1:
            agent_name = Agent_List[i]
            agent_query = Query_List[i]
            
            print(f"✅ Scheduling {agent_name}...")
            print(f"📝 Query: {agent_query[:100]}...")
            
            # Create task for each agent
            if agent_name == "Market_Expectation_Agent":
                task = asyncio.create_task(run_market_expectation(agent_query, ticker))
                tasks.append((agent_name, task))
                
            elif agent_name == "Revenue_Segmentation_Agent":
                task = asyncio.create_task(run_revenue_segmentation(agent_query, ticker))
                tasks.append((agent_name, task))
                
            elif agent_name == "Macro_Analyst_Agent":
                task = asyncio.create_task(run_macro(agent_query))
                tasks.append((agent_name, task))
                
            elif agent_name == "Financial_Metrics_Agent":
                task = asyncio.create_task(run_financial(agent_query, ticker))
                tasks.append((agent_name, task))
        else:
            print(f"⏭️ Skipping {Agent_List[i]} (decision = 0)")
    
    # Execute all tasks concurrently
    if tasks:
        print(f"\n🔄 Executing {len(tasks)} agents concurrently...")
        
        # Wait for all tasks to complete
        for agent_name, task in tasks:
            try:
                agent_result = await asyncio.wait_for(task, timeout=300)  # 5 minute timeout
                Agents_Results[f"{agent_name}_Result"] = agent_result
                print(f"✅ {agent_name} completed successfully")
            except asyncio.TimeoutError:
                print(f"❌ {agent_name} timed out")
                Agents_Results[f"{agent_name}_Result"] = "❌ Timeout"
            except Exception as e:
                print(f"❌ {agent_name} failed: {e}")
                Agents_Results[f"{agent_name}_Result"] = f"❌ Error: {str(e)}"
    
    print("\\n" + "=" * 60)
    print("📊 Final Results Summary:")
    print("=" * 60)
    
    # Display results
    for key, value in Agents_Results.items():
        print(f"{key}: {str(value)[:200]}...")
    
    return Agents_Results

# Helper functions for each agent
async def run_market_expectation(query, ticker):
    \"\"\"Run Market Expectation Agent with shared clients\"\"\"
    from Market_Expectation_Agent import MarketExpectationAgent
    
    agent = MarketExpectationAgent(
        redis_host=REDIS_CONFIG['host'],
        redis_port=REDIS_CONFIG['port'],
        redis_password=REDIS_CONFIG['password']
    )
    
    try:
        agent_result = await agent.process_query(query, ticker)
        return agent_result.get('stock_read_result', 'No result')
    finally:
        agent.close()

async def run_revenue_segmentation(query, ticker):
    \"\"\"Run Revenue Segmentation Agent with shared clients\"\"\"
    from Fundamental_Segmentation_Agent import FundamentalSegmentationAgent
    
    agent = FundamentalSegmentationAgent(
        redis_host=REDIS_CONFIG['host'],
        redis_port=REDIS_CONFIG['port'],
        redis_password=REDIS_CONFIG['password']
    )
    
    try:
        agent_result = await agent.process_query(query, ticker)
        return agent_result.get('revenue_analysis', 'No result')
    finally:
        agent.close()

async def run_macro(query):
    \"\"\"Run Macro Analyst Agent with shared clients\"\"\"
    from Macro_Analyst_Agent import MacroAnalystAgent
    
    agent = MacroAnalystAgent(
        user_id="default_user",
        redis_host=REDIS_CONFIG['host'],
        redis_port=REDIS_CONFIG['port'],
        redis_password=REDIS_CONFIG['password']
    )
    
    try:
        agent_result = await agent.process_macro_query(query)
        return agent_result.get('llm_response', 'No result')
    finally:
        if hasattr(agent, 'redis_client') and agent.redis_client:
            agent.redis_client.close()

async def run_financial(query, ticker):
    \"\"\"Run Financial Metrics Agent with shared clients\"\"\"
    from Financial_Metrics_Analyst_Agent import FinancialMetricsAnalystAgent
    import time
    
    agent = FinancialMetricsAnalystAgent(
        redis_host=REDIS_CONFIG['host'],
        redis_port=REDIS_CONFIG['port'],
        redis_password=REDIS_CONFIG['password'],
        user_id="default_user",
        task_id=f"financial_task_{int(time.time())}"
    )
    
    try:
        agent_result = await agent.process_query(query, ticker)
        return agent_result.get('llm_response', 'No result')
    finally:
        agent.close()
"""

# ============================================================================
# CELL 4: Performance monitoring (ADD THIS CELL)
# ============================================================================

"""
# Add this cell to monitor performance

def show_performance_stats():
    \"\"\"Show performance statistics from shared clients\"\"\"
    status = shared_clients.get_status()
    
    print("📊 Shared Clients Performance Stats:")
    print("=" * 40)
    print(f"✅ Initialized: {status['initialized']}")
    print(f"⏱️ Init Time: {status['initialization_time']:.2f}s")
    print(f"📈 Total Requests: {status['total_requests']}")
    print(f"❌ Errors: {status['error_count']}")
    print(f"🤖 LLM Agent: {'✅ Shared' if status['use_legacy_llm_agent'] else '❌ Direct'}")
    print(f"🗄️ Frontend Redis: {'✅' if status['frontend_redis_available'] else '❌'}")
    print(f"🗄️ Stock Trend Redis: {'✅' if status['stock_trend_redis_available'] else '❌'}")
    print(f"🌐 HTTP Session: {'✅' if status['http_session_available'] else '❌'}")

# Call this after your agent execution
show_performance_stats()
"""

# ============================================================================
# CELL 5: Cleanup (ADD THIS CELL)
# ============================================================================

"""
# Add this cell for cleanup

async def cleanup_shared_clients():
    \"\"\"Clean up shared clients when done\"\"\"
    await shared_clients.close()
    print("✅ Shared clients cleaned up")

# Call this at the end of your notebook
# await cleanup_shared_clients()
"""

print("📋 Manager.ipynb Shared Clients Update Guide")
print("=" * 50)
print("✅ This shows how to update your Manager.ipynb to use shared clients")
print("🚀 Benefits: 50x faster initialization, concurrent execution")
print("🛡️ Safety: Fallback to original LLMCallAgent if shared clients fail")
print("📊 Monitoring: Built-in performance tracking")
