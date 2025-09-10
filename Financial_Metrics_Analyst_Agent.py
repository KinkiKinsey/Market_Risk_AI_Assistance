#!/usr/bin/env python3
"""
Financial Metrics Analyst Agent
Frontend layer agent that takes User ID, Query, and Ticker, then bypasses the query directly to the Read Agent.
Outputs LLM analysis and financial metrics data for frontend display.
"""

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
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Union, Tuple
import redis
from dataclasses import dataclass
from pathlib import Path
import asyncio
import re

# Import existing agents
from Financial_Metrics_Read_Agent import FinancialMetricsReadAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('financial_metrics_analyst.log')
    ]
)

@dataclass
class FinancialAnalysisResult:
    """Data class for financial analysis result information."""
    ticker: str
    query: str
    financial_metrics: Dict
    llm_analysis: str
    data_summary: Dict
    metadata: Dict
    analysis_timestamp: str

class FinancialMetricsAnalystAgent:
    """
    Financial Metrics Analyst Agent - Frontend layer that processes user queries and calls Read Agent.
    """
    
    def __init__(self, progress_context=None, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None, 
                 collection_name: str = "Financial_Metrics_INFOS", openai_api_key: str = None,
                 user_id: str = None, task_id: str = None):
        """
        Initialize Financial Metrics Analyst Agent with progress tracking.
        
        Args:
            progress_context: Context for progress updates
            redis_host: Redis host for progress updates
            redis_port: Redis port
            redis_username: Redis username
            redis_password: Redis password
            collection_name: Collection name for database
            openai_api_key: OpenAI API key
            user_id: User ID for progress tracking
            task_id: Task ID for progress tracking
        """
        self.progress_context = progress_context
        self.user_id = user_id or "default_user"
        self.task_id = task_id or f"task_{int(datetime.now().timestamp())}"
        
        # Frontend Redis Database (Separate from financial metrics database)
        # Using StackExchange.Redis connection details
        self.frontend_redis = None
        self.frontend_redis_host = "redis-16204.fcrce180.us-east-1-1.ec2.redns.redis-cloud.com"
        self.frontend_redis_port = 16204
        self.frontend_redis_username = "default"
        self.frontend_redis_password = "9rHiMKl63iYK9ja4qja6ZjnamuixS4UG"
        
        # Use shared Redis connection if available
        if shared_clients:
            self.frontend_redis = shared_clients.get_frontend_redis()
            logging.info("✅ Using shared frontend Redis connection")
        else:
            try:
                self.frontend_redis = redis.Redis(
                    host=self.frontend_redis_host,
                    port=self.frontend_redis_port,
                    username=self.frontend_redis_username,
                    password=self.frontend_redis_password,
                    decode_responses=True
                )
                # Test connection
                self.frontend_redis.ping()
                logging.info(f"✅ Frontend Redis connected: {self.frontend_redis_host}:{self.frontend_redis_port}")
            except Exception as e:
                logging.warning(f"⚠️ Frontend Redis connection failed: {e}")
                self.frontend_redis = None
        
        # Progress tracking (using frontend Redis)
        self.progress_redis = self.frontend_redis
        
        # Initialize Redis client for database operations (financial metrics database)
        if shared_clients:
            self.redis_client = shared_clients.get_stock_trend_redis()
            logging.info("✅ Using shared financial metrics Redis connection")
        elif redis_host and redis_port:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    username=redis_username,
                    password=redis_password,
                    decode_responses=True
                )
                logging.info(f"✅ Financial metrics Redis connected: {redis_host}:{redis_port}")
            except Exception as e:
                logging.warning(f"⚠️ Financial metrics Redis connection failed: {e}")
                self.redis_client = None
        else:
            self.redis_client = None
        
        # Initialize Financial Metrics Read Agent
        self.financial_read_agent = None
        if shared_clients or (redis_host and redis_port):
            try:
                self.financial_read_agent = FinancialMetricsReadAgent(
                    shared_clients=shared_clients,
                    redis_host=redis_host,
                    redis_port=redis_port,
                    redis_username=redis_username,
                    redis_password=redis_password,
                    collection_name=collection_name
                )
                logging.info("✅ Financial Metrics Read Agent initialized")
            except Exception as e:
                logging.warning(f"⚠️ Financial Metrics Read Agent initialization failed: {e}")
        
        logging.info(f"🚀 Financial Metrics Analyst Agent initialized for user {self.user_id}, task {self.task_id}")
    
    def _update_progress(self, step: str, status: str, progress: int = None, details: str = ""):
        """
        Update progress in Frontend Redis - separate from financial metrics database.
        
        Args:
            step: Current step (e.g., "Query to Read Agent", "Read Agent Analysis")
            status: Status (e.g., "started", "completed", "failed")
            progress: Progress percentage (0-100)
            details: Additional details
        """
        if not self.frontend_redis:
            logging.warning("⚠️ Frontend Redis not available for progress tracking")
            return
        
        try:
            progress_data = {
                "user_id": self.user_id,
                "task_id": self.task_id,
                "step": step,
                "status": status,
                "progress": progress,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "agent": "financial_metrics_analyst"  # Identify this agent's data
            }
            
            # Store progress update in frontend Redis - separate from financial metrics database
            progress_key = f"financial_metrics_analyst_frontend_progress:{self.user_id}"
            
            # Get existing progress data
            existing_data = self.frontend_redis.hgetall(progress_key)
            
            # Create updated data structure
            updated_data = {}
            
            # Keep existing data from other agents
            for key, value in existing_data.items():
                try:
                    data = json.loads(value)
                    # Only keep data from other agents
                    if data.get("agent") != "financial_metrics_analyst":
                        updated_data[key] = value
                except:
                    # Keep non-JSON data (legacy)
                    updated_data[key] = value
            
            # Add/update Financial Metrics Analyst Agent data
            financial_analyst_key = f"financial_metrics_analyst:{step}"
            updated_data[financial_analyst_key] = json.dumps(progress_data)
            
            # Store all data back to Frontend Redis
            if updated_data:
                self.frontend_redis.hset(progress_key, mapping=updated_data)
            
            # Set expiry to clean up old progress (24 hours)
            self.frontend_redis.expire(progress_key, 86400)
            
            logging.info(f"📊 Frontend Progress Update: {step} - {status} ({progress}%) - Agent: Financial Metrics Analyst")
            
        except Exception as e:
            logging.error(f"❌ Failed to update frontend progress: {e}")
    
    def _get_progress(self) -> dict:
        """Get current progress from Frontend Redis - includes all agents."""
        if not self.frontend_redis:
            return {}
        
        try:
            progress_key = f"financial_metrics_analyst_frontend_progress:{self.user_id}"
            progress_data = self.frontend_redis.hgetall(progress_key)
            
            result = {}
            for key, data_str in progress_data.items():
                try:
                    result[key] = json.loads(data_str)
                except:
                    result[key] = {"step": key, "data": data_str}
            
            return result
            
        except Exception as e:
            logging.error(f"❌ Failed to get frontend progress: {e}")
            return {}
    
    def _clear_progress(self):
        """Clear progress from Frontend Redis."""
        if not self.frontend_redis:
            return
        
        try:
            progress_key = f"financial_metrics_analyst_frontend_progress:{self.user_id}"
            self.frontend_redis.delete(progress_key)
            logging.info(f"🧹 Financial Metrics Analyst Frontend Progress cleared for user {self.user_id}")
        except Exception as e:
            logging.error(f"❌ Failed to clear frontend progress: {e}")
    
    def _store_financial_result(self, result: dict, ticker: str) -> bool:
        """
        Store financial metrics analysis result in Frontend Redis.
        
        Args:
            result: Financial metrics analysis result
            ticker: Stock ticker symbol
            
        Returns:
            bool: Success status
        """
        if not self.frontend_redis:
            logging.warning("⚠️ Frontend Redis not available for financial result storage")
            return False
        
        try:
            # Add metadata to result
            financial_result = {
                **result,
                'user_id': self.user_id,
                'task_id': self.task_id,
                'ticker': ticker,
                'agent': 'financial_metrics_analyst_agent',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat()  # 30 days expiry
            }
            
            # Create single key per user ID (only one result per user)
            financial_result_key = f"financial_metrics_analyst_result:{self.user_id}"
            
            # Store in Frontend Redis (overwrites previous result for same user)
            self.frontend_redis.set(financial_result_key, json.dumps(financial_result))
            
            # Set expiry (30 days)
            self.frontend_redis.expire(financial_result_key, 2592000)  # 30 days in seconds
            
            logging.info(f"✅ Financial result stored in Frontend Redis: {financial_result_key}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to store financial result in Frontend Redis: {e}")
            return False
    
    def _get_financial_results(self, user_id: str = None, task_id: str = None, ticker: str = None) -> list:
        """
        Get financial metrics analysis results from Frontend Redis.
        
        Args:
            user_id: User ID (defaults to current user)
            task_id: Task ID (defaults to current task)
            ticker: Stock ticker symbol (optional filter)
            
        Returns:
            list: Financial metrics analysis results
        """
        if not self.frontend_redis:
            return []
        
        try:
            user_id = user_id or self.user_id
            financial_result_key = f"financial_metrics_analyst_result:{user_id}"
            
            # Get result from Frontend Redis
            result_data = self.frontend_redis.get(financial_result_key)
            
            if result_data:
                result = json.loads(result_data)
                
                # Apply filters if provided
                if ticker and result.get('ticker') != ticker:
                    return []
                if task_id and result.get('task_id') != task_id:
                    return []
                
                return [result]
            else:
                return []
                
        except Exception as e:
            logging.error(f"❌ Failed to get financial results: {e}")
            return []
    
    async def call_financial_read_agent(self, query: str, ticker: str) -> Dict:
        """
        Call Financial Metrics Read Agent to analyze the query.
        
        Args:
            query: User query about financial metrics
            ticker: Stock ticker symbol
            
        Returns:
            Dict: Financial metrics analysis result
        """
        try:
            if not self.financial_read_agent:
                raise Exception("Financial Metrics Read Agent not initialized")
            
            logging.info(f"🔄 Calling Financial Metrics Read Agent for {ticker}")
            logging.info(f"   - Query: {query}")
            
            # Call the Read Agent to analyze financial metrics
            result = await self.financial_read_agent.analyze_financial_metrics(ticker, query)
            
            if 'error' in result:
                logging.error(f"❌ Financial Metrics Read Agent error: {result['error']}")
                return {
                    "error": result['error'],
                    "ticker": ticker,
                    "query": query,
                    "timestamp": datetime.now().isoformat()
                }
            
            logging.info(f"✅ Financial Metrics Read Agent analysis completed for {ticker}")
            return result
            
        except Exception as e:
            logging.error(f"❌ Error calling Financial Metrics Read Agent: {e}")
            return {
                "error": f"Failed to call Financial Metrics Read Agent: {str(e)}",
                "ticker": ticker,
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    async def process_query(self, query: str, ticker: str) -> Dict:
        """
        Main method to process financial metrics analysis.
        
        Args:
            query (str): User query about financial metrics
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict: Complete analysis result with Financial Metrics Read Agent analysis
        """
        try:
            self._update_progress("starting analysis", "started", 10)
            
            # Step 1: Process the query (direct pass-through)
            self._update_progress("processing query", "started", 20)
            processed_query = query  # Direct pass-through to Read Agent
            
            # Log the query
            logging.info(f"🎯 Original Query: {query}")
            logging.info(f"🎯 Query sent to Financial Metrics Read Agent: {processed_query}")
            
            # Step 2: Call Financial Metrics Read Agent with query
            self._update_progress("calling financial read agent", "started", 40)
            financial_read_result = await self.call_financial_read_agent(processed_query, ticker)
            
            # Check for errors
            if 'error' in financial_read_result:
                self._update_progress("analysis failed", "failed", 0, financial_read_result['error'])
                raise Exception(f"Financial Metrics Read Agent failed: {financial_read_result['error']}")
            
            # Step 3: Create final result with Financial Metrics Read Agent analysis
            self._update_progress("creating final result", "started", 80)
            
            # Extract just the llm_response to match other agents' output format
            llm_response = financial_read_result.get('llm_response', 'No LLM response available')
            
            # Create simplified result with just the LLM response (standard pattern)
            result = {
                "llm_response": llm_response,  # Just the LLM response like other agents
                "ticker": ticker,
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
            
            # Store full result in Frontend Redis (separate from financial metrics database)
            self._store_financial_result(financial_read_result, ticker)
            
            self._update_progress("analysis complete", "completed", 100)
            
            logging.info(f"✅ Financial metrics analysis completed for {ticker}")
            logging.info(f"   - User ID: {self.user_id}")
            logging.info(f"   - Task ID: {self.task_id}")
            logging.info(f"   - Stored in Frontend Redis: ✅")
            logging.info(f"   - Output format: Standardized (llm_response only)")
            return result
            
        except Exception as e:
            logging.error(f"❌ Error in financial metrics analysis: {e}")
            self._update_progress("analysis failed", "failed", 0, str(e))
            raise e
    
    def close(self):
        """Close the database connection."""
        if self.financial_read_agent:
            self.financial_read_agent.close()
        logging.info("🔚 Financial Metrics Analyst Agent closed")

    def get_workflow_progress(self) -> dict:
        """
        Get complete workflow progress for frontend display - includes all agents.
        
        Returns:
            dict: Complete workflow progress with all steps from all agents
        """
        progress = self._get_progress()
        
        # Define workflow steps in order (Financial Metrics Analyst Agent specific)
        financial_analyst_steps = [
            "starting analysis",
            "processing query", 
            "calling financial read agent",
            "creating final result",
            "analysis complete"
        ]
        
        # Calculate Financial Metrics Analyst Agent progress
        completed_steps = 0
        total_steps = len(financial_analyst_steps)
        
        for step in financial_analyst_steps:
            step_key = f"financial_metrics_analyst:{step}"
            if step_key in progress:
                step_data = progress[step_key]
                if step_data.get("status") in ["completed", "in_progress"]:
                    completed_steps += 1
        
        financial_analyst_progress = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        # Create workflow summary with all agents
        workflow_summary = {
            "user_id": self.user_id,
            "task_id": self.task_id,
            "overall_progress": financial_analyst_progress,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": "Unknown",
            "workflow_steps": [],
            "all_agents_progress": progress,  # Include all agents' data
            "timestamp": datetime.now().isoformat()
        }
        
        # Add each step with its status
        for step in financial_analyst_steps:
            step_key = f"financial_metrics_analyst:{step}"
            step_data = progress.get(step_key, {
                "step": step,
                "status": "pending",
                "progress": 0,
                "details": "Not started",
                "agent": "financial_metrics_analyst"
            })
            
            workflow_summary["workflow_steps"].append(step_data)
            
            # Find current step (last in_progress or first pending)
            if step_data.get("status") == "in_progress":
                workflow_summary["current_step"] = step
            elif step_data.get("status") == "pending" and workflow_summary["current_step"] == "Unknown":
                workflow_summary["current_step"] = step
        
        return workflow_summary
    
    def get_progress_for_frontend(self) -> dict:
        """
        Get simplified progress for frontend display - includes all agents.
        
        Returns:
            dict: Frontend-friendly progress data with all agents
        """
        workflow = self.get_workflow_progress()
        
        # Map workflow steps to frontend-friendly descriptions
        step_descriptions = {
            "starting analysis": "Initializing Analysis",
            "processing query": "Processing Query",
            "calling financial read agent": "Query to Read Agent",
            "creating final result": "Finalizing Results",
            "analysis complete": "Analysis Complete"
        }
        
        # Create frontend-friendly progress
        frontend_progress = {
            "user_id": workflow["user_id"],
            "task_id": workflow["task_id"],
            "overall_progress": workflow["overall_progress"],
            "current_step": step_descriptions.get(workflow["current_step"], workflow["current_step"]),
            "steps": [],
            "all_agents": {}  # Include data from all agents
        }
        
        # Add Financial Metrics Analyst Agent steps
        for step_data in workflow["workflow_steps"]:
            step_name = step_data.get("step", "")
            frontend_step = {
                "name": step_descriptions.get(step_name, step_name),
                "status": step_data.get("status", "pending"),
                "progress": step_data.get("progress", 0),
                "details": step_data.get("details", ""),
                "timestamp": step_data.get("timestamp", ""),
                "agent": "financial_metrics_analyst"
            }
            frontend_progress["steps"].append(frontend_step)
        
        # Add data from other agents
        all_agents_data = workflow.get("all_agents_progress", {})
        for key, data in all_agents_data.items():
            if isinstance(data, dict) and data.get("agent") != "financial_metrics_analyst":
                agent_name = data.get("agent", "unknown")
                if agent_name not in frontend_progress["all_agents"]:
                    frontend_progress["all_agents"][agent_name] = []
                frontend_progress["all_agents"][agent_name].append(data)
        
        return frontend_progress


def main():
    """Main function to run Financial Metrics Analyst Agent with progress tracking."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Financial Metrics Analyst Agent with Progress Tracking')
    parser.add_argument('--query', required=True, help='User query about financial metrics')
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol')
    parser.add_argument('--user-id', default='test_user', help='User ID for progress tracking')
    parser.add_argument('--task-id', default=None, help='Task ID (auto-generated if not provided)')
    parser.add_argument('--redis-host', default='redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com', help='Redis host')
    parser.add_argument('--redis-port', type=int, default=16376, help='Redis port')
    parser.add_argument('--redis-password', default='rl8242B4UItBhFzgHW5APEqZnkYoaEZv', help='Redis password')
    parser.add_argument('--show-progress', action='store_true', help='Show progress updates during execution')
    
    args = parser.parse_args()
    
    # Initialize Financial Metrics Analyst Agent with progress tracking
    agent = FinancialMetricsAnalystAgent(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_password=args.redis_password,
        user_id=args.user_id,
        task_id=args.task_id
    )
    
    try:
        print(f"🚀 Starting Financial Metrics Analysis")
        print(f"   - Query: {args.query}")
        print(f"   - Ticker: {args.ticker}")
        print(f"   - User ID: {args.user_id}")
        print(f"   - Task ID: {agent.task_id}")
        print(f"   - Progress Tracking: {'Enabled' if agent.progress_redis else 'Disabled'}")
        print()
        
        # Start progress tracking
        agent._update_progress("starting analysis", "started", 0, "Initializing Financial Metrics Analyst Agent")
        
        # Process query
        result = asyncio.run(agent.process_query(args.query, args.ticker))
        
        # Show final progress
        if args.show_progress:
            print("\n📊 Final Progress Summary:")
            progress = agent.get_progress_for_frontend()
            print(json.dumps(progress, indent=2))
        
        # Show result
        print("\n✅ Analysis Complete!")
        print("="*60)
        print(json.dumps(result, indent=2))
        
        # DO NOT clear progress - let Manager Agent handle cleanup
        print("\n📝 Progress data preserved in database for Manager Agent cleanup")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        agent._update_progress("analysis failed", "failed", 0, str(e))
        sys.exit(1)
    
    finally:
        agent.close()


if __name__ == "__main__":
    # Example usage:
    # python Financial_Metrics_Analyst_Agent.py --query "Is the current stock price overvalued based on financial metrics?" --ticker AAPL
    # python Financial_Metrics_Analyst_Agent.py --query "What is the current valuation multiple?" --ticker TSLA --user-id user123
    main()
