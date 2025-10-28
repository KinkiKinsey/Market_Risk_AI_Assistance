#!/usr/bin/env python3
"""
SMART Update Pool Function
Directly checks each agent's database for update information and triggers updates only when needed.
"""

import sys
import asyncio
import time
import json
from typing import Dict, Any, List
from datetime import datetime, timedelta

# Add current directory to path
sys.path.append('.')

async def update_pool(ticker: str, agents_to_warm_up: List[str] = None) -> Dict[str, Any]:
    """
    SMART Data Pool Function - Directly checks specified agents' database for update information
    
    Logic:
    1. Directly access specified agents' Redis database
    2. Check update timestamps against thresholds
    3. Only trigger updates for agents that need them
    4. Run updates concurrently for agents that need them
    
    Args:
        ticker (str): Stock ticker symbol (e.g., "TSLA", "AAPL")
        agents_to_warm_up (List[str], optional): List of agent module names to warm up.
            If None, warms up all agents. Valid options:
            - "Market_Expectation_Agent"
            - "Sector_Analyst_Agent" 
            - "Financial_Metrics_Agent"
            - "Macro_Analyst_Agent"
            - "Earning_and_Future_Agent"
            - "Fundamental_Segmentation_Agent"
        
    Returns:
        Dict[str, Any]: Results from specified agents with execution details
    """
    print(f"🧠 Starting SMART Data Pool retrieval for {ticker}...")
    print("=" * 60)
    
    # Define all available agents
    all_agents = {
        "Market_Expectation_Agent": "market_expectation",  # REQUIRED for Quant Impact
        "Sector_Analyst_Agent": "sector_analysis", 
        "Financial_Metrics_Agent": "financial_metrics",
        "Macro_Analyst_Agent": "macro_analysis",
        "Earning_and_Future_Agent": "earnings_future",
        "Fundamental_Segmentation_Agent": "revenue_segmentation"
    }
    
    # Determine which agents to check
    if agents_to_warm_up is None:
        # Warm up all agents
        agents_to_check = list(all_agents.values())
        print(f"🔍 Checking ALL agents for update status...")
    else:
        # Validate and map agent names
        agents_to_check = []
        invalid_agents = []
        
        for agent_name in agents_to_warm_up:
            if agent_name in all_agents:
                agents_to_check.append(all_agents[agent_name])
                print(f"✅ Added {agent_name} to warm-up list")
            else:
                invalid_agents.append(agent_name)
        
        if invalid_agents:
            print(f"❌ Invalid agent names: {invalid_agents}")
            print(f"Valid options: {list(all_agents.keys())}")
            return {
                "status": "error",
                "error": f"Invalid agent names: {invalid_agents}",
                "valid_agents": list(all_agents.keys())
            }
        
        print(f"🔍 Checking {len(agents_to_check)} specified agents for update status...")
    
    start_time = time.time()
    results = {}
    
    try:
        # Initialize shared clients
        from shared_clients import shared_clients
        await shared_clients.initialize()
        
        # Get Redis connections
        frontend_redis = shared_clients.get_frontend_redis()
        stock_trend_redis = shared_clients.get_stock_trend_redis()
        
        # Check specified agents' update status
        update_status = await check_specified_agents_update_status(ticker, frontend_redis, stock_trend_redis, agents_to_check)
        
        print("\n📊 Update Status Summary:")
        print("=" * 40)
        for agent, status in update_status.items():
            print(f"{agent}: {'🔄 UPDATE NEEDED' if status['needs_update'] else '✅ FRESH'}")
            if status['needs_update']:
                print(f"   Reason: {status['reason']}")
            else:
                print(f"   Last update: {status['last_update']}")
        
        # Only update agents that need updates
        agents_to_update = [agent for agent, status in update_status.items() if status['needs_update']]
        
        if not agents_to_update:
            print("\n✅ All specified agents have fresh data - no updates needed!")
            return {
                "status": "all_fresh",
                "execution_time": time.time() - start_time,
                "message": "All specified agents have fresh data",
                "results": {},
                "agents_checked": agents_to_check
            }
        
        print(f"\n🚀 Updating {len(agents_to_update)} agents that need fresh data...")
        
        # Create tasks only for agents that need updates
        tasks = []
        
        # Import agents dynamically based on what needs updating
        if "revenue_segmentation" in agents_to_update:
            from Source_File.Agent_Folder.Sub_Agent_Folder.Fundamental_Segmentation_Agent.Revenue_Segmentation_Read_Agent import RevenueSegmentationAnalystAgent
            async def update_revenue():
                print(f"💰 [SMART] Updating Revenue Segmentation for {ticker}...")
                agent = RevenueSegmentationAnalystAgent(shared_clients=shared_clients)
                result = await agent.process_natural_query(f"Get latest revenue data for {ticker}", ticker)
                print(f"✅ Revenue Segmentation updated for {ticker}")
                return "revenue_segmentation", result
            tasks.append(asyncio.create_task(update_revenue()))
        
        if "financial_metrics" in agents_to_update:
            from Source_File.Agent_Folder.Sub_Agent_Folder.Financial_Metrics_Agent.Financial_Metrics_Read_Agent import FinancialMetricsReadAgent
            async def update_financial():
                print(f"📊 [SMART] Updating Financial Metrics for {ticker}...")
                agent = FinancialMetricsReadAgent(shared_clients=shared_clients)
                result = await agent.get_financial_metrics_data(ticker)
                print(f"✅ Financial Metrics updated for {ticker}")
                return "financial_metrics", result
            tasks.append(asyncio.create_task(update_financial()))
        
        if "macro_analysis" in agents_to_update:
            from Source_File.Agent_Folder.Sub_Agent_Folder.Macro_Analyst_Agent.Macro_Read_Agent import MacroReadAgent
            async def update_macro():
                print(f"🌍 [SMART] Updating Macro Analysis for {ticker}...")
                agent = MacroReadAgent(shared_clients=shared_clients)
                # Use read_macro_data() which has built-in freshness check and update logic
                result = await agent.read_macro_data()
                print(f"✅ Macro Analysis updated for {ticker}")
                return "macro_analysis", result
            tasks.append(asyncio.create_task(update_macro()))
        
        if "earnings_future" in agents_to_update:
            from Source_File.Agent_Folder.Sub_Agent_Folder.Earning_and_Future_Agent.Earnings_and_Future_Read_Agent import EarningsAndFutureReadAgent
            async def update_earnings():
                print(f"📈 [SMART] Updating Earnings and Future for {ticker}...")
                agent = EarningsAndFutureReadAgent(shared_clients=shared_clients)
                result = await agent.process_natural_query(f"Get latest earnings data for {ticker}", ticker, force_update=False)
                print(f"✅ Earnings and Future updated for {ticker}")
                return "earnings_future", result
            tasks.append(asyncio.create_task(update_earnings()))
        
        if "market_expectation" in agents_to_update:
            from Source_File.Agent_Folder.Sub_Agent_Folder.Market_Expectation_Agent.Stock_Trend_Read_Agent import StockTrendAnalystAgent
            async def update_market_expectation():
                print(f"📈 [SMART] Updating Market Expectation for {ticker}...")
                agent = StockTrendAnalystAgent(shared_clients=shared_clients)
                result = await agent.process_natural_query(f"Get latest stock trend analysis for {ticker}", ticker, force_update=True)
                print(f"✅ Market Expectation updated for {ticker}")
                return "market_expectation", result
            tasks.append(asyncio.create_task(update_market_expectation()))
        
        if "sector_analysis" in agents_to_update:
            from Source_File.Agent_Folder.Sub_Agent_Folder.Sector_Analyst_Agent.Sector_Analyst_Read_Agent import SectorAnalystReadAgent
            async def update_sector():
                print(f"🏭 [SMART] Updating Sector Analysis for {ticker}...")
                agent = SectorAnalystReadAgent(shared_clients=shared_clients)
                result = await agent.process_sector_query(ticker)
                print(f"✅ Sector Analysis updated for {ticker}")
                return "sector_analysis", result
            tasks.append(asyncio.create_task(update_sector()))
        
        # Execute only the necessary updates concurrently
        print(f"\n🚀 Executing {len(tasks)} SMART updates concurrently...")
        update_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for i, result in enumerate(update_results):
            if isinstance(result, Exception):
                print(f"❌ Update task {i+1} failed: {result}")
            else:
                key, value = result
                results[key] = value
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        print("\n" + "=" * 60)
        print(f"🎉 SMART Data Pool retrieval completed for {ticker}")
        print(f"⏱️ Total execution time: {execution_time:.2f} seconds")
        print(f"📊 Updated {len(results)} agents")
        print(f"🚀 Performance: {execution_time/len(tasks):.2f}s per update" if tasks else "🚀 Performance: No updates needed")
        print("=" * 60)
        
        return {
            "status": "completed",
            "execution_time": execution_time,
            "updated_agents": len(results),
            "agents_checked": agents_to_check,
            "agents_updated": agents_to_update,
            "results": results,
            "performance": {
                "total_time": execution_time,
                "avg_per_update": execution_time / len(tasks) if tasks else 0,
                "optimization": "smart_checking_enabled"
            }
        }
        
    except Exception as e:
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"❌ Critical error in smart data pool: {e}")
        return {
            "status": "failed",
            "execution_time": execution_time,
            "error": str(e)
        }

async def check_specified_agents_update_status(ticker: str, frontend_redis, stock_trend_redis, agents_to_check: List[str]) -> Dict[str, Dict]:
    """
    Check update status for specified agents using EXACT same logic as Read Agents
    
    Args:
        ticker: Stock ticker symbol
        frontend_redis: Frontend Redis connection
        stock_trend_redis: Stock trend Redis connection
        agents_to_check: List of agent names to check
    
    Returns:
        Dict: Update status for each specified agent
    """
    update_status = {}
    
    # Check only specified agents
    if "market_expectation" in agents_to_check:
        # 1. Market Expectation Agent - EXACT COPY from Stock_Trend_Read_Agent.py lines 699-770
        try:
            # Direct Redis access using the same logic as DB Agent
            redis_key = f"Stock_Trend_INFOS:{ticker.upper()}_trends"
            data_str = await stock_trend_redis.get(redis_key)
            
            if data_str:
                stock_data = json.loads(data_str)
                # Check data freshness - EXACT COPY from Read Agent
                stored_at = stock_data.get('stored_at')
                if stored_at:
                    if isinstance(stored_at, str):
                        stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                    else:
                        stored_datetime = stored_at
                    
                    current_time = datetime.now()
                    hours_since_update = (current_time - stored_datetime).total_seconds() / 3600
                    
                    if hours_since_update < 24:  # 24-hour threshold from Read Agent
                        update_status["market_expectation"] = {
                            "needs_update": False,
                            "last_update": stored_at,
                            "hours_since_update": hours_since_update,
                            "reason": f"Data is fresh (updated {hours_since_update:.1f} hours ago)"
                        }
                    else:
                        update_status["market_expectation"] = {
                            "needs_update": True,
                            "last_update": stored_at,
                            "hours_since_update": hours_since_update,
                            "reason": f"Data is {hours_since_update:.1f} hours old (threshold: 24 hours)"
                        }
                else:
                    update_status["market_expectation"] = {
                        "needs_update": True,
                        "last_update": "Unknown",
                        "reason": "Data found but timestamp unknown"
                    }
            else:
                update_status["market_expectation"] = {
                    "needs_update": True,
                    "last_update": "No data",
                    "reason": f"No data found for ticker {ticker}"
                }
        except Exception as e:
            update_status["market_expectation"] = {
                "needs_update": True,
                "last_update": "Error",
                "reason": f"Error checking database: {e}"
            }
    
    if "financial_metrics" in agents_to_check:
        # 2. Financial Metrics Agent - 15-day update logic
        try:
            # Use same Redis key as Read Agent
            data = await stock_trend_redis.get(f"Financial_Metrics_INFOS:{ticker.upper()}")
            if data:
                existing_data = json.loads(data)
                metadata = existing_data.get('metadata', {})
                last_update = metadata.get('latest_update_time')  # EXACT field from Read Agent
                
                if not last_update:
                    update_status["financial_metrics"] = {
                        "needs_update": True,
                        "last_update": "Unknown",
                        "reason": "No update time found in metadata"
                    }
                else:
                    # 15-day update logic
                    current_time = datetime.now()
                    update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                    current_date = current_time.date()
                    update_date = update_time.date()
                    
                    days_since_update = (current_date - update_date).days
                    
                    if days_since_update < 15:
                        # Data is fresh (within 15 days)
                        update_status["financial_metrics"] = {
                            "needs_update": False,
                            "last_update": last_update,
                            "days_since_update": days_since_update,
                            "reason": f"Data is fresh ({days_since_update} days old, threshold: 15 days)"
                        }
                    else:
                        # Data is stale (15+ days old)
                        update_status["financial_metrics"] = {
                            "needs_update": True,
                            "last_update": last_update,
                            "days_since_update": days_since_update,
                            "reason": f"Data is {days_since_update} days old (threshold: 15 days)"
                        }
            else:
                update_status["financial_metrics"] = {
                    "needs_update": True,
                    "last_update": "No data",
                    "reason": "No data found for this ticker"
                }
        except Exception as e:
            update_status["financial_metrics"] = {
                "needs_update": True,
                "last_update": "Error",
                "reason": f"Error checking status: {str(e)}"
            }
    
    if "earnings_future" in agents_to_check:
        # 3. Earnings and Future Agent - 30-day update logic
        try:
            # Direct Redis access using the same logic as DB Agent
            redis_key = f"Earnings_and_Future_INFOS:{ticker.upper()}_earnings_and_future"
            data_str = await stock_trend_redis.get(redis_key)
            
            if data_str:
                earnings_data = json.loads(data_str)
                # Check data freshness - 30-day logic
                stored_at = earnings_data.get('stored_at')  # EXACT field from Read Agent
                if stored_at:
                    if isinstance(stored_at, str):
                        stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                    else:
                        stored_datetime = stored_at
                    
                    current_time = datetime.now()
                    current_date = current_time.date()
                    update_date = stored_datetime.date()
                    days_since_update = (current_date - update_date).days
                    
                    if days_since_update < 30:  # 30-day threshold
                        update_status["earnings_future"] = {
                            "needs_update": False,
                            "last_update": stored_at,
                            "days_since_update": days_since_update,
                            "reason": f"Earnings data is fresh ({days_since_update} days old, threshold: 30 days)"
                        }
                    else:
                        update_status["earnings_future"] = {
                            "needs_update": True,
                            "last_update": stored_at,
                            "days_since_update": days_since_update,
                            "reason": f"Earnings data is {days_since_update} days old (threshold: 30 days)"
                        }
                else:
                    update_status["earnings_future"] = {
                        "needs_update": True,
                        "last_update": "Unknown",
                        "reason": "Earnings data found but timestamp unknown"
                    }
            else:
                update_status["earnings_future"] = {
                    "needs_update": True,
                    "last_update": "No data",
                    "reason": f"No earnings data found for ticker {ticker}"
                }
        except Exception as e:
            update_status["earnings_future"] = {
                "needs_update": True,
                "last_update": "Error",
                "reason": f"Error checking database: {e}"
            }
    
    if "macro_analysis" in agents_to_check:
        # 4. Macro Analyst Agent - EXACT COPY from Macro_Read_Agent.py lines 102-221
        try:
            # Check Macro_Analyst file - EXACT COPY from Read Agent
            analyst_data = await stock_trend_redis.get("Macro_INFOS:Macro_Analyst")
            
            if not analyst_data:
                update_status["macro_analysis"] = {
                    "needs_update": True,
                    "last_update": "No data",
                    "reason": "No macro analyst data found"
                }
            else:
                # Parse the data and check metadata - EXACT COPY from Read Agent
                parsed_data = json.loads(analyst_data)
                
                if 'meta_data' not in parsed_data:
                    update_status["macro_analysis"] = {
                        "needs_update": True,
                        "last_update": "Unknown",
                        "reason": "No metadata found in macro analyst data"
                    }
                else:
                    metadata = parsed_data['meta_data']
                    last_update_time = metadata.get('last_update_time')  # EXACT field from Read Agent
                    
                    if not last_update_time:
                        update_status["macro_analysis"] = {
                            "needs_update": True,
                            "last_update": "Unknown",
                            "reason": "No update timestamp found"
                        }
                    else:
                        # Check weekly update rule - EXACT COPY from Read Agent
                        current_time = datetime.now()
                        last_update = datetime.fromisoformat(last_update_time)
                        days_since_update = (current_time - last_update).days
                        
                        weekly_threshold = 7  # 7 days from Read Agent
                        is_fresh = days_since_update <= weekly_threshold
                        
                        if is_fresh:
                            update_status["macro_analysis"] = {
                                "needs_update": False,
                                "last_update": last_update_time,
                                "days_since_update": days_since_update,
                                "reason": f'Data is fresh for {weekly_threshold - days_since_update} more days'
                            }
                        else:
                            update_status["macro_analysis"] = {
                                "needs_update": True,
                                "last_update": last_update_time,
                                "days_since_update": days_since_update,
                                "reason": f'Data is {days_since_update - weekly_threshold} days overdue for update'
                            }
        except Exception as e:
            update_status["macro_analysis"] = {
                "needs_update": True,
                "last_update": "Error",
                "reason": f"Error checking data freshness: {str(e)}"
            }
    
    if "sector_analysis" in agents_to_check:
        # 5. Sector Analyst Agent - EXACT COPY from Sector_Analyst_Read_Agent.py lines 142-185
        try:
            # Get data from Redis - EXACT COPY from Read Agent
            data_str = await stock_trend_redis.get(f"Sector_Analyst_INFOS:{ticker.upper()}_sector_analysis")
            
            if not data_str:
                update_status["sector_analysis"] = {
                    "needs_update": True,
                    "last_update": "No data",
                    "reason": f"No data found for {ticker}"
                }
            else:
                data = json.loads(data_str)
                # Check last update time - EXACT COPY from Read Agent
                last_update_str = data.get('last_update', '')  # EXACT field from Read Agent
                if not last_update_str:
                    update_status["sector_analysis"] = {
                        "needs_update": True,
                        "last_update": "Unknown",
                        "reason": f"No last update time for {ticker}"
                    }
                else:
                    try:
                        last_update = datetime.fromisoformat(last_update_str.replace('Z', '+00:00'))
                        days_since_update = (datetime.now() - last_update.replace(tzinfo=None)).days
                        
                        monthly_threshold = 30  # 30 days from Read Agent
                        is_fresh = days_since_update < monthly_threshold
                        
                        if is_fresh:
                            update_status["sector_analysis"] = {
                                "needs_update": False,
                                "last_update": last_update_str,
                                "days_since_update": days_since_update,
                                "reason": f"Data is fresh for {monthly_threshold - days_since_update} more days"
                            }
                        else:
                            update_status["sector_analysis"] = {
                                "needs_update": True,
                                "last_update": last_update_str,
                                "days_since_update": days_since_update,
                                "reason": f"Data is {days_since_update} days old (threshold: {monthly_threshold} days)"
                            }
                    except Exception as e:
                        update_status["sector_analysis"] = {
                            "needs_update": True,
                            "last_update": "Unknown",
                            "reason": f"Error parsing last update time for {ticker}: {e}"
                        }
        except Exception as e:
            update_status["sector_analysis"] = {
                "needs_update": True,
                "last_update": "Error",
                "reason": f"Error checking data freshness for {ticker}: {e}"
            }
    
    if "revenue_segmentation" in agents_to_check:
        # 6. Revenue Segmentation Agent - EXACT COPY from Revenue_Segmentation_Read_Agent.py lines 387-435
        try:
            # Create Redis key - use same format as DB Agent
            redis_key = f"Revenue_Segmentation_INFOS:{ticker.upper()}_revenue_segmentation"
            
            # Get data from Redis
            stored_data = await stock_trend_redis.get(redis_key)
            
            if stored_data:
                data = json.loads(stored_data)
                
                # PRIORITY 1: Check earnings date first (if exists)
                metadata = data.get('metadata', {})
                next_earnings_date = metadata.get('next_earnings_date')
                
                if next_earnings_date:
                    try:
                        # Check if earnings date has passed
                        current_date = datetime.now().date()
                        earnings_date = datetime.strptime(next_earnings_date, '%Y-%m-%d').date()
                        
                        if current_date >= earnings_date:
                            # Earnings date passed - need fresh data
                            update_status["revenue_segmentation"] = {
                                "needs_update": True,
                                "last_update": next_earnings_date,
                                "reason": f"Earnings date {next_earnings_date} has passed"
                            }
                        else:
                            # Earnings date hasn't passed - data is fresh
                            update_status["revenue_segmentation"] = {
                                "needs_update": False,
                                "last_update": next_earnings_date,
                                "reason": f"Earnings date {next_earnings_date} hasn't passed yet"
                            }
                    except (ValueError, TypeError) as e:
                        # Invalid earnings date format - fall back to stored_at
                        stored_at = data.get('stored_at')
                        if stored_at:
                            stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                            hours_since_update = (datetime.now() - stored_datetime).total_seconds() / 3600
                            
                            if hours_since_update < 24:
                                update_status["revenue_segmentation"] = {
                                    "needs_update": False,
                                    "last_update": stored_at,
                                    "hours_since_update": hours_since_update,
                                    "reason": f"Data is fresh (updated {hours_since_update:.1f} hours ago, earnings date invalid)"
                                }
                            else:
                                update_status["revenue_segmentation"] = {
                                    "needs_update": True,
                                    "last_update": stored_at,
                                    "hours_since_update": hours_since_update,
                                    "reason": f"Data is {hours_since_update:.1f} hours old (threshold: 24 hours, earnings date invalid)"
                                }
                        else:
                            update_status["revenue_segmentation"] = {
                                "needs_update": True,
                                "last_update": "Unknown",
                                "reason": "No earnings date and no timestamp found"
                            }
                else:
                    # PRIORITY 2: No earnings date - check stored_at timestamp (24-hour fallback)
                    stored_at = data.get('stored_at')
                    if stored_at:
                        stored_datetime = datetime.fromisoformat(stored_at.replace('Z', '+00:00'))
                        hours_since_update = (datetime.now() - stored_datetime).total_seconds() / 3600
                        
                        if hours_since_update < 24:  # 24-hour threshold
                            update_status["revenue_segmentation"] = {
                                "needs_update": False,
                                "last_update": stored_at,
                                "hours_since_update": hours_since_update,
                                "reason": f"Data is fresh (updated {hours_since_update:.1f} hours ago, no earnings date)"
                            }
                        else:
                            update_status["revenue_segmentation"] = {
                                "needs_update": True,
                                "last_update": stored_at,
                                "hours_since_update": hours_since_update,
                                "reason": f"Data is {hours_since_update:.1f} hours old (threshold: 24 hours, no earnings date)"
                            }
                    else:
                        update_status["revenue_segmentation"] = {
                            "needs_update": True,
                            "last_update": "Unknown",
                            "reason": "No earnings date and no timestamp found"
                        }
            else:
                update_status["revenue_segmentation"] = {
                    "needs_update": True,
                    "last_update": "No data",
                    "reason": f"No revenue segmentation data found for {ticker}"
                }
        except Exception as e:
            update_status["revenue_segmentation"] = {
                "needs_update": True,
                "last_update": "Error",
                "reason": f"Error retrieving data for {ticker}: {e}"
            }
    
    return update_status