#!/usr/bin/env python3
"""
Macro Read Agent
Reads and analyzes macro-economic data using LLM.
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
from LLM_Call_Agent import LLMCallAgent
from Macro_DB_Agent import MacroDBAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('macro_read_agent.log')
    ]
)

class MacroReadAgent:
    """
    Macro Read Agent - Reads queries and provides macro data answers
    """
    
    def __init__(self, shared_clients=None, redis_host: str = None, redis_port: int = None, 
                 redis_username: str = "default", redis_password: str = None):
        """Initialize Macro Read Agent"""
        self.macro_analyst_key = "Macro_INFOS:Macro_Analyst"
        self.macro_data_key = "Macro_INFOS:Macro_Data"
        self.weekly_threshold = 7  # 7 days
        
        # Initialize Macro DB Agent (standard pattern like other agents)
        self.macro_db_agent = MacroDBAgent(
            shared_clients=shared_clients,
            redis_host=redis_host,
            redis_port=redis_port,
            redis_username=redis_username,
            redis_password=redis_password
        )
        
        # 🚀 NEW: Use shared clients instead of creating individual LLM client
        try:
            from shared_clients import shared_clients
            self.llm_client = shared_clients
            print(f"🤖 Macro Read Agent (Shared Clients) initialized")
        except ImportError:
            # Fallback to individual client if shared_clients not available
            from LLM_Call_Agent import LLMCallAgent
            self.llm_client = LLMCallAgent(
                default_provider="deepseek", 
                default_model="deepseek-chat"
            )
            print(f"🤖 Macro Read Agent (Individual Client) initialized")
        print(f"📊 Will read from: {self.macro_analyst_key}")
        print(f"📈 Data source: {self.macro_data_key}")
        print(f"🔄 Weekly update threshold: {self.weekly_threshold} days")
        print(f"🧠 LLM Integration: DeepSeek (via {'Shared Clients' if 'shared_clients' in str(type(self.llm_client)) else 'LLM_Call_Agent'})")
        print(f"📋 Output Format: FACT → EVIDENCE → RESULT structure")
        print(f"📋 Always 2 sections: OPPORTUNITY & RISK")
        # Check API keys based on client type
        if hasattr(self.llm_client, 'get_status'):
            # Using shared clients
            status = self.llm_client.get_status()
            # Check both direct clients and legacy LLM agent
            deepseek_available = (status.get('deepseek_client_available', False) or 
                                (status.get('use_legacy_llm_agent', False) and status.get('llm_call_agent_available', False)))
            openai_available = (status.get('openai_client_available', False) or 
                              (status.get('use_legacy_llm_agent', False) and status.get('llm_call_agent_available', False)))
            print(f"🔑 DeepSeek API Key: {'✅ Available' if deepseek_available else '❌ Missing'}")
            print(f"🔑 OpenAI API Key: {'✅ Available' if openai_available else '❌ Missing'}")
        else:
            # Using individual LLM client
            print(f"🔑 DeepSeek API Key: {'✅ Available' if hasattr(self.llm_client, 'deepseek_api_key') and self.llm_client.deepseek_api_key else '❌ Missing'}")
            print(f"🔑 OpenAI API Key: {'✅ Available' if hasattr(self.llm_client, 'openai_api_key') and self.llm_client.openai_api_key else '❌ Missing'}")
        print(f"🗄️ Macro DB Agent: {'✅ Available' if self.macro_db_agent else '❌ Missing'}")
    
    async def check_data_freshness(self) -> Dict[str, Any]:
        """
        Check if macro data is fresh by reading meta_data from Macro_Analyst file (async version)
        
        Returns:
            Dict containing freshness status and metadata
        """
        try:
            print("🔍 Checking macro data freshness...")
            
            # Try to import redis to check the file
            try:
                import redis
                
                # Redis configuration (stock trend Redis for data storage)
                redis_config = {
                    "host": "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
                    "port": 16376,
                    "username": "default",
                    "password": "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
                }
                
                # Connect to Redis (run in thread to avoid blocking)
                def _check_redis():
                    redis_client = redis.Redis(
                        host=redis_config["host"],
                        port=redis_config["port"],
                        username=redis_config["username"],
                        password=redis_config["password"],
                        decode_responses=True
                    )
                
                    # Check if Macro_Analyst file exists
                    analyst_data = redis_client.get(self.macro_analyst_key)
                    
                    if not analyst_data:
                        return {
                            'status': 'no_data',
                            'message': 'No macro analyst data found',
                            'needs_update': True,
                            'metadata': None
                        }
                    
                    # Parse the data and check metadata
                    try:
                        parsed_data = json.loads(analyst_data)
                        
                        if 'meta_data' not in parsed_data:
                            return {
                                'status': 'no_metadata',
                                'message': 'No metadata found in macro analyst data',
                                'needs_update': True,
                                'metadata': None
                            }
                        
                        metadata = parsed_data['meta_data']
                        last_update_time = metadata.get('last_update_time')
                        
                        if not last_update_time:
                            return {
                                'status': 'no_timestamp',
                                'message': 'No update timestamp found',
                                'needs_update': True,
                                'metadata': None
                            }
                        
                        # Check weekly update rule
                        current_time = datetime.now()
                        last_update = datetime.fromisoformat(last_update_time)
                        days_since_update = (current_time - last_update).days
                        
                        is_fresh = days_since_update < self.weekly_threshold
                        next_update_due = last_update + timedelta(days=self.weekly_threshold)
                        
                        if is_fresh:
                            status = 'fresh'
                            message = f'Data is fresh for {self.weekly_threshold - days_since_update} more days'
                            needs_update = False
                        else:
                            status = 'stale'
                            message = f'Data is {days_since_update - self.weekly_threshold} days overdue for update'
                            needs_update = True
                        
                        return {
                            'status': status,
                            'message': message,
                            'needs_update': needs_update,
                            'metadata': metadata,
                            'days_since_update': days_since_update,
                            'next_update_due': next_update_due.isoformat(),
                            'last_update': last_update_time
                        }
                        
                    except json.JSONDecodeError:
                        return {
                            'status': 'parse_error',
                            'message': 'Error parsing macro analyst data',
                            'needs_update': True,
                            'metadata': None
                        }
                
                return await asyncio.to_thread(_check_redis)
                    
            except ImportError:
                # Redis not available, assume update needed
                return {
                    'status': 'redis_unavailable',
                    'message': 'Redis not available, update needed',
                    'needs_update': True,
                    'metadata': None
                }
                
        except Exception as e:
            logging.error(f"Error checking data freshness: {e}")
            return {
                'status': 'error',
                'message': f'Error checking data freshness: {str(e)}',
                'needs_update': True,
                'metadata': None
            }
    
    async def trigger_macro_update(self) -> bool:
        """
        Trigger Macro DB Agent update using direct method call (standard pattern)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            print("🚀 Triggering Macro DB Agent update...")
            print("📡 Using direct method call (standard pattern)")
            
            # Use direct method call instead of subprocess (like other agents)
            if hasattr(self.macro_db_agent, 'force_macro_update'):
                print("🔄 Calling force_macro_update() method...")
                # Run sync method in thread to avoid blocking
                update_success = await self.macro_db_agent.force_macro_update()
                
                if update_success:
                    print("✅ Macro DB Agent update completed successfully!")
                    print("📊 Macro data updated and ready for queries!")
                    return True
                else:
                    print("❌ Macro DB Agent force update failed")
                    return False
            else:
                print("❌ Macro DB Agent doesn't have force_macro_update method")
                return False
                
        except Exception as e:
            print(f"❌ Error triggering macro update: {e}")
            logging.error(f"Error triggering macro update: {e}")
            return False
    
    async def read_macro_data(self) -> Dict[str, Any]:
        """
        Read macro data from Redis database (async version)
        
        Returns:
            Dict containing macro data and analysis
        """
        try:
            print("📖 Reading macro data from database...")
            
            import redis
            
            # Redis configuration (stock trend Redis for data storage)
            redis_config = {
                "host": "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
                "port": 16376,
                "username": "default",
                "password": "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
            }
            
            # Connect to Redis (run in thread to avoid blocking)
            def _read_redis():
                redis_client = redis.Redis(
                    host=redis_config["host"],
                    port=redis_config["port"],
                    username=redis_config["username"],
                    password=redis_config["password"],
                    decode_responses=True
                )
                
                # Read both files
                analyst_data = redis_client.get(self.macro_analyst_key)
                macro_data = redis_client.get(self.macro_data_key)
                
                if not analyst_data or not macro_data:
                    return {
                        'error': 'Missing macro data files',
                        'analyst_exists': analyst_data is not None,
                        'data_exists': macro_data is not None
                    }
                
                # Parse the data
                try:
                    analyst_parsed = json.loads(analyst_data)
                    macro_parsed = json.loads(macro_data)
                    
                    return {
                        'analyst': analyst_parsed,
                        'macro_data': macro_parsed,
                        'metadata': analyst_parsed.get('meta_data', {}),
                        'analysis': analyst_parsed.get('analysis', ''),
                        'indicators': macro_parsed.keys()
                    }
                    
                except json.JSONDecodeError as e:
                    return {
                        'error': f'Error parsing data: {str(e)}',
                        'analyst_data': analyst_data[:200] + '...' if analyst_data else None,
                        'macro_data': macro_data[:200] + '...' if macro_data else None
                    }
                    
            return await asyncio.to_thread(_read_redis)
                
        except ImportError:
            return {
                'error': 'Redis not available',
                'solution': 'Install redis package: pip install redis'
            }
        except Exception as e:
            logging.error(f"Error reading macro data: {e}")
            return {
                'error': f'Error reading macro data: {str(e)}'
            }
    
    async def process_user_query(self, user_query: str) -> str:
        """
        Process user query and provide relevant macro data information (Standardized to async)
        
        Args:
            user_query: User's question about macro data
            
        Returns:
            str: Answer based on macro data
        """
        try:
            print(f"🤔 Processing user query: {user_query}")
            
            # First check data freshness
            freshness_status = await self.check_data_freshness()
            
            if freshness_status['needs_update']:
                print(f"⚠️ {freshness_status['message']}")
                print("🔄 Data needs update. Triggering Macro DB Agent...")
                
                # Trigger update (now async)
                update_success = await self.trigger_macro_update()
                
                if update_success:
                    print("✅ Update completed. Now processing query...")
                    # Re-read data after update
                    macro_data = await self.read_macro_data()
                else:
                    return "❌ Failed to update macro data. Cannot process query."
            else:
                print(f"✅ {freshness_status['message']}")
                print("📖 Reading existing macro data...")
                macro_data = await self.read_macro_data()
            
            # Process query based on available data
            if 'error' in macro_data:
                return f"❌ Error reading macro data: {macro_data['error']}"
            
            # Extract relevant information
            analysis = macro_data.get('analysis', '')
            metadata = macro_data.get('metadata', {})
            indicators = list(macro_data.get('indicators', []))
            
            # Remove meta_data from indicators list
            if 'meta_data' in indicators:
                indicators.remove('meta_data')
            
            # Generate LLM-powered response
            response = await self._generate_llm_response(user_query, analysis, metadata, indicators)
            
            return response
            
        except Exception as e:
            error_msg = f"Error processing user query: {str(e)}"
            logging.error(error_msg)
            return f"❌ {error_msg}"
    
    def close(self):
        """Close connections (standard pattern like other agents)"""
        try:
            if hasattr(self, 'macro_db_agent') and self.macro_db_agent:
                # Close Macro DB Agent connections if it has a close method
                if hasattr(self.macro_db_agent, 'close'):
                    self.macro_db_agent.close()
                print("✅ Macro Read Agent connections closed")
        except Exception as e:
            print(f"⚠️ Error closing Macro Read Agent: {e}")

    async def _generate_llm_response(self, query: str, analysis: str, metadata: Dict, indicators: List[str]) -> str:
        """
        Generate intelligent LLM-powered response based on user query and macro data (async)
        
        Args:
            query: User's natural language question
            analysis: LLM analysis from macro data
            metadata: Metadata about the data
            indicators: List of available economic indicators
            
        Returns:
            str: AI-generated response
        """
        try:
            print("🤖 Generating LLM-powered response...")
            
            # Prepare context for LLM
            context = self._prepare_llm_context(analysis, metadata, indicators)
            
            # Create LLM prompt
            prompt = self._create_llm_prompt(query, context)
            
            # Call DeepSeek LLM (run in thread to avoid blocking)
            print("📡 Calling DeepSeek LLM...")
            
            # 🚀 NEW: Handle both shared clients and individual clients
            if hasattr(self.llm_client, 'call_deepseek'):
                if asyncio.iscoroutinefunction(self.llm_client.call_deepseek):
                    # Using shared clients (async)
                    llm_response = await self.llm_client.call_deepseek(prompt)
                else:
                    # Using individual client (sync) - wrap in thread
                    llm_response = await asyncio.to_thread(self.llm_client.call_deepseek, prompt)
            else:
                # Fallback to direct call
                llm_response = await asyncio.to_thread(self.llm_client.call_deepseek, prompt)
            
            if llm_response:
                print("✅ LLM response generated successfully!")
                return llm_response
            else:
                print("⚠️ LLM call failed, falling back to template response")
                return self._generate_fallback_response(query, analysis, metadata, indicators)
                
        except Exception as e:
            print(f"⚠️ LLM generation failed: {e}, using fallback")
            logging.error(f"LLM generation error: {e}")
            return self._generate_fallback_response(query, analysis, metadata, indicators)

    def _prepare_llm_context(self, analysis: str, metadata: Dict, indicators: List[str]) -> str:
        """
        Prepare context information for LLM processing
        """
        context_parts = []
        
        # Add analysis
        if analysis:
            context_parts.append(f"MACRO ECONOMIC ANALYSIS:\n{analysis}")
        
        # Add metadata
        if metadata:
            context_parts.append(f"DATA METADATA:\n- Last Update: {metadata.get('last_update_time', 'Unknown')}")
            context_parts.append(f"- Data Range: {metadata.get('data_range', {}).get('start_date', 'Unknown')} to {metadata.get('data_range', {}).get('end_date', 'Unknown')}")
            context_parts.append(f"- Total Indicators: {metadata.get('total_indicators', len(indicators))}")
            context_parts.append(f"- Data Quality: {metadata.get('data_quality', {}).get('total_data_points', 'Unknown')} data points")
        
        # Add indicators
        if indicators:
            context_parts.append(f"AVAILABLE ECONOMIC INDICATORS:\n{', '.join(indicators)}")
        
        return "\n\n".join(context_parts)

    def _create_llm_prompt(self, query: str, context: str) -> str:
        """
        Create comprehensive prompt for LLM with consistent output format
        """
        return f"""You are an expert financial analyst specializing in macroeconomics and market analysis. You have access to comprehensive macro economic data and analysis.

USER QUERY: {query}

AVAILABLE MACRO DATA AND CONTEXT:
{context}

CRITICAL OUTPUT FORMAT REQUIREMENT:
You MUST structure your response in EXACTLY 2 sections with FACT → EVIDENCE → RESULT format:

1. **OPPORTUNITY** - Structured analysis of positive aspects
2. **RISK** - Structured analysis of risk factors

STRUCTURED ANALYSIS FORMAT:
For each section, use this exact structure:

**OPPORTUNITY**
• **FACT:** [Specific macro economic fact]
  - **EVIDENCE:** [Data point/indicator value]
  - **RESULT:** [How this creates opportunity]

• **FACT:** [Another macro economic fact]
  - **EVIDENCE:** [Data point/indicator value]
  - **RESULT:** [How this creates opportunity]

**RISK**
• **FACT:** [Specific macro economic fact]
  - **EVIDENCE:** [Data point/indicator value]
  - **RESULT:** [How this creates risk]

• **FACT:** [Another macro economic fact]
  - **EVIDENCE:** [Data point/indicator value]
  - **RESULT:** [How this creates risk]

ANALYSIS INSTRUCTIONS:
1. Use ONLY the actual macro data provided
2. Each FACT must be a specific economic condition
3. Each EVIDENCE must include actual data values
4. Each RESULT must explain the direct impact
5. Be concise and data-driven
6. Maximum 3-4 facts per section

Always provide both sections with this exact structure for every query."""

    def _generate_fallback_response(self, query: str, analysis: str, metadata: Dict, indicators: List[str]) -> str:
        """
        Generate fallback response when LLM fails - maintains consistent format
        """
        return f"""📊 **Response to: {query}**

🤖 **LLM Analysis Unavailable** - Using Template Response

**OPPORTUNITY**
• **FACT:** Macro data is available for analysis
  - **EVIDENCE:** {len(indicators)} economic indicators with {metadata.get('data_quality', {}).get('total_data_points', 'Unknown')} data points
  - **RESULT:** Comprehensive data foundation exists for analysis

• **FACT:** Recent data coverage available
  - **EVIDENCE:** Data range: {metadata.get('data_range', {}).get('start_date', 'Unknown')} to {metadata.get('data_range', {}).get('end_date', 'Unknown')}
  - **RESULT:** Current economic conditions are captured

**RISK**
• **FACT:** LLM analysis service unavailable
  - **EVIDENCE:** Cannot process intelligent queries
  - **RESULT:** Limited to basic data display only

• **FACT:** No contextual analysis possible
  - **EVIDENCE:** Cannot relate data to specific questions
  - **RESULT:** Missing intelligent insights and recommendations

💡 **Note:** For structured FACT → EVIDENCE → RESULT analysis, please ensure the LLM service is available."""

    def _generate_response(self, query: str, analysis: str, metadata: Dict, indicators: List[str]) -> str:
        """
        Generate response based on user query and macro data
        
        Args:
            query: User's question
            analysis: LLM analysis text
            metadata: Metadata from macro data
            indicators: List of available indicators
            
        Returns:
            str: Formatted response
        """
        query_lower = query.lower()
        
        # Check for specific query types
        if any(word in query_lower for word in ['update', 'fresh', 'recent', 'when']):
            return self._format_update_info(metadata)
        
        elif any(word in query_lower for word in ['indicator', 'data', 'what', 'available']):
            return self._format_indicators_info(indicators, metadata)
        
        elif any(word in query_lower for word in ['analysis', 'summary', 'overview']):
            return self._format_analysis_info(analysis, metadata)
        
        elif any(word in query_lower for word in ['range', 'period', 'dates']):
            return self._format_date_range_info(metadata)
        
        else:
            # General response with all available info
            return self._format_general_response(analysis, metadata, indicators)
    
    def _format_update_info(self, metadata: Dict) -> str:
        """Format update information"""
        last_update = metadata.get('last_update_time', 'Unknown')
        indicators_count = metadata.get('total_indicators', 0)
        
        return f"""📅 **Update Information:**
• Last Update: {last_update}
• Total Indicators: {indicators_count}
• Data Quality: {metadata.get('data_quality', {}).get('total_data_points', 'Unknown')} data points"""
    
    def _format_indicators_info(self, indicators: List[str], metadata: Dict) -> str:
        """Format indicators information"""
        indicators_str = '\n• '.join(indicators)
        total = len(indicators)
        
        return f"""📊 **Available Economic Indicators ({total}):**
• {indicators_str}

📈 **Data Summary:**
• Total Indicators: {metadata.get('total_indicators', total)}
• Date Range: {metadata.get('data_range', {}).get('start_date', 'Unknown')} to {metadata.get('data_range', {}).get('end_date', 'Unknown')}"""
    
    def _format_analysis_info(self, analysis: str, metadata: Dict) -> str:
        """Format analysis information"""
        analysis_preview = analysis[:500] + '...' if len(analysis) > 500 else analysis
        
        return f"""🤖 **Macro Economic Analysis:**
{analysis_preview}

📊 **Analysis Details:**
• Length: {len(analysis)} characters
• Last Update: {metadata.get('last_update_time', 'Unknown')}"""
    
    def _format_date_range_info(self, metadata: Dict) -> str:
        """Format date range information"""
        data_range = metadata.get('data_range', {})
        start_date = data_range.get('start_date', 'Unknown')
        end_date = data_range.get('end_date', 'Unknown')
        
        return f"""📅 **Data Coverage Period:**
• Start Date: {start_date}
• End Date: {end_date}
• Last Update: {metadata.get('last_update_time', 'Unknown')}"""
    
    def _format_general_response(self, analysis: str, metadata: Dict, indicators: List[str]) -> str:
        """Format general response with all information"""
        indicators_str = '\n• '.join(indicators[:10])  # Show first 10
        if len(indicators) > 10:
            indicators_str += f"\n• ... and {len(indicators) - 10} more"
        
        analysis_preview = analysis[:300] + '...' if len(analysis) > 300 else analysis
        
        return f"""📊 **Macro Economic Data Overview:**

📈 **Available Indicators ({len(indicators)}):**
• {indicators_str}

📅 **Data Coverage:**
• Period: {metadata.get('data_range', {}).get('start_date', 'Unknown')} to {metadata.get('data_range', {}).get('end_date', 'Unknown')}
• Last Update: {metadata.get('last_update_time', 'Unknown')}
• Total Data Points: {metadata.get('data_quality', {}).get('total_data_points', 'Unknown')}

🤖 **Economic Analysis Preview:**
{analysis_preview}

💡 **Tip:** Ask specific questions about indicators, analysis, or data freshness for more detailed information."""

def main():
    """
    Main execution function - supports command line queries
    """
    import sys
    
    print("🚀 MACRO READ AGENT")
    print("=" * 50)
    
    try:
        # Initialize the agent
        agent = MacroReadAgent()
        
        # Check if query provided as command line argument
        if len(sys.argv) > 1:
            # Check for help command
            if sys.argv[1].lower() in ['--help', '-h', 'help']:
                print("💡 MACRO READ AGENT - USAGE GUIDE")
                print("=" * 50)
                print("📝 Command Line Usage:")
                print("  python3 Macro_Read_Agent.py 'Your question here'")
                print("")
                print("📝 Examples:")
                print("  python3 Macro_Read_Agent.py 'What economic indicators are available?'")
                print("  python3 Macro_Read_Agent.py 'When was the data last updated?'")
                print("  python3 Macro_Read_Agent.py 'Show me the macro analysis'")
                print("  python3 Macro_Read_Agent.py 'What is the data coverage period?'")
                print("")
                print("📝 Interactive Mode:")
                print("  python3 Macro_Read_Agent.py")
                print("  (No arguments = interactive chat mode)")
                print("")
                print("📝 Help:")
                print("  python3 Macro_Read_Agent.py --help")
                print("  python3 Macro_Read_Agent.py -h")
                return
            
            # Command line query mode
            user_query = ' '.join(sys.argv[1:])  # Join all arguments after script name
            print(f"🤔 Processing query: {user_query}")
            print("=" * 50)
            
            # Process the query
            response = agent.process_user_query(user_query)
            print(response)
            
        else:
            # Interactive mode (no arguments provided)
            print("💡 Usage: python3 Macro_Read_Agent.py 'Your question here'")
            print("💡 Example: python3 Macro_Read_Agent.py 'What economic indicators are available?'")
            print("\n🔍 No query provided. Entering interactive mode...")
            print("=" * 50)
            
            # Check data freshness
            print("\n🔍 Checking data freshness...")
            freshness = agent.check_data_freshness()
            print(f"Status: {freshness['status']}")
            print(f"Message: {freshness['message']}")
            print(f"Needs Update: {freshness['needs_update']}")
            
            if freshness['metadata']:
                print(f"Last Update: {freshness['metadata'].get('last_update_time', 'Unknown')}")
            
            # Example queries
            print("\n📝 Example Queries (LLM-Powered):")
            print("1. 'What economic indicators are available?'")
            print("2. 'Show me the macro analysis'")
            print("3. 'When was the data last updated?'")
            print("4. 'What is the data coverage period?'")
            print("5. 'Why did PLTR go down recently, based on macro factors?'")
            print("6. 'How do inflation trends affect tech stocks?'")
            print("7. 'What macro risks should I watch for?'")
            print("\n📋 Every response will have 2 sections: OPPORTUNITY & RISK")
            
            # Interactive mode
            print("\n💬 Interactive Mode (type 'quit' to exit):")
            while True:
                try:
                    user_input = input("\n🤔 Your question: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        print("👋 Goodbye!")
                        break
                    
                    if user_input:
                        print("\n" + "="*50)
                        response = agent.process_user_query(user_input)
                        print(response)
                        print("="*50)
                    else:
                        print("⚠️ Please enter a question.")
                        
                except KeyboardInterrupt:
                    print("\n👋 Goodbye!")
                    break
                except EOFError:
                    print("\n👋 Goodbye!")
                    break
                    
    except Exception as e:
        print(f"❌ Main execution failed: {e}")
        logging.error(f"Main execution error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
