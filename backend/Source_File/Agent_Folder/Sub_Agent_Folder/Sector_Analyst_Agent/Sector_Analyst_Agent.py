#!/usr/bin/env python3
"""
Sector Analyst Agent
Analyzes sector trends and competitor landscape for companies.
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
from Sector_Analyst_Read_Agent import SectorAnalystReadAgent

# COMPLETELY SILENT - No logging output
logging.basicConfig(
    level=logging.CRITICAL,  # Only show critical errors
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.NullHandler()  # No output at all
    ]
)

class SectorAnalystAgent:
    """
    Sector Analyst Agent - Processes sector analysis queries and stores results in database
    """
    
    def __init__(self, user_id: str = None, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None):
        """
        Initialize Sector Analyst Agent (Following same pattern as other agents)
        
        Args:
            user_id: User ID for database storage (if None, uses default)
            shared_clients: Shared client pool for connections
            redis_host (str): Redis host
            redis_port (int): Redis port
            redis_username (str): Redis username
            redis_password (str): Redis password
        """
        self.user_id = user_id
        if not self.user_id:
            raise ValueError("user_id is required - cannot use default user")
        
        self.shared_clients = shared_clients
        if not shared_clients:
            raise ValueError("shared_clients is required - cannot use hardcoded Redis connections")
        
        # Initialize Sector Analyst Read Agent with shared clients
        self.sector_read_agent = SectorAnalystReadAgent(
            shared_clients=shared_clients
        )
        logging.info("✅ Using shared Sector Analyst Read Agent")
        
        # Frontend Redis client for user results
        self.frontend_redis = shared_clients.get_frontend_redis()
        logging.info("✅ Using shared frontend Redis connection")
        
        # Database keys - Same structure as other agents
        self.sector_result_key = f"sector_analyst_result:{self.user_id}"
        self.sector_frontend_progress_key = f"sector_frontend_progress:{self.user_id}"
        
        logging.info("🤖 Sector Analyst Agent initialized")
        logging.info(f"👤 User ID: {self.user_id}")
        logging.info(f"📊 Frontend Database: Connected via shared_clients")
        logging.info(f"🔗 Integrated with: Sector Analyst Read Agent")
        logging.info(f"📋 Output Format: asset_relative, answer_collection, url_collection")
        logging.info(f"🗄️ Database Keys: {self.sector_result_key}, {self.sector_frontend_progress_key}")
        logging.info(f"🔄 Logic: Always keep latest (overwrite previous)")
    
    
    async def process_sector_analysis(self, ticker: str, user_query: str = None) -> Dict[str, Any]:
        """
        Process sector analysis for a given ticker and store in frontend Redis.
        
        Args:
            ticker (str): Stock ticker symbol
            user_query (str): Specific user question (optional)
            
        Returns:
            Dict[str, Any]: Sector analysis results with three keys:
                - asset_relative: What the company is relative to
                - answer_collection: Sector trend and competitor answers
                - url_collection: URLs for further research
        """
        try:
            logging.info(f"🔍 Processing sector analysis for {ticker}")
            if user_query:
                logging.info(f"❓ User query: {user_query}")
            
            # Update progress: Starting analysis
            await self._update_progress("Starting sector analysis...", 10)
            
            # Use the read agent to get sector analysis
            result = await self.sector_read_agent.process_sector_query(ticker)
            
            # Update progress: Analysis complete
            await self._update_progress("Sector analysis completed", 90)
            
            # If user provided a specific query, answer it directly
            if user_query and result.get("status") == "success":
                result = await self._answer_specific_query(ticker, user_query, result)
            
            # Store result in frontend Redis (same pattern as other agents)
            if result.get("status") == "success" and self.frontend_redis:
                await self._store_frontend_result(ticker, result, user_query)
            
            # Update progress: Complete
            await self._update_progress("Analysis complete", 100)
            
            logging.info(f"✅ Sector analysis completed for {ticker}")
            
            return result
            
        except Exception as e:
            logging.error(f"❌ Sector analysis failed for {ticker}: {e}")
            await self._update_progress(f"Analysis failed: {str(e)}", 0)
            return {
                "ticker": ticker,
                "asset_relative": "",
                "answer_collection": {},
                "url_collection": {},
                "error": str(e),
                "status": "failed"
            }
    
    async def _answer_specific_query(self, ticker: str, user_query: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer a specific user query using LLM analysis of the data.
        
        Args:
            ticker (str): Stock ticker symbol
            user_query (str): User's specific question
            analysis_data (Dict[str, Any]): Complete analysis data
            
        Returns:
            Dict[str, Any]: Modified result with direct answer to user query
        """
        try:
            logging.info(f"🎯 Answering specific query using LLM: '{user_query}' for {ticker}")
            
            # Extract relevant information
            asset_relative = analysis_data.get("asset_relative", "")
            sector_trend = analysis_data.get("answer_collection", {}).get("sector_trend", "")
            competitor_analysis = analysis_data.get("answer_collection", {}).get("company_competitor_landscape", "")
            
            # Use LLM to generate a direct answer to the user's specific question
            direct_answer = await self._generate_llm_answer(ticker, user_query, asset_relative, sector_trend, competitor_analysis)
            
            # Create a focused result that answers the user's question
            focused_result = {
                "ticker": ticker,
                "user_query": user_query,
                "direct_answer": direct_answer,
                "query_type": "specific_question",
                "asset_relative": asset_relative,
                "answer_collection": {
                    "sector_trend": sector_trend,
                    "company_competitor_landscape": competitor_analysis
                },
                "url_collection": analysis_data.get("url_collection", {}),
                "last_update": analysis_data.get("last_update", ""),
                "status": "success"
            }
            
            logging.info(f"✅ Generated LLM answer for query: '{user_query}'")
            return focused_result
            
        except Exception as e:
            logging.error(f"❌ Failed to answer specific query: {e}")
            raise e  # Fail completely if LLM doesn't work
    
    async def _generate_llm_answer(self, ticker: str, user_query: str, asset_relative: str, sector_trend: str, competitor_analysis: str) -> str:
        """
        Use LLM to generate a direct answer to the user's specific question.
        Follows the same pattern as other agents (Stock Trend Read Agent, etc.)
        
        Args:
            ticker (str): Stock ticker symbol
            user_query (str): User's specific question
            asset_relative (str): Company's market position
            sector_trend (str): Sector trend analysis
            competitor_analysis (str): Competitor landscape analysis
            
        Returns:
            str: LLM-generated direct answer
        """
        try:
            # Create a structured prompt for asset relative, landscape, and industrial trends
            prompt = f"""
Analyze this sector analysis data and provide a structured answer in the EXACT format below:

USER QUERY: "{user_query}"

SECTOR ANALYSIS DATA:
- Asset Relative: {asset_relative}
- Sector Trend Analysis: {sector_trend}
- Competitor Landscape Analysis: {competitor_analysis}

**REQUIRED OUTPUT FORMAT - ANSWER IN THIS EXACT STRUCTURE:**

<asset relative> [Extract 2-3 key words that best describe what the company is relative to]
<landscape> [Provide competitor landscape analysis with specific competitor names and market distribution]
<Industrial/Asset Trend> [Provide neutral industrial trends analysis focusing on advantages and disadvantages]

**CRITICAL REQUIREMENTS:**
- Use ONLY the exact data provided above
- Do NOT make up numbers, dates, or company names
- Keep response under 300 words total
- Be neutral and objective - no bias
- Focus on quick-to-see competitive insights
- Follow the EXACT format: <asset relative>, <landscape>, <Industrial/Asset Trend>

ANSWER:
"""

            # Use LLM agent (EXACT same pattern as Stock Trend Read Agent)
            analysis_response = self.sector_read_agent.llm_agent.call_llm(
                prompt=prompt,
                system_message="You are a neutral financial analyst specializing in sector analysis. Provide structured answers in the exact format: <asset relative> (2-3 words), <landscape>, <Industrial/Asset Trend>. Be objective, factual, and concise. Focus on quick-to-see competitive advantages and disadvantages.",
                max_tokens=400,
                temperature=0.3
            )
            
            logging.info(f"✅ LLM generated answer for query: '{user_query}'")
            return analysis_response
                
        except Exception as e:
            logging.error(f"❌ LLM answer generation failed: {e}")
            raise e  # Fail completely if LLM doesn't work
    
    async def get_sector_summary(self, ticker: str) -> Dict[str, Any]:
        """
        Get a summary of sector analysis for a ticker.
        
        Args:
            ticker (str): Stock ticker symbol
            
        Returns:
            Dict[str, Any]: Sector analysis summary
        """
        try:
            result = await self.process_sector_analysis(ticker)
            
            if result.get("status") == "success":
                return {
                    "ticker": ticker,
                    "asset_relative": result.get("asset_relative", ""),
                    "sector_trend_summary": result.get("answer_collection", {}).get("sector_trend", "")[:200] + "...",
                    "competitor_summary": result.get("answer_collection", {}).get("company_competitor_landscape", "")[:200] + "...",
                    "total_urls": len(result.get("url_collection", {}).get("sector_trend", [])) + 
                                 len(result.get("url_collection", {}).get("company_competitor_landscape", [])),
                    "status": "success"
                }
            else:
                return result
                
        except Exception as e:
            logging.error(f"❌ Sector summary failed for {ticker}: {e}")
            return {
                "ticker": ticker,
                "error": str(e),
                "status": "failed"
            }
    
    async def _update_progress(self, message: str, progress: int):
        """Update progress in frontend Redis (same pattern as other agents)."""
        try:
            if self.frontend_redis:
                progress_key = self.sector_frontend_progress_key
                progress_data = {
                    "message": message,
                    "progress": progress,
                    "timestamp": datetime.now().isoformat(),
                    "user_id": self.user_id
                }
                await self.frontend_redis.hset(progress_key, mapping=progress_data)
        except Exception as e:
            logging.warning(f"⚠️ Progress tracking failed: {e}")
    
    async def _store_frontend_result(self, ticker: str, result: Dict[str, Any], user_query: str = None):
        """Store user-specific query result with actual answers in frontend Redis."""
        try:
            if self.frontend_redis:
                # Create user-specific query result with actual answers
                user_query_result = {
                    "query_ticker": ticker,
                    "query_user_id": self.user_id,
                    "query_timestamp": datetime.now().isoformat(),
                    "query_status": result.get("status", "success"),
                    "agent_type": "sector_analyst",
                    
                    # USER'S SPECIFIC QUERY AND DIRECT ANSWER
                    "user_query": user_query if user_query else f"What is {ticker}'s sector analysis?",
                    "direct_answer": result.get("direct_answer", ""),
                    "query_type": result.get("query_type", "general_analysis"),
                    
                    # ACTUAL QUERY ANSWERS (what the user needs to see)
                    "query_answers": {
                        "asset_relative": result.get("asset_relative", ""),
                        "sector_trend_analysis": result.get("answer_collection", {}).get("sector_trend", ""),
                        "competitor_landscape_analysis": result.get("answer_collection", {}).get("company_competitor_landscape", ""),
                        "research_urls": {
                            "sector_trend_urls": result.get("url_collection", {}).get("sector_trend", []),
                            "competitor_landscape_urls": result.get("url_collection", {}).get("company_competitor_landscape", [])
                        }
                    },
                    
                    # QUERY SUMMARY (for quick reference)
                    "query_summary": {
                        "analysis_sections": list(result.get("answer_collection", {}).keys()),
                        "total_urls": sum(len(urls) for urls in result.get("url_collection", {}).values() if isinstance(urls, list)),
                        "last_update": result.get("last_update", ""),
                        "asset_relative_length": len(result.get("asset_relative", "")),
                        "sector_trend_length": len(result.get("answer_collection", {}).get("sector_trend", "")),
                        "competitor_analysis_length": len(result.get("answer_collection", {}).get("company_competitor_landscape", ""))
                    },
                    
                    # QUERY METADATA (for tracking)
                    "query_metadata": {
                        "ticker": ticker,
                        "user_id": self.user_id,
                        "timestamp": datetime.now().isoformat(),
                        "agent_type": "sector_analyst",
                        "query_type": "sector_analysis",
                        "result_source": "database_analysis"
                    }
                }
                
                result_key = self.sector_result_key
                result_data = json.dumps(user_query_result, default=str)
                
                await self.frontend_redis.set(result_key, result_data)
                await self.frontend_redis.expire(result_key, 30 * 24 * 60 * 60)  # 30 days
                
                logging.info(f"✅ Stored user query result with answers in frontend Redis for user {self.user_id}")
                logging.info(f"   - Query ticker: {ticker}")
                logging.info(f"   - Asset relative: {len(user_query_result['query_answers']['asset_relative'])} chars")
                logging.info(f"   - Sector trend: {len(user_query_result['query_answers']['sector_trend_analysis'])} chars")
                logging.info(f"   - Competitor analysis: {len(user_query_result['query_answers']['competitor_landscape_analysis'])} chars")
                logging.info(f"   - Total URLs: {user_query_result['query_summary']['total_urls']}")
        except Exception as e:
            logging.warning(f"⚠️ Frontend storage failed: {e}")
    
    async def get_user_results_count(self) -> int:
        """Get count of results for this user (same pattern as other agents)."""
        try:
            if not self.frontend_redis:
                return 0
            
            # Count result entries for this user
            result_keys = await self.frontend_redis.keys(f"sector_analyst_result:{self.user_id}")
            return len(result_keys)
            
        except Exception as e:
            logging.error(f"❌ Error counting user results: {e}")
            return 0
    
    async def close(self):
        """Close all connections and cleanup resources."""
        try:
            if self.db_agent:
                await self.db_agent.close()
            if self.frontend_redis:
                await self.frontend_redis.close()
            logging.info("✅ SectorAnalystAgent closed successfully")
        except Exception as e:
            logging.warning(f"⚠️ Error closing SectorAnalystAgent: {e}")

# Example usage
async def main():
    """Example usage of the Sector Analyst Agent."""
    
    # Initialize the agent
    agent = SectorAnalystAgent()
    
    # Test with a ticker
    ticker = "TEST"  # Default test ticker
    result = await agent.process_sector_analysis(ticker)
    
    print(f"Sector Analysis for {ticker}:")
    print(f"Asset Relative: {result.get('asset_relative', 'N/A')}")
    print(f"Answer Collection Keys: {list(result.get('answer_collection', {}).keys())}")
    print(f"URL Collection Keys: {list(result.get('url_collection', {}).keys())}")

if __name__ == "__main__":
    asyncio.run(main())
