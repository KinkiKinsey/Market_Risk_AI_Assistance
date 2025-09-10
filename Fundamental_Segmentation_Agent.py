#!/usr/bin/env python3
"""
Fundamental Segmentation Agent
Analyzes fundamental data and performs revenue segmentation analysis.
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

# Import centralized LLM management
from LLM_Call_Agent import LLMCallAgent

# Import existing agents (RESTORE PROPER ARCHITECTURE!)
from Revenue_Segmentation_Read_Agent import RevenueSegmentationAnalystAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('fundamental_segmentation.log')
    ]
)

@dataclass
class FundamentalEvent:
    """Data class for fundamental event information."""
    event_type: str  # 'earnings', 'policy_change', 'competition', 'regulation', 'product_launch'
    event_description: str
    affected_revenue_segments: List[str]
    time_period: str  # 'recent', 'historical', 'upcoming'
    confidence_score: float

@dataclass
class RevenueImpact:
    """Data class for revenue impact information."""
    segment_name: str
    impact_percentage: str  # e.g., "-15%", "+8%"
    impact_description: str
    affected_customers: List[str]
    time_horizon: str  # 'immediate', 'short_term', 'long_term'

class FundamentalSegmentationAgent:
    """
    Fundamental Segmentation Agent - Breaks down fundamental queries and generates revenue impact analysis.
    """
    
    def __init__(self, progress_context=None, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None, 
                 collection_name: str = "Revenue_Segmentation_INFOS", openai_api_key: str = None,
                 user_id: str = None, task_id: str = None):
        """
        Initialize Fundamental Segmentation Agent with progress tracking.
        
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
        
        # Frontend Redis Database (Separate from revenue segmentation database)
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
        
        # Use shared clients for LLM operations
        if shared_clients:
            self.llm_agent = shared_clients.get_llm_agent()
            logging.info("✅ Using shared LLM client")
        else:
            try:
                from shared_clients import shared_clients
                self.llm_agent = shared_clients.get_llm_agent()
                logging.info("✅ Using shared LLM client")
            except ImportError:
                # Fallback to direct LLM agent if shared clients not available
                self.llm_agent = LLMCallAgent(
                    default_provider="deepseek",
                    default_model="deepseek-chat"
                )
                logging.info("⚠️ Using direct LLM client (shared clients not available)")
        
        logging.info(f"🔑 API Keys Status:")
        logging.info(f"   - DeepSeek: {'✅ Available' if self.llm_agent.deepseek_api_key else '❌ Missing'}")
        logging.info(f"   - OpenAI: {'✅ Available' if self.llm_agent.openai_api_key else '❌ Missing'}")
        
        # Initialize Revenue Segmentation Database connection
        if shared_clients:
            self.revenue_redis_client = shared_clients.get_stock_trend_redis()
            logging.info("✅ Using shared revenue Redis connection")
        else:
            self.revenue_redis_host = redis_host or "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
            self.revenue_redis_port = redis_port or 16376
            self.revenue_redis_username = redis_username or "default"
            self.revenue_redis_password = redis_password or "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
            self.revenue_redis_client = None
        
        # Initialize Revenue Segmentation Read Agent (RESTORE PROPER ARCHITECTURE!)
        if shared_clients:
            self.revenue_read_agent = RevenueSegmentationAnalystAgent(
                shared_clients=shared_clients,
                collection_name=collection_name
            )
        else:
            self.revenue_read_agent = RevenueSegmentationAnalystAgent(
                shared_clients=shared_clients,
                redis_host=self.revenue_redis_host,
                redis_port=self.revenue_redis_port,
                redis_username=self.revenue_redis_username,
                redis_password=self.revenue_redis_password,
                collection_name=collection_name
            )
        
        logging.info("✅ Revenue Segmentation Database connection configured")
        logging.info("✅ Revenue Segmentation Read Agent initialized")
        
        logging.info(f"🚀 Fundamental Segmentation Agent initialized for user {self.user_id}, task {self.task_id}")
    
    def _update_progress(self, step: str, status: str, progress: int = None, details: str = ""):
        """
        Update progress in Frontend Redis - separate from revenue segmentation database.
        
        Args:
            step: Current step (e.g., "Query to Revenue Read Agent", "Revenue Analysis")
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
                "agent": "fundamental_segmentation"  # Identify this agent's data
            }
            
            # Store progress update in frontend Redis - separate from revenue segmentation database
            progress_key = f"fundamental_segmentation_frontend_progress:{self.user_id}"
            
            # Get existing progress data
            existing_data = self.frontend_redis.hgetall(progress_key)
            
            # Create updated data structure
            updated_data = {}
            
            # Keep existing data from other agents
            for key, value in existing_data.items():
                try:
                    data = json.loads(value)
                    # Only keep data from other agents
                    if data.get("agent") != "fundamental_segmentation":
                        updated_data[key] = value
                except:
                    # Keep non-JSON data (legacy)
                    updated_data[key] = value
            
            # Add/update Fundamental Segmentation Agent data
            fundamental_key = f"fundamental_segmentation:{step}"
            updated_data[fundamental_key] = json.dumps(progress_data)
            
            # Store all data back to Frontend Redis
            if updated_data:
                self.frontend_redis.hset(progress_key, mapping=updated_data)
            
            # Set expiry to clean up old progress (24 hours)
            self.frontend_redis.expire(progress_key, 86400)
            
            logging.info(f"📊 Frontend Progress Update: {step} - {status} ({progress}%) - Agent: Fundamental Segmentation")
            
        except Exception as e:
            logging.error(f"❌ Failed to update frontend progress: {e}")
    
    def _get_progress(self) -> dict:
        """Get current progress from Frontend Redis - includes all agents."""
        if not self.frontend_redis:
            return {}
        
        try:
            progress_key = f"fundamental_segmentation_frontend_progress:{self.user_id}"
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
            progress_key = f"fundamental_segmentation_frontend_progress:{self.user_id}"
            self.frontend_redis.delete(progress_key)
            logging.info(f"🧹 Fundamental Segmentation Frontend Progress cleared for user {self.user_id}")
        except Exception as e:
            logging.error(f"❌ Failed to clear frontend progress: {e}")
    
    def preprocess_query_with_cot(self, query: str, ticker: str) -> str:
        """
        Preprocess query using Chain of Thought to understand fundamental events.
        
        Args:
            query (str): Original user query
            ticker (str): Stock ticker symbol
            
        Returns:
            str: Preprocessed query focused on revenue impact
        """
        try:
            logging.info(f"🧠 Preprocessing query with Chain of Thought: {query}")
            
            # Create Chain of Thought prompt
            cot_prompt = f"""
Analyze this fundamental event query and break it down into revenue-focused analysis.

ORIGINAL QUERY: "{query}"
TICKER: {ticker}

CHAIN OF THOUGHT ANALYSIS:
1. What type of fundamental event is this? (earnings, policy, competition, regulation, etc.)
2. Which revenue segments are most likely to be affected?
3. What is the expected revenue impact direction? (positive/negative/neutral)
4. What time horizon should we analyze? (immediate, short-term, long-term)

Based on this analysis, create a refined query focused on revenue impact analysis.

REFINED QUERY FORMAT:
"What is the revenue impact of [EVENT] on [TICKER]'s [RELEVANT_SEGMENTS]?"

Provide only the refined query, no explanations.
"""
            
            # Get LLM response
            response = self.llm_agent.call_llm(
                prompt=cot_prompt,
                system_message="You are a fundamental analysis expert. Focus on revenue impact analysis.",
                max_tokens=200,
                temperature=0.3
            )
            
            # Clean response
            refined_query = response.strip().replace('"', '').replace('"', '')
            
            logging.info(f"✅ Query preprocessed: {refined_query}")
            return refined_query
            
        except Exception as e:
            logging.error(f"❌ Error in query preprocessing: {e}")
            # Fallback to simple query
            return f"What is the revenue impact of {query} on {ticker}?"
    
    async def call_revenue_read_agent(self, refined_query: str, ticker: str) -> Dict:
        """
        Call Revenue Segmentation Read Agent with refined query and track progress.
        
        Args:
            refined_query: Refined query focused on revenue impact
            ticker: Stock ticker symbol
            
        Returns:
            Dict: Revenue read agent result
        """
        try:
            self._update_progress("Query to Revenue Read Agent", "started", 40, f"Calling Revenue Read Agent for {ticker}")
            
            # Call Revenue Segmentation Read Agent
            if self.revenue_read_agent:
                result = await self.revenue_read_agent.process_natural_query(refined_query, ticker)
                self._update_progress("Query to Revenue Read Agent", "completed", 50, "Successfully called Revenue Read Agent")
            else:
                # Fallback if Revenue Read Agent is not available
                result = {
                    "status": "error",
                    "message": "Revenue Read Agent not available",
                    "data": {}
                }
                self._update_progress("Query to Revenue Read Agent", "failed", 50, "Revenue Read Agent not available")
            
            return {
                "original_query": refined_query,
                "refined_query": refined_query,
                "revenue_read_result": result
            }
            
        except Exception as e:
            self._update_progress("Query to Revenue Read Agent", "failed", 50, str(e))
            logging.error(f"❌ Error calling Revenue Read Agent: {e}")
            raise e
    
    def generate_fundamental_insights(self, query: str, refined_query: str, revenue_result: str, ticker: str) -> str:
        """
        Generate comprehensive fundamental insights using LLM.
        
        Args:
            query (str): Original user query
            refined_query (str): Refined revenue-focused query
            revenue_result (str): Result from Revenue Read Agent
            ticker (str): Stock ticker symbol
            
        Returns:
            str: LLM-generated fundamental insights
        """
        try:
            logging.info(f"🤖 Generating fundamental insights for {ticker}")
            
            prompt = f"""
Based on the following information, provide comprehensive fundamental insights about the revenue impact.

ORIGINAL QUERY: "{query}"
REFINED QUERY: "{refined_query}"
TICKER: {ticker}
REVENUE ANALYSIS: {revenue_result}

ANALYSIS REQUIREMENTS:
1. **Fundamental Event Analysis**: Explain what fundamental event occurred and its significance
2. **Revenue Segment Impact**: Identify which revenue segments are most affected and why
3. **Competitive Landscape**: Analyze how this event affects competitive positioning
4. **Risk Assessment**: Evaluate short-term and long-term risks to revenue streams
5. **Strategic Implications**: Discuss what this means for the company's business model

Provide a structured analysis with clear sections and actionable insights.
Focus on fundamental business implications, not just revenue numbers.
"""
            
            response = self.llm_agent.call_llm(
                prompt=prompt,
                system_message="You are a fundamental analysis expert. Provide comprehensive business insights.",
                max_tokens=800,
                temperature=0.3
            )
            
            logging.info(f"✅ Fundamental insights generated for {ticker}")
            return response
            
        except Exception as e:
            logging.error(f"❌ Error generating fundamental insights: {e}")
            return f"❌ Error generating fundamental insights: {str(e)}"
    
    async def process_query(self, query: str, ticker: str) -> Dict:
        """
        Main method to process fundamental segmentation analysis.
        
        Args:
            query (str): Complex fundamental event query
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict: Complete analysis result with fundamental insights and revenue analysis
        """
        try:
            self._update_progress("starting analysis", "started", 10)
            
            # Step 1: Direct query pass-through (no LLM preprocessing)
            self._update_progress("direct query pass-through", "started", 20)
            preprocessed_query = query  # Direct pass-through, no transformation
            
            # Log the fundamental analysis
            logging.info(f"🎯 Original Query: {query}")
            logging.info(f"🎯 Direct Pass-Through: {preprocessed_query}")
            
            # Step 2: Call Revenue Read Agent with original query (direct pass-through)
            self._update_progress("calling revenue read agent", "started", 40)
            revenue_read_wrapper = await self.call_revenue_read_agent(preprocessed_query, ticker)
            
            # Extract the revenue analysis result
            revenue_read_result = revenue_read_wrapper.get("revenue_read_result", "No result available")
            
            # Step 3: Generate fundamental insights
            self._update_progress("generating fundamental insights", "started", 80)
            fundamental_insights = self.generate_fundamental_insights(query, preprocessed_query, revenue_read_result, ticker)
            
            # Step 4: Create final result
            self._update_progress("creating final result", "started", 95)
            result = {
                "original_query": query,
                "ticker": ticker,
                "fundamental_event": self._extract_event_type(query),
                "refined_query": preprocessed_query,
                "revenue_analysis": revenue_read_result,
                "fundamental_insights": fundamental_insights,
                "completed_at": datetime.now().isoformat()
            }
            
            # Store result in Frontend Redis (separate from revenue segmentation database)
            storage_success = self._store_fundamental_result(result, ticker)
            
            self._update_progress("analysis complete", "completed", 100)
            
            logging.info(f"✅ Fundamental segmentation analysis completed for {ticker}")
            logging.info(f"   - User ID: {self.user_id}")
            logging.info(f"   - Task ID: {self.task_id}")
            logging.info(f"   - Stored in Frontend Redis: {'✅' if storage_success else '❌'}")
            return result
            
        except Exception as e:
            logging.error(f"❌ Error in fundamental segmentation analysis: {e}")
            self._update_progress("analysis failed", "failed", 0, str(e))
            raise e
    
    def _extract_event_type(self, query: str) -> str:
        """Extract the type of fundamental event from the query."""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['earnings', 'quarterly', 'annual', 'report']):
            return "Earnings Event"
        elif any(word in query_lower for word in ['policy', 'regulation', 'law', 'government']):
            return "Policy/Regulatory Change"
        elif any(word in query_lower for word in ['competition', 'competitor', 'pricing', 'fees']):
            return "Competitive Action"
        elif any(word in query_lower for word in ['product', 'launch', 'technology', 'innovation']):
            return "Product/Technology Event"
        elif any(word in query_lower for word in ['merger', 'acquisition', 'partnership']):
            return "Corporate Action"
        else:
            return "General Market Event"
    
    def _store_fundamental_result(self, result: Dict, ticker: str) -> bool:
        """
        Store fundamental segmentation result in Frontend Redis.
        
        Args:
            result: Fundamental segmentation analysis result
            ticker: Stock ticker symbol
            
        Returns:
            bool: Success status
        """
        if not self.frontend_redis:
            logging.warning("⚠️ Frontend Redis not available for fundamental result storage")
            return False
        
        try:
            # Add metadata to result
            fundamental_result = {
                **result,
                'user_id': self.user_id,
                'task_id': self.task_id,
                'ticker': ticker,
                'agent': 'fundamental_segmentation_agent',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat()  # 30 days expiry
            }
            
            # Create single key per user ID (only one result per user)
            fundamental_result_key = f"fundamental_segmentation_result:{self.user_id}"
            
            # Store in Frontend Redis (overwrites previous result for same user)
            self.frontend_redis.set(fundamental_result_key, json.dumps(fundamental_result))
            
            # Set expiry (30 days)
            self.frontend_redis.expire(fundamental_result_key, 2592000)  # 30 days in seconds
            
            logging.info(f"✅ Fundamental result stored in Frontend Redis: {fundamental_result_key}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to store fundamental result in Frontend Redis: {e}")
            return False
    
    def _get_fundamental_results(self, user_id: str = None, task_id: str = None, ticker: str = None) -> list:
        """
        Get fundamental segmentation results from Frontend Redis.
        
        Args:
            user_id: User ID (defaults to current user)
            task_id: Task ID (defaults to current task)
            ticker: Stock ticker symbol (optional filter)
            
        Returns:
            list: Fundamental segmentation results
        """
        if not self.frontend_redis:
            return []
        
        try:
            target_user_id = user_id or self.user_id
            target_task_id = task_id or self.task_id
            
            # Get result for specific user
            fundamental_result_key = f"fundamental_segmentation_result:{target_user_id}"
            result_data = self.frontend_redis.get(fundamental_result_key)
            
            if not result_data:
                return []
            
            result = json.loads(result_data)
            
            # Filter by ticker if specified
            if ticker and result.get('ticker') != ticker.upper():
                return []
            
            # Filter by task_id if specified
            if task_id and result.get('task_id') != task_id:
                return []
            
            return [result]
            
        except Exception as e:
            logging.error(f"❌ Failed to get fundamental results: {e}")
            return []
    
    def _clear_fundamental_results(self, user_id: str = None) -> bool:
        """
        Clear fundamental segmentation results from Frontend Redis.
        
        Args:
            user_id: User ID (defaults to current user)
            
        Returns:
            bool: Success status
        """
        if not self.frontend_redis:
            return False
        
        try:
            target_user_id = user_id or self.user_id
            fundamental_result_key = f"fundamental_segmentation_result:{target_user_id}"
            
            # Delete result
            self.frontend_redis.delete(fundamental_result_key)
            
            logging.info(f"🧹 Fundamental results cleared for user {target_user_id}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to clear fundamental results: {e}")
            return False
    
    def close(self):
        """Close the database connection."""
        if self.revenue_read_agent:
            self.revenue_read_agent.close()
        logging.info("🔚 Fundamental Segmentation Agent closed")

    def get_workflow_progress(self) -> dict:
        """
        Get complete workflow progress for frontend display - includes all agents.
        
        Returns:
            dict: Complete workflow progress with all steps from all agents
        """
        progress = self._get_progress()
        
        # Define workflow steps in order (Fundamental Segmentation Agent specific)
        fundamental_steps = [
            "starting analysis",
            "direct query pass-through", 
            "calling revenue read agent",
            "generating fundamental insights",
            "creating final result",
            "analysis complete"
        ]
        
        # Calculate Fundamental Segmentation Agent progress
        completed_steps = 0
        total_steps = len(fundamental_steps)
        
        for step in fundamental_steps:
            step_key = f"fundamental_segmentation:{step}"
            if step_key in progress:
                step_data = progress[step_key]
                if step_data.get("status") in ["completed", "in_progress"]:
                    completed_steps += 1
        
        fundamental_progress = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        # Create workflow summary with all agents
        workflow_summary = {
            "user_id": self.user_id,
            "task_id": self.task_id,
            "overall_progress": fundamental_progress,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": "Unknown",
            "workflow_steps": [],
            "all_agents_progress": progress,  # Include all agents' data
            "timestamp": datetime.now().isoformat()
        }
        
        # Add each step with its status
        for step in fundamental_steps:
            step_key = f"fundamental_segmentation:{step}"
            step_data = progress.get(step_key, {
                "step": step,
                "status": "pending",
                "progress": 0,
                "details": "Not started",
                "agent": "fundamental_segmentation"
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
            "direct query pass-through": "Direct Query Pass-Through",
            "calling revenue read agent": "Query to Revenue Read Agent",
            "generating fundamental insights": "Generating Fundamental Insights", 
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
        
        # Add step details
        for step_data in workflow["workflow_steps"]:
            step_name = step_data.get("step", "Unknown")
            step_description = step_descriptions.get(step_name, step_name.replace("_", " ").title())
            
            frontend_progress["steps"].append({
                "name": step_name,
                "description": step_description,
                "status": step_data.get("status", "pending"),
                "progress": step_data.get("progress", 0),
                "details": step_data.get("details", ""),
                "timestamp": step_data.get("timestamp", "")
            })
        
        # Include all agents' progress data
        frontend_progress["all_agents"] = workflow["all_agents_progress"]
        
        return frontend_progress


def main():
    """Main function to handle command line arguments and execute fundamental segmentation analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Fundamental Segmentation Agent - Revenue impact analysis for fundamental events')
    
    # Required arguments
    parser.add_argument('--query', required=True, help='Fundamental event query (e.g., "Meta cancels GPU fees impact on CRWV")')
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol (e.g., CRWV, AAPL, TSLA)')
    
    # Optional arguments
    parser.add_argument('--user-id', help='User ID for progress tracking')
    parser.add_argument('--task-id', help='Task ID for progress tracking')
    parser.add_argument('--show-progress', action='store_true', help='Show progress updates')
    parser.add_argument('--log-level', default='INFO', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'])
    
    args = parser.parse_args()
    
    # Setup logging
    logging.getLogger().setLevel(getattr(logging, args.log_level.upper()))
    
    # PREDEFINED DATABASE CONFIGURATION (same as Revenue Segmentation DB Agent)
    DB_TYPE = "redis"
    DB_COLLECTION = "Revenue_Segmentation_INFOS"
    
    # Redis configuration (predefined - same as Revenue Segmentation DB Agent)
    REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
    REDIS_PORT = 16376
    REDIS_USERNAME = "default"
    REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
    
    try:
        logging.info(f"🔧 INITIALIZING FUNDAMENTAL SEGMENTATION AGENT")
        logging.info(f"   - Query: {args.query}")
        logging.info(f"   - Ticker: {args.ticker.upper()}")
        logging.info(f"   - User ID: {args.user_id or 'default'}")
        logging.info(f"   - Task ID: {args.task_id or 'auto-generated'}")
        
        # Initialize agent
        agent = FundamentalSegmentationAgent(
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            redis_username=REDIS_USERNAME,
            redis_password=REDIS_PASSWORD,
            collection_name=DB_COLLECTION,
            user_id=args.user_id,
            task_id=args.task_id
        )
        
        # Process query
        logging.info(f"🚀 PROCESSING FUNDAMENTAL SEGMENTATION QUERY")
        logging.info(f"   - Query: {args.query}")
        logging.info(f"   - Ticker: {args.ticker.upper()}")
        
        # Run async process
        result = asyncio.run(agent.process_query(args.query, args.ticker.upper()))
        
        # Display results
        logging.info(f"✅ FUNDAMENTAL SEGMENTATION ANALYSIS COMPLETED")
        logging.info(f"   - Ticker: {args.ticker.upper()}")
        logging.info(f"   - Event Type: {result.get('fundamental_event', 'Unknown')}")
        logging.info(f"   - Refined Query: {result.get('refined_query', 'Unknown')}")
        
        print(f"\n🎯 FUNDAMENTAL SEGMENTATION RESULTS FOR {args.ticker.upper()}:")
        print(json.dumps(result, indent=2))
        
        # Show progress if requested
        if args.show_progress:
            progress = agent.get_workflow_progress()
            print(f"\n📊 WORKFLOW PROGRESS:")
            print(json.dumps(progress, indent=2))
        
    except KeyboardInterrupt:
        logging.warning("⚠️  OPERATION CANCELLED BY USER")
    except Exception as e:
        logging.error("❌ CRITICAL ERROR IN MAIN EXECUTION:")
        logging.error(f"   - Error type: {type(e).__name__}")
        logging.error(f"   - Error details: {e}")
        logging.error(f"   - Full traceback:")
        import traceback
        logging.error(traceback.format_exc())
        sys.exit(1)
    finally:
        if 'agent' in locals():
            agent.close()
            logging.info("🔚 Fundamental Segmentation Agent closed")


if __name__ == "__main__":
    # Example usage:
    # python3 Fundamental_Segmentation_Agent.py --query "Meta cancels GPU fees impact on CRWV" --ticker CRWV
    # python3 Fundamental_Segmentation_Agent.py --query "New AI regulation impact on CRWV" --ticker CRWV --show-progress
    main()
