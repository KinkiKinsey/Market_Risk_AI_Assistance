#!/usr/bin/env python3
"""
Earnings and Future Agent
Breaks down complex user queries into precise, callable queries for Earnings Read Agent.
Outputs LLM analysis and earnings data for frontend display.
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
import argparse

# Import existing agents
from Earnings_and_Future_Read_Agent import EarningsAndFutureReadAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('earnings_and_future.log')
    ]
)

@dataclass
class QueryBreakdown:
    """Data class for broken down query information."""
    original_query: str
    simplified_queries: List[str]
    query_type: str  # 'earnings', 'future_development', 'growth_plans', etc.
    affected_sectors: List[str]
    time_period: str  # 'recent', 'historical', 'all'
    confidence_score: float

@dataclass
class EarningsInsight:
    """Data class for earnings insight information."""
    insight_type: str  # 'performance', 'guidance', 'strategy', 'risks'
    importance_score: float  # 0-1, relevance to user query
    description: str
    key_metrics: List[str]

class EarningsAndFutureAgent:
    """
    Earnings and Future Agent - Breaks down complex queries and generates precise analysis.
    """
    
    def __init__(self, progress_context=None, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None, 
                 collection_name: str = "Earnings_and_Future_INFOS", openai_api_key: str = None,
                 user_id: str = None, task_id: str = None):
        """
        Initialize Earnings and Future Agent with progress tracking.
        
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
        
        # Frontend Redis Database (Separate from earnings database)
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
        
        # Initialize Redis client for database operations (earnings database)
        if shared_clients:
            self.redis_client = shared_clients.get_earnings_redis()
            logging.info("✅ Using shared earnings Redis connection")
        elif redis_host and redis_port:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    username=redis_username,
                    password=redis_password,
                    decode_responses=True
                )
                logging.info(f"✅ Earnings Redis connected: {redis_host}:{redis_port}")
            except Exception as e:
                logging.warning(f"⚠️ Earnings Redis connection failed: {e}")
                self.redis_client = None
        else:
            self.redis_client = None
        
        # LLM agent removed - no longer needed for CoT preprocessing
        
        # Initialize Earnings Read Agent
        self.earnings_read_agent = None
        if shared_clients or (redis_host and redis_port):
            try:
                self.earnings_read_agent = EarningsAndFutureReadAgent(
                    shared_clients=shared_clients,
                    redis_host=redis_host,
                    redis_port=redis_port,
                    redis_username=redis_username,
                    redis_password=redis_password
                )
                logging.info("✅ Earnings Read Agent initialized")
            except Exception as e:
                logging.warning(f"⚠️ Earnings Read Agent initialization failed: {e}")
        
        logging.info(f"🚀 Earnings and Future Agent initialized for user {self.user_id}, task {self.task_id}")
    
    def _update_progress(self, step: str, status: str, progress: int = None, details: str = ""):
        """
        Update progress in Frontend Redis - separate from earnings database.
        
        Args:
            step: Current step (e.g., "Query to Read Agent", "Read Agent to DB Agent")
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
                "agent": "earnings_and_future"  # Identify this agent's data
            }
            
            # Store progress update in frontend Redis - separate from earnings database
            progress_key = f"earnings_and_future_frontend_progress:{self.user_id}"
            
            # Get existing progress data
            existing_data = self.frontend_redis.hgetall(progress_key)
            
            # Create updated data structure
            updated_data = {}
            
            # Keep existing data from other agents
            for key, value in existing_data.items():
                try:
                    data = json.loads(value)
                    # Only keep data from other agents
                    if data.get("agent") != "earnings_and_future":
                        updated_data[key] = value
                except:
                    # If parsing fails, keep the original value
                    updated_data[key] = value
            
            # Add new progress data
            updated_data[f"{step}_{status}"] = json.dumps(progress_data)
            
            # Store updated data
            self.frontend_redis.hset(progress_key, mapping=updated_data)
            
            logging.info(f"📊 Frontend Progress Update: {step} - {status} ({progress}%) - Agent: Earnings and Future")
            
        except Exception as e:
            logging.error(f"❌ Error updating progress: {e}")
    
    def scoped_db_insert(self, collection: str, scoped_data: Dict, key_suffix: str = None) -> bool:
        """
        Insert scoped data into Redis database.
        
        Args:
            collection: Collection name
            scoped_data: Data to insert
            key_suffix: Optional key suffix
            
        Returns:
            bool: Success status
        """
        if not self.redis_client:
            logging.warning("⚠️ Redis client not available for scoped_db_insert")
            return False
        
        try:
            # Create unique key
            timestamp = int(datetime.now().timestamp())
            suffix = key_suffix or f"{timestamp}"
            key = f"{collection}:{self.user_id}:{self.task_id}:{suffix}"
            
            # Store in Redis
            self.redis_client.set(key, json.dumps(scoped_data))
            
            logging.info(f"✅ Scoped data inserted: {key}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Error in scoped_db_insert: {e}")
            return False
    
    def _matches_query(self, data: dict, query: dict) -> bool:
        """Check if data matches the query filters."""
        if not query:
            return True
        
        for key, value in query.items():
            if key not in data or data[key] != value:
                return False
        
        return True
    
    def report_progress(self, progress: int, step: str, status: str = "processing"):
        """Report progress if context is available."""
        if self.progress_context:
            self.progress_context.report_progress("earnings_and_future", progress, step, status)
    
    # CoT preprocessing removed - user queries pass through directly to Earnings Read Agent
    
    async def call_earnings_read_agent(self, preprocessed_query: str, ticker: str) -> Dict:
        """
        Call Earnings Read Agent with enhanced query and track progress.
        
        Args:
            preprocessed_query: Enhanced query with earnings focus
            ticker: Stock ticker symbol
            
        Returns:
            Dict: Earnings read agent result
        """
        try:
            self._update_progress("Query to Read Agent", "started", 40, f"Calling Read Agent for {ticker}")
            
            # Enhance query with earnings focus
            enhanced_query = self._enhance_query_with_earnings_focus(preprocessed_query, ticker)
            
            self._update_progress("Query to Read Agent", "in_progress", 45, "Enhanced query with earnings focus")
            
            # Call Earnings Read Agent
            if self.earnings_read_agent:
                result = await self.earnings_read_agent.process_natural_query(enhanced_query, ticker)
                self._update_progress("Query to Read Agent", "completed", 50, "Successfully called Read Agent")
            else:
                # Fallback if Earnings Read Agent is not available
                result = {
                    "status": "error",
                    "message": "Earnings Read Agent not available",
                    "data": {}
                }
                self._update_progress("Query to Read Agent", "failed", 50, "Earnings Read Agent not available")
            
            return {
                "original_query": preprocessed_query,
                "enhanced_query": enhanced_query,
                "earnings_read_result": result
            }
            
        except Exception as e:
            self._update_progress("Query to Read Agent", "failed", 50, str(e))
            logging.error(f"❌ Error calling Earnings Read Agent: {e}")
            raise e
    
    def _enhance_query_with_earnings_focus(self, preprocessed_query: str, ticker: str) -> str:
        """
        Enhance the preprocessed query to be more explicit about earnings focus.
        
        Args:
            preprocessed_query (str): Original preprocessed query
            ticker (str): Stock ticker symbol
            
        Returns:
            str: Enhanced query with explicit earnings focus
        """
        query_lower = preprocessed_query.lower()
        
        # Check if the query already contains earnings keywords
        earnings_keywords = ['earnings', 'revenue', 'profit', 'eps', 'guidance', 'outlook', 'future', 'growth']
        if any(keyword in query_lower for keyword in earnings_keywords):
            return preprocessed_query
        
        # Analyze the query for earnings-related indicators
        performance_indicators = [
            'performance', 'results', 'beat', 'miss', 'growth', 'decline', 'increase', 'decrease',
            'revenue', 'profit', 'margin', 'eps', 'earnings per share', 'quarterly', 'annual'
        ]
        
        future_indicators = [
            'future', 'outlook', 'guidance', 'forecast', 'strategy', 'plans', 'roadmap',
            'expansion', 'development', 'innovation', 'technology', 'market', 'opportunities'
        ]
        
        # Count indicators
        performance_count = sum(1 for indicator in performance_indicators if indicator in query_lower)
        future_count = sum(1 for indicator in future_indicators if indicator in query_lower)
        
        # Determine focus
        if performance_count > future_count:
            # Add explicit earnings performance request
            enhanced_query = f"Analyze {ticker} earnings performance and financial results: {query_lower}"
            logging.info(f"📊 Enhanced query for EARNINGS PERFORMANCE analysis: {enhanced_query}")
            
        elif future_count > performance_count:
            # Add explicit future development request
            enhanced_query = f"Analyze {ticker} future development and growth plans: {query_lower}"
            logging.info(f"🚀 Enhanced query for FUTURE DEVELOPMENT analysis: {enhanced_query}")
            
        else:
            # If unclear, request both
            enhanced_query = f"Analyze {ticker} earnings performance and future development: {query_lower}"
            logging.info(f"📈 Enhanced query for COMPREHENSIVE earnings analysis: {enhanced_query}")
        
        return enhanced_query
    
    def extract_earnings_insights(self, earnings_read_result: Dict) -> List[EarningsInsight]:
        """
        Extract earnings insights from Earnings Read Agent result.
        
        Args:
            earnings_read_result (Dict): Result from Earnings Read Agent
            
        Returns:
            List[EarningsInsight]: Earnings insights for analysis
        """
        logging.info(f"📊 Extracting earnings insights from Earnings Read Agent result")
        
        insights = []
        
        try:
            # Parse the result
            if isinstance(earnings_read_result, str):
                # If it's a string result, create a basic insight
                insights.append(EarningsInsight(
                    insight_type="analysis",
                    importance_score=1.0,
                    description=earnings_read_result,
                    key_metrics=[]
                ))
            elif isinstance(earnings_read_result, dict):
                # If it's a dict, extract structured insights
                if "earnings_read_result" in earnings_read_result:
                    result_text = earnings_read_result["earnings_read_result"]
                    
                    # Extract different types of insights
                    if "earnings" in result_text.lower():
                        insights.append(EarningsInsight(
                            insight_type="performance",
                            importance_score=0.9,
                            description="Earnings performance analysis",
                            key_metrics=["revenue", "profit", "eps"]
                        ))
                    
                    if "future" in result_text.lower() or "development" in result_text.lower():
                        insights.append(EarningsInsight(
                            insight_type="strategy",
                            importance_score=0.8,
                            description="Future development strategy",
                            key_metrics=["growth", "expansion", "innovation"]
                        ))
                    
                    if "guidance" in result_text.lower() or "outlook" in result_text.lower():
                        insights.append(EarningsInsight(
                            insight_type="guidance",
                            importance_score=0.7,
                            description="Management guidance and outlook",
                            key_metrics=["forecast", "expectations", "targets"]
                        ))
            
            logging.info(f"✅ Extracted {len(insights)} earnings insights")
            return insights
            
        except Exception as e:
            logging.error(f"❌ Error extracting earnings insights: {e}")
            return []
    
    async def process_natural_query(self, query: str, ticker: str = None) -> Dict:
        """
        Process a natural language query about earnings and future development.
        
        Args:
            query (str): Natural language query
            ticker (str): Optional ticker symbol
            
        Returns:
            Dict: Processed result with earnings analysis
        """
        try:
            logging.info(f"🚀 Starting Earnings and Future Analysis")
            logging.info(f"   - Query: {query}")
            logging.info(f"   - Ticker: {ticker}")
            logging.info(f"   - User ID: {self.user_id}")
            logging.info(f"   - Task ID: {self.task_id}")
            logging.info(f"   - Progress Tracking: Enabled")
            
            # Update progress
            self._update_progress("starting analysis", "started", 0, "Initializing earnings analysis")
            
            # Step 1: Preprocess query
            self._update_progress("starting analysis", "started", 10, "Preprocessing query")
            preprocessed_query = self._preprocess_query(query)
            
            # Step 2: Process query
            self._update_progress("processing query", "started", 20, "Processing earnings query")
            
            # Step 3: Call Earnings Read Agent
            self._update_progress("calling earnings read agent", "started", 40, "Calling Earnings Read Agent")
            earnings_result = await self.call_earnings_read_agent(preprocessed_query, ticker)
            
            # Step 4: Extract insights
            self._update_progress("extracting insights", "started", 60, "Extracting earnings insights")
            insights = self.extract_earnings_insights(earnings_result)
            
            # Step 5: Create final result
            self._update_progress("creating final result", "started", 80, "Creating final earnings result")
            
            final_result = {
                "original_query": query,
                "ticker": ticker,
                "preprocessed_query": preprocessed_query,
                "earnings_read_result": earnings_result.get("earnings_read_result", ""),
                "completed_at": datetime.now().isoformat()
            }
            
            # Store result in frontend Redis
            if self.frontend_redis:
                result_key = f"earnings_and_future_result:{self.user_id}"
                self.frontend_redis.set(result_key, json.dumps(final_result), ex=86400)  # 24 hours
                logging.info(f"✅ Earnings result stored in Frontend Redis: {result_key}")
            
            self._update_progress("analysis complete", "completed", 100, "Earnings analysis completed")
            
            logging.info(f"✅ Earnings and future analysis completed for {ticker}")
            logging.info(f"   - User ID: {self.user_id}")
            logging.info(f"   - Task ID: {self.task_id}")
            logging.info(f"   - Stored in Frontend Redis: ✅")
            
            return final_result
            
        except Exception as e:
            self._update_progress("analysis failed", "failed", 100, str(e))
            logging.error(f"❌ Error in earnings analysis: {e}")
            raise e
    
    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess the query to make it more suitable for earnings analysis.
        
        Args:
            query (str): Original query
            
        Returns:
            str: Preprocessed query
        """
        # Basic preprocessing - can be enhanced later
        preprocessed = query.strip()
        
        # Add earnings context if not present
        if not any(keyword in preprocessed.lower() for keyword in ['earnings', 'revenue', 'profit', 'future', 'development']):
            preprocessed = f"Analyze earnings and future development: {preprocessed}"
        
        return preprocessed
    
    def close(self):
        """Close Redis connections."""
        if self.frontend_redis:
            self.frontend_redis.close()
        if self.redis_client:
            self.redis_client.close()
        logging.info("🔚 Earnings and Future Agent closed")


def main():
    """Main function to handle command line arguments and execute queries."""
    parser = argparse.ArgumentParser(description='Earnings and Future Agent - Natural Language Query Interface')
    
    # Database arguments
    parser.add_argument('--redis-host', default='redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com',
                       help='Redis host')
    parser.add_argument('--redis-port', type=int, default=16376, help='Redis port')
    parser.add_argument('--redis-username', default='default', help='Redis username')
    parser.add_argument('--redis-password', default='rl8242B4UItBhFzgHW5APEqZnkYoaEZv', help='Redis password')
    parser.add_argument('--collection', default='Earnings_and_Future_INFOS', help='Redis collection name')
    
    # Query arguments
    parser.add_argument('--query', help='Natural language query about earnings and future development')
    parser.add_argument('--ticker', help='Stock ticker symbol')
    
    # OpenAI arguments
    parser.add_argument('--openai-key', help='OpenAI API key for LLM analysis (optional, will auto-import from LLM_Call_Agent if not provided)')
    
    # User and task arguments
    parser.add_argument('--user-id', default='test_user', help='User ID for progress tracking')
    parser.add_argument('--task-id', help='Task ID for progress tracking (auto-generated if not provided)')
    
    args = parser.parse_args()
    
    try:
        # Initialize agent
        agent = EarningsAndFutureAgent(
            redis_host=args.redis_host,
            redis_port=args.redis_port,
            redis_username=args.redis_username,
            redis_password=args.redis_password,
            collection_name=args.collection,
            openai_api_key=args.openai_key,
            user_id=args.user_id,
            task_id=args.task_id
        )
        
        # Process query
        if args.query:
            result = asyncio.run(agent.process_natural_query(args.query, args.ticker))
            print(f"\n✅ Analysis Complete!")
            print("=" * 60)
            print(json.dumps(result, indent=2))
            print("\n📝 Progress data preserved in database for Manager Agent cleanup")
        else:
            print("🤖 Earnings and Future Agent")
            print("Use --query to ask a question about earnings and future development")
            print("\nExamples:")
            print("  python Earnings_and_Future_Agent.py --query 'What are AAPL earnings and future plans?' --ticker AAPL")
            print("  python Earnings_and_Future_Agent.py --query 'Analyze TSLA earnings performance' --ticker TSLA")
    
    except Exception as e:
        logging.error(f"❌ Critical error: {e}")
        sys.exit(1)
    finally:
        if 'agent' in locals():
            agent.close()


if __name__ == "__main__":
    # Example usage
    # python Earnings_and_Future_Agent.py --query "What are AAPL earnings and future plans?" --ticker AAPL
    # python Earnings_and_Future_Agent.py --query "Analyze TSLA earnings performance" --ticker TSLA
    
    main()