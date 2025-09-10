#!/usr/bin/env python3
"""
Market Expectation Agent
Breaks down complex user queries into precise, callable queries for Stock Read Agent.
Outputs LLM analysis and timeline intervals for frontend graphing.
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
from Stock_Trend_Read_Agent import StockTrendAnalystAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('market_expectation.log')
    ]
)

@dataclass
class QueryBreakdown:
    """Data class for broken down query information."""
    original_query: str
    simplified_queries: List[str]
    query_type: str  # 'policy_change', 'earnings', 'product_launch', etc.
    affected_sectors: List[str]
    time_period: str  # 'recent', 'historical', 'all'
    confidence_score: float

@dataclass
class TimelineInterval:
    """Data class for timeline interval information."""
    start_date: str
    end_date: str
    trend_type: str  # 'uptrend', 'downtrend', 'volatile'
    importance_score: float  # 0-1, relevance to user query
    description: str
    key_events: List[str]

class MarketExpectationAgent:
    """
    Market Expectation Agent - Breaks down complex queries and generates precise analysis.
    """
    
    def __init__(self, progress_context=None, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None, 
                 collection_name: str = "Stock_Trend_INFOS", openai_api_key: str = None,
                 user_id: str = None, task_id: str = None):
        """
        Initialize Market Expectation Agent with progress tracking.
        
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
        
        # Frontend Redis Database (Separate from stock trend database)
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
        
        # Initialize Redis client for database operations (original stock trend database)
        if shared_clients:
            self.redis_client = shared_clients.get_stock_trend_redis()
            logging.info("✅ Using shared stock trend Redis connection")
        elif redis_host and redis_port:
            try:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    username=redis_username,
                    password=redis_password,
                    decode_responses=True
                )
                logging.info(f"✅ Stock trend Redis connected: {redis_host}:{redis_port}")
            except Exception as e:
                logging.warning(f"⚠️ Stock trend Redis connection failed: {e}")
                self.redis_client = None
        else:
            self.redis_client = None
        
        # LLM agent removed - no longer needed for CoT preprocessing
        
        # Initialize Stock Read Agent
        self.stock_read_agent = None
        if shared_clients or (redis_host and redis_port):
            try:
                self.stock_read_agent = StockTrendAnalystAgent(
                    shared_clients=shared_clients,
                    redis_host=redis_host,
                    redis_port=redis_port,
                    redis_username=redis_username,
                    redis_password=redis_password
                )
                logging.info("✅ Stock Read Agent initialized")
            except Exception as e:
                logging.warning(f"⚠️ Stock Read Agent initialization failed: {e}")
        
        logging.info(f"🚀 Market Expectation Agent initialized for user {self.user_id}, task {self.task_id}")
    
    def _update_progress(self, step: str, status: str, progress: int = None, details: str = ""):
        """
        Update progress in Frontend Redis - separate from stock trend database.
        
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
                "agent": "market_expectation"  # Identify this agent's data
            }
            
            # Store progress update in frontend Redis - separate from stock trend database
            progress_key = f"market_expectation_frontend_progress:{self.user_id}"
            
            # Get existing progress data
            existing_data = self.frontend_redis.hgetall(progress_key)
            
            # Create updated data structure
            updated_data = {}
            
            # Keep existing data from other agents
            for key, value in existing_data.items():
                try:
                    data = json.loads(value)
                    # Only keep data from other agents
                    if data.get("agent") != "market_expectation":
                        updated_data[key] = value
                except:
                    # Keep non-JSON data (legacy)
                    updated_data[key] = value
            
            # Add/update Market Expectation Agent data
            market_expectation_key = f"market_expectation:{step}"
            updated_data[market_expectation_key] = json.dumps(progress_data)
            
            # Store all data back to Frontend Redis
            if updated_data:
                self.frontend_redis.hset(progress_key, mapping=updated_data)
            
            # Set expiry to clean up old progress (24 hours)
            self.frontend_redis.expire(progress_key, 86400)
            
            logging.info(f"📊 Frontend Progress Update: {step} - {status} ({progress}%) - Agent: Market Expectation")
            
        except Exception as e:
            logging.error(f"❌ Failed to update frontend progress: {e}")
    
    def _get_progress(self) -> dict:
        """Get current progress from Frontend Redis - includes all agents."""
        if not self.frontend_redis:
            return {}
        
        try:
            progress_key = f"market_expectation_frontend_progress:{self.user_id}"
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
            progress_key = f"market_expectation_frontend_progress:{self.user_id}"
            self.frontend_redis.delete(progress_key)
            logging.info(f"🧹 Market Expectation Frontend Progress cleared for user {self.user_id}")
        except Exception as e:
            logging.error(f"❌ Failed to clear frontend progress: {e}")
    
    def _store_market_result(self, result: dict, ticker: str) -> bool:
        """
        Store market expectation result in Frontend Redis.
        
        Args:
            result: Market expectation analysis result
            ticker: Stock ticker symbol
            
        Returns:
            bool: Success status
        """
        if not self.frontend_redis:
            logging.warning("⚠️ Frontend Redis not available for market result storage")
            return False
        
        try:
            # Add metadata to result
            market_result = {
                **result,
                'user_id': self.user_id,
                'task_id': self.task_id,
                'ticker': ticker,
                'agent': 'market_expectation_agent',
                'created_at': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(days=30)).isoformat()  # 30 days expiry
            }
            
            # Create single key per user ID (only one result per user)
            market_result_key = f"market_expectation_result:{self.user_id}"
            
            # Store in Frontend Redis (overwrites previous result for same user)
            self.frontend_redis.set(market_result_key, json.dumps(market_result))
            
            # Set expiry (30 days)
            self.frontend_redis.expire(market_result_key, 2592000)  # 30 days in seconds
            
            logging.info(f"✅ Market result stored in Frontend Redis: {market_result_key}")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to store market result in Frontend Redis: {e}")
            return False
    
    def _get_market_results(self, user_id: str = None, task_id: str = None, ticker: str = None) -> list:
        """
        Get market expectation results from Frontend Redis.
        
        Args:
            user_id: User ID (defaults to current user)
            task_id: Task ID (defaults to current task)
            ticker: Stock ticker symbol (optional filter)
            
        Returns:
            list: Market expectation results
        """
        if not self.frontend_redis:
            return []
        
        try:
            user_id = user_id or self.user_id
            
            # Get the single result for this user
            market_result_key = f"market_expectation_result:{user_id}"
            data = self.frontend_redis.get(market_result_key)
            
            if data:
                result = json.loads(data)
                # Filter by ticker if specified
                if ticker and result.get('ticker') != ticker:
                    return []
                return [result]
            
            return []
            
        except Exception as e:
            logging.error(f"❌ Failed to get market results from Frontend Redis: {e}")
            return []
    
    def scoped_db_find(self, collection: str, query: dict = None) -> list:
        """
        Find documents in database with user and task scoping.
        
        Args:
            collection (str): Collection name
            query (dict): Query filter (will be enhanced with user/task scoping)
            
        Returns:
            list: Scoped results
        """
        if not self.redis_client:
            return []
        
        try:
            # Enhance query with user/task scoping
            scoped_query = {
                'user_id': self.user_id,
                'task_id': self.task_id,
                **(query or {})
            }
            
            # Search for matching keys
            pattern = f"{collection}:{self.user_id}:{self.task_id}:*"
            keys = self.redis_client.keys(pattern)
            
            results = []
            for key in keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        result = json.loads(data)
                        # Check if result matches query
                        if self._matches_query(result, scoped_query):
                            results.append(result)
                except Exception as e:
                    logging.warning(f"⚠️ Failed to parse result {key}: {e}")
            
            return results
            
        except Exception as e:
            logging.error(f"❌ Error in scoped_db_find: {e}")
            return []
    
    def scoped_db_insert(self, collection: str, data: dict, key_suffix: str = None) -> bool:
        """
        Insert document into database with user and task scoping.
        
        Args:
            collection (str): Collection name
            data (dict): Data to insert
            key_suffix (str): Optional key suffix for uniqueness
            
        Returns:
            bool: Success status
        """
        if not self.redis_client:
            return False
        
        try:
            # Add user and task scoping to data
            scoped_data = {
                **data,
                'user_id': self.user_id,
                'task_id': self.task_id,
                'sub_agent': 'market_expectation_agent',
                'created_at': datetime.now().isoformat()
            }
            
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
            self.progress_context.report_progress("market_expectation", progress, step, status)
    
    # CoT preprocessing removed - user queries pass through directly to Stock Read Agent
    
    async def call_stock_read_agent(self, preprocessed_query: str, ticker: str) -> Dict:
        """
        Call Stock Read Agent with enhanced query and track progress.
        
        Args:
            preprocessed_query: Enhanced query with trend direction
            ticker: Stock ticker symbol
            
        Returns:
            Dict: Stock read agent result
        """
        try:
            self._update_progress("Query to Read Agent", "started", 40, f"Calling Read Agent for {ticker}")
            
            # Enhance query with trend direction
            enhanced_query = self._enhance_query_with_trend_direction(preprocessed_query, ticker)
            
            self._update_progress("Query to Read Agent", "in_progress", 45, "Enhanced query with trend direction")
            
            # Call Stock Read Agent
            if self.stock_read_agent:
                result = await self.stock_read_agent.process_natural_query(enhanced_query, ticker)
                self._update_progress("Query to Read Agent", "completed", 50, "Successfully called Read Agent")
            else:
                # Fallback if Stock Read Agent is not available
                result = {
                    "status": "error",
                    "message": "Stock Read Agent not available",
                    "data": {}
                }
                self._update_progress("Query to Read Agent", "failed", 50, "Stock Read Agent not available")
            
            return {
                "original_query": preprocessed_query,
                "enhanced_query": enhanced_query,
                "stock_read_result": result
            }
            
        except Exception as e:
            self._update_progress("Query to Read Agent", "failed", 50, str(e))
            logging.error(f"❌ Error calling Stock Read Agent: {e}")
            raise e
    
    def _enhance_query_with_trend_direction(self, preprocessed_query: str, ticker: str) -> str:
        """
        Enhance the preprocessed query to be more explicit about trend direction.
        
        Args:
            preprocessed_query (str): Original preprocessed query
            ticker (str): Stock ticker symbol
            
        Returns:
            str: Enhanced query with explicit trend direction
        """
        query_lower = preprocessed_query.lower()
        
        # Check if the query already contains trend direction keywords
        if 'uptrend' in query_lower:
            return preprocessed_query
        elif 'downtrend' in query_lower:
            return preprocessed_query
        
        # Analyze the query for negative/positive indicators
        negative_indicators = [
            'cancel', 'ban', 'restrict', 'regulation', 'miss', 'decline', 'drop', 'fall',
            'negative', 'bearish', 'downtrend', 'downward', 'decrease', 'loss', 'penalty',
            'fine', 'investigation', 'lawsuit', 'litigation', 'case', 'crypto policy',
            'regulatory uncertainty', 'policy restrictions', 'earnings miss'
        ]
        
        positive_indicators = [
            'support', 'approve', 'launch', 'beat', 'growth', 'positive', 'bullish',
            'uptrend', 'upward', 'increase', 'gain', 'profit', 'deregulation',
            'policy support', 'earnings beat', 'product launch', 'technology release'
        ]
        
        # Count negative and positive indicators
        negative_count = sum(1 for indicator in negative_indicators if indicator in query_lower)
        positive_count = sum(1 for indicator in positive_indicators if indicator in query_lower)
        
        # Determine trend direction
        if negative_count > positive_count:
            # Add explicit downtrend request
            if 'analyze' in query_lower:
                enhanced_query = query_lower.replace('analyze', 'analyze DOWNTRENDS for')
            else:
                enhanced_query = f"Analyze {ticker} stock DOWNTRENDS during {query_lower}"
            logging.info(f"🔻 Enhanced query for DOWNTREND analysis: {enhanced_query}")
            
        elif positive_count > negative_count:
            # Add explicit uptrend request
            if 'analyze' in query_lower:
                enhanced_query = query_lower.replace('analyze', 'analyze UPTRENDS for')
            else:
                enhanced_query = f"Analyze {ticker} stock UPTRENDS during {query_lower}"
            logging.info(f"🔺 Enhanced query for UPTREND analysis: {enhanced_query}")
            
        else:
            # If unclear, request both trends
            enhanced_query = f"Analyze {ticker} stock BOTH UPTRENDS AND DOWNTRENDS during {query_lower}"
            logging.info(f"🔄 Enhanced query for BOTH trend analysis: {enhanced_query}")
        
        return enhanced_query
    
    def extract_timeline_intervals(self, stock_read_result: Dict) -> List[TimelineInterval]:
        """
        Extract timeline intervals from Stock Read Agent result.
        
        Args:
            stock_read_result (Dict): Result from Stock Read Agent
            
        Returns:
            List[TimelineInterval]: Timeline intervals for graphing
        """
        logging.info(f"📅 Extracting timeline intervals from Stock Read Agent result")
        
        timeline_intervals = []
        
        try:
            # Handle different possible result structures
            result_text = None
            
            # Check if it's a string directly
            if isinstance(stock_read_result, str):
                result_text = stock_read_result
            # Check if it has a 'result' key
            elif isinstance(stock_read_result, dict) and "result" in stock_read_result:
                result_text = stock_read_result["result"]
            # Check if it has a 'stock_read_result' key (from call_stock_read_agent)
            elif isinstance(stock_read_result, dict) and "stock_read_result" in stock_read_result:
                result_text = stock_read_result["stock_read_result"]
            # Check if it has an 'error' key
            elif isinstance(stock_read_result, dict) and stock_read_result.get("error"):
                logging.warning(f"⚠️ Stock read result contains error: {stock_read_result.get('error')}")
                return timeline_intervals
            # If it's a dict, try to convert to string
            elif isinstance(stock_read_result, dict):
                result_text = str(stock_read_result)
            else:
                logging.warning(f"⚠️ Unexpected stock_read_result type: {type(stock_read_result)}")
                return timeline_intervals
            
            if result_text:
                # Parse the result to extract timeline information
                intervals = self._parse_result_for_intervals(result_text)
                timeline_intervals.extend(intervals)
                logging.info(f"✅ Successfully parsed {len(intervals)} intervals from result")
            else:
                logging.warning(f"⚠️ No result text found in stock_read_result")
            
        except Exception as e:
            logging.error(f"❌ Error extracting intervals from result: {e}")
            logging.error(f"   - Result type: {type(stock_read_result)}")
            logging.error(f"   - Result keys: {list(stock_read_result.keys()) if isinstance(stock_read_result, dict) else 'N/A'}")
        
        # Sort by importance score
        timeline_intervals.sort(key=lambda x: x.importance_score, reverse=True)
        
        logging.info(f"✅ Extracted {len(timeline_intervals)} timeline intervals")
        return timeline_intervals
    
    def _parse_result_for_intervals(self, result: str) -> List[TimelineInterval]:
        """Parse Stock Read Agent result to extract timeline intervals."""
        import re
        intervals = []
        
        if not result or not isinstance(result, str):
            logging.warning(f"⚠️ Invalid result for parsing: {type(result)}")
            return intervals
        
        # Look for date patterns in the result
        date_patterns = [
            # Standard date formats
            r'(\d{4}-\d{2}-\d{2})\s*to\s*(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{2}-\d{2})\s*-\s*(\d{4}-\d{2}-\d{2})',
            r'(\d{4}/\d{2}/\d{2})\s*to\s*(\d{4}/\d{2}/\d{2})',
            # MM/DD/YYYY format
            r'(\d{1,2}/\d{1,2}/\d{4})\s*to\s*(\d{1,2}/\d{1,2}/\d{4})',
            # Date ranges with different separators
            r'(\d{4}-\d{2}-\d{2})\s*through\s*(\d{4}-\d{2}-\d{2})',
            r'(\d{4}-\d{2}-\d{2})\s*until\s*(\d{4}-\d{2}-\d{2})',
            # Single dates (for current trends)
            r'(\d{4}-\d{2}-\d{2})',
            r'(\d{1,2}/\d{1,2}/\d{4})'
        ]
        
        found_dates = set()  # To avoid duplicates
        
        for pattern in date_patterns:
            matches = re.findall(pattern, result)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2:
                        start_date, end_date = match
                    else:
                        continue
                else:
                    # Single date match
                    start_date = match
                    # For single dates, use a 7-day period
                    try:
                        start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                        end_dt = start_dt + timedelta(days=7)
                        end_date = end_dt.strftime('%Y-%m-%d')
                    except ValueError:
                        try:
                            start_dt = datetime.strptime(start_date, '%m/%d/%Y')
                            end_dt = start_dt + timedelta(days=7)
                            end_date = end_dt.strftime('%Y-%m-%d')
                            start_date = start_dt.strftime('%Y-%m-%d')
                        except ValueError:
                            continue
                
                # Create a unique key for this date range
                date_key = f"{start_date}_{end_date}"
                if date_key in found_dates:
                    continue
                found_dates.add(date_key)
                
                # Basic date format validation and normalization
                try:
                    # Try YYYY-MM-DD format
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
                except ValueError:
                    try:
                        # Try MM/DD/YYYY format
                        start_dt = datetime.strptime(start_date, '%m/%d/%Y')
                        end_dt = datetime.strptime(end_date, '%m/%d/%Y')
                        # Convert to YYYY-MM-DD
                        start_date = start_dt.strftime('%Y-%m-%d')
                        end_date = end_dt.strftime('%Y-%m-%d')
                    except ValueError:
                        logging.warning(f"⚠️ Invalid date format: {start_date} to {end_date}")
                        continue
                
                # Determine trend type from context
                trend_type = self._determine_trend_type(result, start_date, end_date)
                
                # Calculate importance score
                importance_score = self._calculate_importance_score(result, start_date, end_date)
                
                # Extract description
                description = self._extract_description(result, start_date, end_date)
                
                # Extract key events
                key_events = self._extract_key_events(result, start_date, end_date)
                
                interval = TimelineInterval(
                    start_date=start_date,
                    end_date=end_date,
                    trend_type=trend_type,
                    importance_score=importance_score,
                    description=description,
                    key_events=key_events
                )
                
                intervals.append(interval)
                logging.info(f"📅 Found interval: {start_date} to {end_date} ({trend_type})")
        
        return intervals
    
    def _determine_trend_type(self, result: str, start_date: str, end_date: str) -> str:
        """Determine trend type from context."""
        context = result.lower()
        
        if any(word in context for word in ['uptrend', 'positive', 'gain', 'rise', 'increase']):
            return 'uptrend'
        elif any(word in context for word in ['downtrend', 'negative', 'loss', 'fall', 'decrease']):
            return 'downtrend'
        else:
            return 'volatile'
    
    def _calculate_importance_score(self, result: str, start_date: str, end_date: str) -> float:
        """Calculate importance score based on relevance indicators."""
        score = 0.5  # Base score
        
        # Increase score for relevant keywords
        relevant_keywords = ['policy', 'regulation', 'crypto', 'earnings', 'announcement']
        for keyword in relevant_keywords:
            if keyword in result.lower():
                score += 0.1
        
        # Increase score for recent dates
        try:
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            days_ago = (datetime.now() - end_dt).days
            if days_ago < 365:  # Within last year
                score += 0.2
        except:
            pass
        
        return min(score, 1.0)
    
    def _extract_description(self, result: str, start_date: str, end_date: str) -> str:
        """Extract description for the timeline interval."""
        # Look for trend type in the context
        context = result.lower()
        if any(word in context for word in ['uptrend', 'positive', 'gain', 'rise']):
            return "Uptrend period"
        elif any(word in context for word in ['downtrend', 'negative', 'loss', 'fall']):
            return "Downtrend period"
        else:
            return "Volatile period"
    
    def _extract_key_events(self, result: str, start_date: str, end_date: str) -> List[str]:
        """Extract key events for the timeline interval."""
        events = []
        
        # Look for specific event keywords
        context = result.lower()
        if 'earnings' in context:
            events.append("Earnings announcement")
        if 'policy' in context or 'regulation' in context:
            events.append("Policy change")
        if 'launch' in context:
            events.append("Product launch")
        if 'announcement' in context:
            events.append("Company announcement")
        
        return events[:2]  # Limit to 2 key events
    
    def create_standard_timeline_json(self, timeline_intervals: List[TimelineInterval]) -> List[List[str]]:
        """
        Create simple timeline JSON - just the most relevant time interval.
        
        Args:
            timeline_intervals (List[TimelineInterval]): Timeline intervals
            
        Returns:
            List[List[str]]: Simple format [[start_date, end_date]] - just one interval
        """
        if not timeline_intervals:
            return []
        
        # Sort by importance score and take the most relevant interval
        timeline_intervals.sort(key=lambda x: x.importance_score, reverse=True)
        most_relevant = timeline_intervals[0]
        
        # Convert dates to MM/DD/YYYY format
        start_date = self._convert_date_format(most_relevant.start_date)
        end_date = self._convert_date_format(most_relevant.end_date)
        
        # Return just one interval: [[start_date, end_date]]
        return [[start_date, end_date]]
    
    def _convert_date_format(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to MM/DD/YYYY format."""
        try:
            # Parse the date
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            # Return in MM/DD/YYYY format
            return date_obj.strftime('%m/%d/%Y')
        except:
            # If parsing fails, return original
            return date_str
    
    # LLM analysis method removed - no longer needed
    
    async def process_query(self, query: str, ticker: str) -> Dict:
        """
        Main method to process market expectation analysis.
        
        Args:
            query (str): Complex user query
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict: Complete analysis result with Stock Read Agent analysis only
        """
        try:
            self._update_progress("starting analysis", "started", 10)
            
            # Step 1: Use original query directly (no CoT preprocessing)
            self._update_progress("processing query", "started", 20)
            preprocessed_query = query  # Use original query directly
            
            # Log the query
            logging.info(f"🎯 Original Query: {query}")
            logging.info(f"🎯 Query sent to Stock Read Agent: {preprocessed_query}")
            
            # Step 2: Call Stock Read Agent with original query
            self._update_progress("calling stock read agent", "started", 40)
            stock_read_wrapper = await self.call_stock_read_agent(preprocessed_query, ticker)
            
            # Extract the actual Stock Read Agent response
            stock_read_result = stock_read_wrapper.get("stock_read_result", "No result available")
            
            # Step 3: Create final result with Stock Read Agent analysis only (no LLM analysis)
            self._update_progress("creating final result", "started", 80)
            result = {
                "original_query": query,
                "ticker": ticker,
                "preprocessed_query": preprocessed_query,
                "stock_read_result": stock_read_result,  # Direct output from Stock Read Agent
                "completed_at": datetime.now().isoformat()
            }
            
            # Store result in Frontend Redis (separate from stock trend database)
            self._store_market_result(result, ticker)
            
            self._update_progress("analysis complete", "completed", 100)
            
            logging.info(f"✅ Market expectation analysis completed for {ticker}")
            logging.info(f"   - User ID: {self.user_id}")
            logging.info(f"   - Task ID: {self.task_id}")
            logging.info(f"   - Stored in Frontend Redis: ✅")
            return result
            
        except Exception as e:
            logging.error(f"❌ Error in market expectation analysis: {e}")
            self._update_progress("analysis failed", "failed", 0, str(e))
            raise e
    
    def close(self):
        """Close the database connection."""
        if self.stock_read_agent:
            self.stock_read_agent.close()
        logging.info("🔚 Market Expectation Agent closed")

    def get_workflow_progress(self) -> dict:
        """
        Get complete workflow progress for frontend display - includes all agents.
        
        Returns:
            dict: Complete workflow progress with all steps from all agents
        """
        progress = self._get_progress()
        
        # Define workflow steps in order (Market Expectation Agent specific)
        market_expectation_steps = [
            "starting analysis",
            "processing query", 
            "calling stock read agent",
            "creating final result",
            "analysis complete"
        ]
        
        # Calculate Market Expectation Agent progress
        completed_steps = 0
        total_steps = len(market_expectation_steps)
        
        for step in market_expectation_steps:
            step_key = f"market_expectation:{step}"
            if step_key in progress:
                step_data = progress[step_key]
                if step_data.get("status") in ["completed", "in_progress"]:
                    completed_steps += 1
        
        market_expectation_progress = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        # Create workflow summary with all agents
        workflow_summary = {
            "user_id": self.user_id,
            "task_id": self.task_id,
            "overall_progress": market_expectation_progress,
            "completed_steps": completed_steps,
            "total_steps": total_steps,
            "current_step": "Unknown",
            "workflow_steps": [],
            "all_agents_progress": progress,  # Include all agents' data
            "timestamp": datetime.now().isoformat()
        }
        
        # Add each step with its status
        for step in market_expectation_steps:
            step_key = f"market_expectation:{step}"
            step_data = progress.get(step_key, {
                "step": step,
                "status": "pending",
                "progress": 0,
                "details": "Not started",
                "agent": "market_expectation"
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
            "preprocessing query with CoT": "Processing Query",
            "calling stock read agent": "Query to Read Agent",
            "extracting timeline intervals": "Extracting Timeline",
            "generating comprehensive analysis": "Generating Analysis", 
            "creating standardized timeline": "Creating Timeline",
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
        
        # Add Market Expectation Agent steps
        for step_data in workflow["workflow_steps"]:
            step_name = step_data.get("step", "")
            frontend_step = {
                "name": step_descriptions.get(step_name, step_name),
                "status": step_data.get("status", "pending"),
                "progress": step_data.get("progress", 0),
                "details": step_data.get("details", ""),
                "timestamp": step_data.get("timestamp", ""),
                "agent": "market_expectation"
            }
            frontend_progress["steps"].append(frontend_step)
        
        # Add data from other agents
        all_agents_data = workflow.get("all_agents_progress", {})
        for key, data in all_agents_data.items():
            if isinstance(data, dict) and data.get("agent") != "market_expectation":
                agent_name = data.get("agent", "unknown")
                if agent_name not in frontend_progress["all_agents"]:
                    frontend_progress["all_agents"][agent_name] = []
                frontend_progress["all_agents"][agent_name].append(data)
        
        return frontend_progress


def main():
    """Main function to run Market Expectation Agent with progress tracking."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Market Expectation Agent with Progress Tracking')
    parser.add_argument('--query', required=True, help='User query')
    parser.add_argument('--ticker', required=True, help='Stock ticker symbol')
    parser.add_argument('--user-id', default='test_user', help='User ID for progress tracking')
    parser.add_argument('--task-id', default=None, help='Task ID (auto-generated if not provided)')
    parser.add_argument('--redis-host', default='redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com', help='Redis host')
    parser.add_argument('--redis-port', type=int, default=16376, help='Redis port')
    parser.add_argument('--redis-password', default='rl8242B4UItBhFzgHW5APEqZnkYoaEZv', help='Redis password')
    parser.add_argument('--show-progress', action='store_true', help='Show progress updates during execution')
    
    args = parser.parse_args()
    
    # Initialize Market Expectation Agent with progress tracking
    agent = MarketExpectationAgent(
        redis_host=args.redis_host,
        redis_port=args.redis_port,
        redis_password=args.redis_password,
        user_id=args.user_id,
        task_id=args.task_id
    )
    
    try:
        print(f"🚀 Starting Market Expectation Analysis")
        print(f"   - Query: {args.query}")
        print(f"   - Ticker: {args.ticker}")
        print(f"   - User ID: {args.user_id}")
        print(f"   - Task ID: {agent.task_id}")
        print(f"   - Progress Tracking: {'Enabled' if agent.progress_redis else 'Disabled'}")
        print()
        
        # Start progress tracking
        agent._update_progress("starting analysis", "started", 0, "Initializing Market Expectation Agent")
        
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
    # python Market_Expectation_Agent.py --query "If trump cancel crypto policy how will the market move on stock COINBASE" --ticker COIN
    main() 