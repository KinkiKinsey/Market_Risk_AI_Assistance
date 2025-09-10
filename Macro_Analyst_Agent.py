#!/usr/bin/env python3
"""
Macro Analyst Agent
Analyzes macro-economic queries and provides comprehensive analysis.
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
from typing import Dict, List, Any, Optional, Union
import redis
from dataclasses import dataclass
from pathlib import Path
import asyncio
import re

# Import existing agents
from Macro_Read_Agent import MacroReadAgent

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('macro_analyst_agent.log')
    ]
)

class MacroAnalystAgent:
    """
    Macro Analyst Agent - Processes macro queries and stores results in user database
    """
    
    def __init__(self, user_id: str = None, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None):
        """
        Initialize Macro Analyst Agent (Standardized to match other agents)
        
        Args:
            user_id: User ID for database storage (if None, uses default)
            redis_host: Redis host (if None, uses default)
            redis_port: Redis port (if None, uses default)
            redis_username: Redis username (if None, uses default)
            redis_password: Redis password (if None, uses default)
        """
        self.user_id = user_id or "default_user"
        
        # Frontend Redis Database (Same as other agents)
        self.frontend_redis_host = redis_host or "redis-16204.fcrce180.us-east-1-1.ec2.redns.redis-cloud.com"
        self.frontend_redis_port = redis_port or 16204
        self.frontend_redis_username = redis_username or "default"
        self.frontend_redis_password = redis_password or "9rHiMKl63iYK9ja4qja6ZjnamuixS4UG"
        
        # Initialize Macro Read Agent with stock trend Redis (for data storage)
        if shared_clients:
            self.macro_read_agent = MacroReadAgent(
                shared_clients=shared_clients
            )
            logging.info("✅ Using shared Macro Read Agent")
        else:
            self.macro_read_agent = MacroReadAgent(
                redis_host="redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
                redis_port=16376,
                redis_username="default",
                redis_password="rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
            )
            logging.info("✅ Using individual Macro Read Agent")
        
        # Frontend Redis client for user results (same as other agents)
        if shared_clients:
            self.frontend_redis = shared_clients.get_frontend_redis()
            logging.info("✅ Using shared frontend Redis connection")
        else:
            self.frontend_redis = None
            self._connect_frontend_redis()
        
        # Database keys - Same structure as other agents
        self.macro_result_key = f"macro_analyst_result:{self.user_id}"
        self.macro_frontend_progress_key = f"macro_frontend_progress:{self.user_id}"
        
        print(f"🤖 Macro Analyst Agent initialized")
        print(f"👤 User ID: {self.user_id}")
        print(f"📊 Frontend Database: {self.frontend_redis_host}:{self.frontend_redis_port}")
        print(f"🔗 Integrated with: Macro Read Agent")
        print(f"📋 Output Format: FACT → EVIDENCE → RESULT structure")
        print(f"🗄️ Database Keys: {self.macro_result_key}, {self.macro_frontend_progress_key}")
        print(f"🔄 Logic: Always keep latest (overwrite previous)")
    
    def _connect_frontend_redis(self):
        """Connect to Frontend Redis (same as other agents)"""
        try:
            self.frontend_redis = redis.Redis(
                host=self.frontend_redis_host,
                port=self.frontend_redis_port,
                username=self.frontend_redis_username,
                password=self.frontend_redis_password,
                decode_responses=True
            )
            self.frontend_redis.ping()
            print(f"✅ Frontend Redis connected: {self.frontend_redis_host}:{self.frontend_redis_port}")
        except Exception as e:
            print(f"❌ Frontend Redis connection failed: {e}")
            self.frontend_redis = None
    
    async def process_macro_query(self, query: str) -> Dict[str, Any]:
        """
        Process macro query and return structured analysis (Standardized to match other agents)
        
        Args:
            query: User's macro analysis question
            
        Returns:
            Dict containing analysis results (simplified structure like other agents)
        """
        try:
            print(f"🔍 Processing macro query: {query}")
            
            # Update progress: Starting analysis
            self._update_progress("starting analysis", "started", 10, f"Initializing macro analysis for query: {query[:50]}...")
            
            # Update progress: Calling Macro Read Agent
            self._update_progress("calling macro read agent", "started", 30, "Connecting to Macro Read Agent")
            print("📡 Calling Macro Read Agent...")
            
            # Call Macro Read Agent (now async)
            analysis_response = await self.macro_read_agent.process_user_query(query)
            
            if not analysis_response:
                self._update_progress("calling macro read agent", "failed", 30, "No response from Macro Read Agent")
                return {
                    'llm_response': 'No response from Macro Read Agent',
                    'query': query,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Update progress: Processing response
            self._update_progress("processing response", "started", 60, "Processing LLM analysis response")
            
            # Create simplified result structure (matching other agents)
            result = {
                'llm_response': analysis_response,  # Standardized key like other agents
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✅ Query processed successfully")
            print(f"📊 Response length: {len(analysis_response)} characters")
            
            # Store result (simplified)
            self._store_macro_result(result)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing macro query: {str(e)}"
            logging.error(error_msg)
            self._update_progress("processing query", "failed", 0, f"Error: {error_msg}")
            return {
                'llm_response': f'Error: {error_msg}',
                'query': query,
                'timestamp': datetime.now().isoformat()
            }
    
    def _update_progress(self, step: str, status: str, progress: int = None, details: str = ""):
        """
        Update progress in Frontend Redis - same structure as other agents
        
        Args:
            step: Current step (e.g., "calling macro read agent", "generating analysis")
            status: Status (e.g., "started", "completed", "failed")
            progress: Progress percentage (0-100)
            details: Additional details
        """
        if not self.frontend_redis:
            print("⚠️ Frontend Redis not available for progress tracking")
            return
        
        try:
            progress_data = {
                "user_id": self.user_id,
                "step": step,
                "status": status,
                "progress": progress,
                "details": details,
                "timestamp": datetime.now().isoformat(),
                "agent": "macro_analyst"  # Identify this agent's data
            }
            
            # Store progress update in Frontend Redis - same structure as other agents
            progress_key = self.macro_frontend_progress_key
            
            try:
                # Check if key exists and is a hash, if not, delete it
                key_type = self.frontend_redis.type(progress_key)
                if key_type != 'hash' and key_type != 'none':
                    print(f"⚠️ Key {progress_key} exists as {key_type}, deleting to recreate as hash")
                    self.frontend_redis.delete(progress_key)
                
                # Get existing progress data
                existing_data = self.frontend_redis.hgetall(progress_key)
                
                # Create updated data structure
                updated_data = {}
                
                # Keep existing data from other agents
                for key, value in existing_data.items():
                    try:
                        data = json.loads(value)
                        # Only keep data from other agents
                        if data.get("agent") != "macro_analyst":
                            updated_data[key] = value
                    except:
                        # Keep non-JSON data (legacy)
                        updated_data[key] = value
                
                # Add/update Macro Analyst Agent data
                macro_key = f"macro_analyst:{step}"
                updated_data[macro_key] = json.dumps(progress_data)
                
                # Store all data back to Frontend Redis
                if updated_data:
                    self.frontend_redis.hset(progress_key, mapping=updated_data)
                    
            except Exception as e:
                print(f"⚠️ Progress tracking failed, continuing without it: {e}")
                # Continue execution even if progress tracking fails
            
            # Set expiry to clean up old progress (24 hours)
            self.frontend_redis.expire(progress_key, 86400)
            
            print(f"📊 Progress Update: {step} - {status} ({progress}%)")
            
        except Exception as e:
            print(f"❌ Failed to update progress: {e}")
            logging.error(f"Progress update error: {e}")

    def _store_macro_result(self, result: Dict[str, Any]):
        """
        Store macro result in Frontend Redis (same as other agents)
        
        Args:
            result: Simplified result from process_macro_query
        """
        try:
            if not self.frontend_redis:
                print("⚠️ Frontend Redis not connected. Continuing without storage.")
                return
            
            # Store result in Frontend Redis (same as other agents)
            result_key = self.macro_result_key
            result_data = json.dumps(result, default=str)
            
            self.frontend_redis.set(result_key, result_data)
            self.frontend_redis.expire(result_key, 30 * 24 * 60 * 60)  # 30 days
            
            # Update progress: Analysis complete
            self._update_progress("analysis complete", "completed", 100, "Macro analysis completed successfully")
            
            print(f"✅ Macro result stored in Frontend Redis: {result_key}")
            
        except Exception as e:
            print(f"⚠️ Failed to store macro result: {e}")
            logging.error(f"Store macro result error: {e}")
    
    def _get_total_analyses_count(self) -> int:
        """Get total count of stored analyses"""
        try:
            if not self.frontend_redis:
                return 0
            
            # Count result entries for this user
            result_keys = self.frontend_redis.keys(f"macro_analyst_result:{self.user_id}")
            return len(result_keys)
            
        except Exception as e:
            logging.error(f"Error counting analyses: {e}")
            return 0
    
    def get_user_macro_analysis(self) -> Dict[str, Any]:
        """
        Get current macro analysis for user from Frontend Redis
        
        Returns:
            Dict containing current analysis or error
        """
        try:
            if not self.frontend_redis:
                return {'error': 'Frontend Redis not connected'}
            
            # Get current analysis from Frontend Redis
            result_data = self.frontend_redis.get(self.macro_result_key)
            if not result_data:
                return {'error': 'No current analysis found'}
            
            current_analysis = json.loads(result_data)
            
            # Get progress data from Frontend Redis
            progress_data = self.frontend_redis.get(self.macro_frontend_progress_key)
            progress = json.loads(progress_data) if progress_data else {}
            
            return {
                'current_analysis': current_analysis,
                'progress': progress,
                'retrieved_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': f'Error retrieving analysis: {str(e)}'}
    

    
    def run_macro_analysis(self, query: str) -> Dict[str, Any]:
        """
        Complete macro analysis workflow: process query and store result
        
        Args:
            query: User's macro analysis question
            
        Returns:
            Dict containing analysis result and storage status
        """
        try:
            print(f"🚀 Starting macro analysis workflow...")
            print(f"=" * 50)
            
            # Step 1: Process query
            print(f"📝 Step 1: Processing query...")
            analysis_result = self.process_macro_query(query)
            
            if not analysis_result.get('success'):
                print(f"❌ Query processing failed: {analysis_result.get('error')}")
                return analysis_result
            
            print(f"✅ Query processed successfully")
            
            # Step 2: Store result
            print(f"💾 Step 2: Storing analysis...")
            storage_success = self.store_macro_analysis(analysis_result)
            
            if storage_success:
                print(f"✅ Analysis stored successfully")
                analysis_result['stored'] = True
                analysis_result['storage_timestamp'] = datetime.now().isoformat()
            else:
                print(f"⚠️ Analysis storage failed")
                analysis_result['stored'] = False
            
            print(f"🎉 Macro analysis workflow completed!")
            print(f"=" * 50)
            
            return analysis_result
            
        except Exception as e:
            error_msg = f"Error in macro analysis workflow: {str(e)}"
            logging.error(error_msg)
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat(),
                'query': query
            }

def main():
    """
    Main execution function - Command Line Query Input
    """
    import sys
    import argparse
    
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Macro Analyst Agent - Process macro queries')
    parser.add_argument('--queries', '-q', type=str, help='Macro analysis query')
    parser.add_argument('--user-id', '-u', type=str, default='default_user', help='User ID for database storage')
    
    # Parse arguments
    args = parser.parse_args()
    
    # Check if query provided
    if not args.queries:
        print("❌ No query provided!")
        print("Usage: python3 Macro_Analyst_Agent.py --queries 'Your macro question here'")
        print("Example: python3 Macro_Analyst_Agent.py --queries 'Why did PLTR go down recently?'")
        print("Or: python3 Macro_Analyst_Agent.py -q 'What economic indicators are available?'")
        sys.exit(1)
    
    try:
        # Initialize agent
        user_id = args.user_id
        agent = MacroAnalystAgent(user_id=user_id)
        
        # Run analysis workflow
        print(f"🔍 Processing query: {args.queries}")
        result = agent.run_macro_analysis(args.queries)
        
        if result.get('success'):
            print(f"\n📊 ANALYSIS RESULT:")
            print(f"Query: {result['query']}")
            print(f"Timestamp: {result['timestamp']}")
            print(f"Stored: {result.get('stored', False)}")
            print(f"\n{result['analysis']}")
        else:
            print(f"❌ Analysis failed: {result.get('error')}")
        
        print("="*50)
        print("✅ Analysis completed!")
                
    except Exception as e:
        print(f"❌ Main execution failed: {e}")
        logging.error(f"Main execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
