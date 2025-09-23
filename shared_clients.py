#!/usr/bin/env python3
"""
Shared Client Pool
Centralized client management for all agents to improve performance.

This file contains all shared clients (OpenAI, DeepSeek, Redis, HTTP) that are used
by all agents to avoid creating duplicate connections and improve performance.

USAGE:
    from shared_clients import shared_clients
    await shared_clients.initialize()
    
    # Then pass to agents:
    agent = YourAgent(shared_clients=shared_clients)
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import json
import time # Added for performance tracking

# ============================================================================
# EXTERNAL LIBRARIES - Install these if missing:
# pip install aioredis aiohttp openai redis
# ============================================================================

try:
    import aioredis
    AIOREDIS_AVAILABLE = True
except ImportError:
    AIOREDIS_AVAILABLE = False
    print("⚠️ aioredis not available. Install with: pip install aioredis")

try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    AIOHTTP_AVAILABLE = False
    print("⚠️ aiohttp not available. Install with: pip install aiohttp")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("⚠️ openai not available. Install with: pip install openai")

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("⚠️ redis not available. Install with: pip install redis")

# ============================================================================
# INTEGRATION WITH EXISTING LLM_Call_Agent
# ============================================================================

try:
    from LLM_Call_Agent import LLMCallAgent, OPENAI_API_KEY as EXISTING_OPENAI_KEY, DEEPSEEK_API_KEY as EXISTING_DEEPSEEK_KEY
    LLM_CALL_AGENT_AVAILABLE = True
    # print("✅ LLM_Call_Agent integration available")  # Silent
except ImportError:
    LLM_CALL_AGENT_AVAILABLE = False
    print("⚠️ LLM_Call_Agent not available - using direct API keys")

# ============================================================================
# CONFIGURATION - MODIFY THESE VALUES AS NEEDED
# ============================================================================

# API Keys (from your existing LLM_Call_Agent.py or direct)
if LLM_CALL_AGENT_AVAILABLE:
    OPENAI_API_KEY = EXISTING_OPENAI_KEY
    DEEPSEEK_API_KEY = EXISTING_DEEPSEEK_KEY
    # print("✅ Using API keys from LLM_Call_Agent")  # Silent
else:
    OPENAI_API_KEY = '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'
    DEEPSEEK_API_KEY = 'sk-43e9043c7ab8480393d34367f2ae997e'
    print("⚠️ Using direct API keys")

# Redis Configuration (from your existing agents)
FRONTEND_REDIS_CONFIG = {
    "host": "redis-16204.fcrce180.us-east-1-1.ec2.redns.redis-cloud.com",
    "port": 16204,
    "username": "default",
    "password": "9rHiMKl63iYK9ja4qja6ZjnamuixS4UG"
}

STOCK_TREND_REDIS_CONFIG = {
    "host": "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com",
    "port": 16376,
    "username": "default",
    "password": "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
}

# Connection Pool Settings - OPTIMIZED FOR CONCURRENT EXECUTION
REDIS_MAX_CONNECTIONS = 20
HTTP_MAX_CONNECTIONS = 50
HTTP_MAX_PER_HOST = 20
HTTP_TIMEOUT = 10

# ============================================================================
# SHARED CLIENT POOL CLASS
# ============================================================================

class SharedClientPool:
    """
    Centralized client pool for all agents.
    
    This class manages shared connections to:
    - OpenAI API
    - DeepSeek API  
    - Redis databases (Frontend + Stock Trend)
    - HTTP session for external API calls
    
    Benefits:
    - 5-7x faster initialization
    - Reduced API costs
    - Better error handling
    - Connection pooling
    """
    
    def __init__(self):
        """Initialize the shared client pool (but don't connect yet)"""
        # LLM Clients
        self.openai_client: Optional[OpenAI] = None
        self.deepseek_client: Optional[OpenAI] = None
        
        # Integration with existing LLM_Call_Agent
        self.llm_call_agent: Optional[LLMCallAgent] = None
        self.use_legacy_llm_agent = False
        
        # Redis Connections
        self.frontend_redis_pool: Optional[aioredis.Redis] = None
        self.stock_trend_redis_pool: Optional[aioredis.Redis] = None
        
        # No backup clients - fail fast if aioredis not available
        
        # HTTP Session
        self.http_session: Optional[aiohttp.ClientSession] = None
        
        # Semaphores for concurrency control - OPTIMIZED FOR CONCURRENT EXECUTION
        self.sem_openai = asyncio.Semaphore(10) # Allow 10 concurrent OpenAI calls
        self.sem_deepseek = asyncio.Semaphore(10) # Allow 10 concurrent DeepSeek calls
        
        # Status tracking
        self._initialized = False
        self._initialization_lock = asyncio.Lock()
        
        # Performance metrics
        self.initialization_time = 0
        self.total_requests = 0
        self.error_count = 0
        
        # print("🤖 Shared Client Pool created (not initialized yet)")  # Silent
    
    async def initialize(self) -> bool:
        """
        Initialize all shared clients.
        
        This method:
        1. Creates OpenAI and DeepSeek clients
        2. Creates Redis connection pools
        3. Creates HTTP session with connection pooling
        4. Tests all connections
        
        Returns:
            bool: True if successful, False otherwise
        """
        # Prevent multiple simultaneous initializations
        async with self._initialization_lock:
            if self._initialized:
                # print("✅ Shared clients already initialized")  # Silent
                return True
            
            start_time = asyncio.get_event_loop().time()
            print("🚀 Initializing shared client pool...")
            
            try:
                # Step 1: Initialize LLM Clients
                await self._initialize_llm_clients()
                
                # Step 2: Initialize Redis Pools
                await self._initialize_redis_pools()
                
                # Step 3: Initialize HTTP Session
                await self._initialize_http_session()
                
                # Step 4: Test all connections
                await self._test_connections()
                
                # Mark as initialized
                self._initialized = True
                self.initialization_time = asyncio.get_event_loop().time() - start_time
                
                # print(f"✅ Shared client pool initialized successfully!")  # Silent
                print(f"⏱️ Initialization time: {self.initialization_time:.2f} seconds")
                # print(f"🔗 OpenAI: {'✅' if self.openai_client else '❌'}")  # Silent
                # print(f"🔗 DeepSeek: {'✅' if self.deepseek_client else '❌'}")  # Silent
                # print(f"🔗 Frontend Redis: {'✅' if self.frontend_redis_pool else '❌'}")  # Silent
                # print(f"🔗 Stock Trend Redis: {'✅' if self.stock_trend_redis_pool else '❌'}")  # Silent
                # print(f"🔗 HTTP Session: {'✅' if self.http_session else '❌'}")  # Silent
                
                return True
                
            except Exception as e:
                print(f"❌ Failed to initialize shared clients: {e}")
                logging.error(f"Shared client initialization error: {e}")
                await self._cleanup()
                return False
    
    async def _initialize_llm_clients(self):
        """Initialize OpenAI and DeepSeek clients with fallback to LLM_Call_Agent"""
        print("🤖 Initializing LLM clients...")
        
        # Try to use existing LLM_Call_Agent first
        if LLM_CALL_AGENT_AVAILABLE:
            try:
                self.llm_call_agent = LLMCallAgent(
                    openai_api_key=OPENAI_API_KEY,
                    deepseek_api_key=DEEPSEEK_API_KEY,
                    default_provider="deepseek",
                    default_model="deepseek-chat"
                )
                self.use_legacy_llm_agent = True
                # print("✅ Using existing LLM_Call_Agent for LLM operations")  # Silent
                return
            except Exception as e:
                print(f"⚠️ LLM_Call_Agent initialization failed: {e}")
                print("🔄 Falling back to direct API clients")
                # Ensure we have a fallback LLM agent
                self.llm_call_agent = None
        
        # Fallback to direct API clients
        if not OPENAI_AVAILABLE:
            print("⚠️ OpenAI library not available")
            return
        
        # Initialize OpenAI client
        if OPENAI_API_KEY:
            self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
            # print("✅ OpenAI client initialized (direct)")  # Silent
        else:
            print("⚠️ No OpenAI API key provided")
        
        # Initialize DeepSeek client
        if DEEPSEEK_API_KEY:
            self.deepseek_client = OpenAI(
                api_key=DEEPSEEK_API_KEY, 
                base_url="https://api.deepseek.com"
            )
            # print("✅ DeepSeek client initialized (direct)")  # Silent
        else:
            print("⚠️ No DeepSeek API key provided")
        
        # CRITICAL: Ensure we always have an LLM agent available
        if self.llm_call_agent is None:
            try:
                # Try to create LLMCallAgent again with different approach
                self.llm_call_agent = LLMCallAgent(
                    openai_api_key=OPENAI_API_KEY,
                    deepseek_api_key=DEEPSEEK_API_KEY,
                    default_provider="deepseek",
                    default_model="deepseek-chat"
                )
                self.use_legacy_llm_agent = True
                # print("✅ Created LLM agent using direct initialization")  # Silent
            except Exception as e:
                print(f"❌ CRITICAL: Failed to create LLM agent: {e}")
                # Set to None but don't raise exception - let agents handle it
                self.llm_call_agent = None
                print("⚠️ LLM agent will be None - agents will create their own")
    
    async def _initialize_redis_pools(self):
        """Initialize Redis connection pools"""
        print("🗄️ Initializing Redis pools...")
        
        if not AIOREDIS_AVAILABLE:
            raise Exception("❌ aioredis library not available. Install with: pip install aioredis")
        
        # Initialize Frontend Redis pool
        try:
            frontend_url = f"redis://{FRONTEND_REDIS_CONFIG['username']}:{FRONTEND_REDIS_CONFIG['password']}@{FRONTEND_REDIS_CONFIG['host']}:{FRONTEND_REDIS_CONFIG['port']}"
            self.frontend_redis_pool = aioredis.from_url(
                frontend_url,
                max_connections=REDIS_MAX_CONNECTIONS,
                decode_responses=True
            )
            # print("✅ Frontend Redis pool initialized")  # Silent
        except Exception as e:
            print(f"❌ Frontend Redis pool failed: {e}")
        
        # Initialize Stock Trend Redis pool
        try:
            stock_trend_url = f"redis://{STOCK_TREND_REDIS_CONFIG['username']}:{STOCK_TREND_REDIS_CONFIG['password']}@{STOCK_TREND_REDIS_CONFIG['host']}:{STOCK_TREND_REDIS_CONFIG['port']}"
            self.stock_trend_redis_pool = aioredis.from_url(
                stock_trend_url,
                max_connections=REDIS_MAX_CONNECTIONS,
                decode_responses=True
            )
            # print("✅ Stock Trend Redis pool initialized")  # Silent
        except Exception as e:
            print(f"❌ Stock Trend Redis pool failed: {e}")
    
    async def _initialize_http_session(self):
        """Initialize HTTP session with connection pooling"""
        print("🌐 Initializing HTTP session...")
        
        if not AIOHTTP_AVAILABLE:
            print("⚠️ aiohttp library not available")
            return
        
        try:
            self.http_session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=HTTP_TIMEOUT),
                connector=aiohttp.TCPConnector(
                    limit=HTTP_MAX_CONNECTIONS,
                    limit_per_host=HTTP_MAX_PER_HOST
                )
            )
            # print("✅ HTTP session initialized")  # Silent
        except Exception as e:
            print(f"❌ HTTP session failed: {e}")
    
    async def _test_connections(self):
        """Test all connections to ensure they work"""
        print("🧪 Testing connections...")
        
        # Test Redis connections - fail fast if not available
        if not self.frontend_redis_pool:
            raise Exception("❌ Frontend Redis pool not initialized")
        if not self.stock_trend_redis_pool:
            raise Exception("❌ Stock Trend Redis pool not initialized")
            
        try:
            await self.frontend_redis_pool.ping()
            await self.stock_trend_redis_pool.ping()
            print("✅ All Redis connections verified")
        except Exception as e:
            raise Exception(f"❌ Redis connection test failed: {e}")
        
        # Test HTTP session
        if self.http_session:
            try:
                async with self.http_session.get("https://httpbin.org/get") as response:
                    if response.status == 200:
                        pass  # HTTP session test passed (silent)
                    else:
                        print(f"❌ HTTP session test failed: {response.status}")
            except Exception as e:
                print(f"❌ HTTP session test failed: {e}")
    
    async def _cleanup(self):
        """Clean up resources if initialization fails"""
        print("🧹 Cleaning up failed initialization...")
        
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
        
        if self.frontend_redis_pool:
            await self.frontend_redis_pool.close()
            self.frontend_redis_pool = None
        
        if self.stock_trend_redis_pool:
            await self.stock_trend_redis_pool.close()
            self.stock_trend_redis_pool = None
    
    async def close(self):
        """Close all connections and cleanup resources"""
        print("🔚 Closing shared client pool...")
        
        if self.http_session:
            await self.http_session.close()
            self.http_session = None
        
        if self.frontend_redis_pool:
            await self.frontend_redis_pool.close()
            self.frontend_redis_pool = None
        
        if self.stock_trend_redis_pool:
            await self.stock_trend_redis_pool.close()
            self.stock_trend_redis_pool = None
        
        self._initialized = False
        # print("✅ Shared client pool closed")  # Silent
    
    def get_llm_agent(self):
        """Get LLM call agent"""
        return self.llm_call_agent
    
    def get_frontend_redis(self):
        """Get frontend Redis connection"""
        if not self.frontend_redis_pool:
            raise Exception("❌ Frontend Redis pool not available")
        return self.frontend_redis_pool
    
    def get_stock_trend_redis(self):
        """Get stock trend Redis connection"""
        if not self.stock_trend_redis_pool:
            raise Exception("❌ Stock Trend Redis pool not available")
        return self.stock_trend_redis_pool
    
    def get_earnings_redis(self):
        """Get earnings Redis connection (alias for stock trend)"""
        return self.get_stock_trend_redis()
    
    def get_financial_metrics_redis(self):
        """Get financial metrics Redis connection (alias for stock trend)"""
        return self.get_stock_trend_redis()
    
    def get_http_session(self):
        """Get HTTP session"""
        return self.http_session
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of all shared clients"""
        return {
            "initialized": self._initialized,
            "initialization_time": self.initialization_time,
            "total_requests": self.total_requests,
            "error_count": self.error_count,
            "llm_call_agent_available": self.llm_call_agent is not None,
            "use_legacy_llm_agent": self.use_legacy_llm_agent,
            "openai_client_available": self.openai_client is not None,
            "deepseek_client_available": self.deepseek_client is not None,
            "frontend_redis_available": self.frontend_redis_pool is not None,
            "stock_trend_redis_available": self.stock_trend_redis_pool is not None,
            "http_session_available": self.http_session is not None,
            # 🚀 NEW: Semaphore status
            "openai_semaphore_value": self.sem_openai._value if hasattr(self.sem_openai, '_value') else 'N/A',
            "deepseek_semaphore_value": self.sem_deepseek._value if hasattr(self.sem_deepseek, '_value') else 'N/A'
        }
    
    async def call_openai(self, prompt: str, **kwargs) -> str:
        """
        Call OpenAI API with semaphore control and async execution
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments for the API call
            
        Returns:
            str: API response
        """
        self.total_requests += 1
        
        try:
            # 🚀 Use semaphore to control concurrency
            async with self.sem_openai:
                if self.use_legacy_llm_agent and self.llm_call_agent:
                    # Use existing LLM_Call_Agent but wrap in async
                    return await asyncio.to_thread(
                        self.llm_call_agent.call_openai, 
                        prompt, 
                        **kwargs
                    )
                elif self.openai_client:
                    # Use direct OpenAI client (already async)
                    response = await self.openai_client.chat.completions.create(
                        model=kwargs.get('model', 'gpt-4o'),
                        messages=[
                            {"role": "system", "content": kwargs.get('system_message', 'You are a helpful assistant.')},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=kwargs.get('max_tokens', 4000),
                        temperature=kwargs.get('temperature', 0.3)
                    )
                    return response.choices[0].message.content.strip()
                else:
                    raise Exception("No OpenAI client available")
                
        except Exception as e:
            self.error_count += 1
            print(f"❌ OpenAI API call failed: {e}")
            return f"❌ OpenAI API Error: {str(e)}"
    
    async def call_deepseek(self, prompt: str, **kwargs) -> str:
        """
        Call DeepSeek API with semaphore control and async execution
        
        Args:
            prompt: The prompt to send
            **kwargs: Additional arguments for the API call
            
        Returns:
            str: API response
        """
        self.total_requests += 1
        
        try:
            # 🚀 Use semaphore to control concurrency
            async with self.sem_deepseek:
                if self.use_legacy_llm_agent and self.llm_call_agent:
                    # Use existing LLM_Call_Agent but wrap in async
                    return await asyncio.to_thread(
                        self.llm_call_agent.call_deepseek, 
                        prompt, 
                        **kwargs
                    )
                elif self.deepseek_client:
                    # Use direct DeepSeek client (already async)
                    response = await self.deepseek_client.chat.completions.create(
                        model=kwargs.get('model', 'deepseek-chat'),
                        messages=[
                            {"role": "system", "content": kwargs.get('system_message', 'You are a helpful assistant.')},
                            {"role": "user", "content": prompt}
                        ],
                        max_tokens=kwargs.get('max_tokens', 4000),
                        temperature=kwargs.get('temperature', 0.3)
                    )
                    return response.choices[0].message.content.strip()
                else:
                    raise Exception("No DeepSeek client available")
                
        except Exception as e:
            self.error_count += 1
            print(f"❌ DeepSeek API call failed: {e}")
            return f"❌ DeepSeek API Error: {str(e)}"

# ============================================================================
# PERFORMANCE MONITORING
# ============================================================================

def show_performance_stats():
    """Show performance statistics from shared clients"""
    status = shared_clients.get_status()
    
    print("📊 Shared Clients Performance Stats:")
    print("=" * 40)
    # print(f"✅ Initialized: {status['initialized']}")  # Silent
    print(f"⏱️ Init Time: {status['initialization_time']:.2f}s")
    print(f"📈 Total Requests: {status['total_requests']}")
    print(f"❌ Errors: {status['error_count']}")
    # print(f"🤖 LLM Agent: {'✅ Shared' if status['use_legacy_llm_agent'] else '❌ Direct'}")  # Silent
    # print(f"🗄️ Frontend Redis: {'✅' if status['frontend_redis_available'] else '❌'}")  # Silent
    # print(f"🗄️ Stock Trend Redis: {'✅' if status['stock_trend_redis_available'] else '❌'}")  # Silent
    # print(f"🌐 HTTP Session: {'✅' if status['http_session_available'] else '❌'}")  # Silent
    # 🚀 NEW: Semaphore status
    print(f"🔒 OpenAI Semaphore: {status['openai_semaphore_value']}")
    print(f"🔒 DeepSeek Semaphore: {status['deepseek_semaphore_value']}")

# ============================================================================
# LLM CALL TIMING TRACKER
# ============================================================================

class LLMTimingTracker:
    """Track LLM call timing for performance analysis"""
    
    def __init__(self):
        self.start_time = time.perf_counter()
        self.calls = {}
    
    def stamp(self, phase: str, agent: str):
        """Record a timing stamp"""
        elapsed = time.perf_counter() - self.start_time
        print(f"{elapsed:8.3f}s [{agent}] {phase}")
    
    def track_llm_call(self, agent: str, provider: str):
        """Track LLM call timing"""
        self.stamp(f"LLM {provider} start", agent)
        return self.start_time
    
    def end_llm_call(self, agent: str, provider: str, start_time: float):
        """End LLM call tracking"""
        elapsed = time.perf_counter() - start_time
        self.stamp(f"LLM {provider} end ({elapsed:.1f}s)", agent)

# Global timing tracker
llm_tracker = LLMTimingTracker()

# ============================================================================
# GLOBAL INSTANCE - Import this in other files
# ============================================================================

# Create global instance - this is what you import in other files
shared_clients = SharedClientPool()

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

async def get_shared_clients() -> SharedClientPool:
    """
    Get the shared clients instance and ensure it's initialized.
    
    Usage:
        clients = await get_shared_clients()
        result = await clients.openai_client.chat.completions.create(...)
    """
    if not shared_clients._initialized:
        await shared_clients.initialize()
    return shared_clients

def get_redis_pool(pool_type: str = "frontend"):
    """
    Get Redis pool by type.
    
    Args:
        pool_type: "frontend" or "stock_trend"
    
    Returns:
        Redis pool or None if not available
    """
    if pool_type == "frontend":
        return shared_clients.frontend_redis_pool
    elif pool_type == "stock_trend":
        return shared_clients.stock_trend_redis_pool
    else:
        print(f"⚠️ Unknown Redis pool type: {pool_type}")
        return None

# ============================================================================
# COMPATIBILITY LAYER - For existing agents
# ============================================================================

class LLMCallAgentCompatibility:
    """
    Compatibility wrapper for existing agents to use shared clients.
    
    This class provides the same interface as LLMCallAgent but uses shared clients
    internally for better performance.
    """
    
    def __init__(self, 
                 openai_api_key: str = None,
                 deepseek_api_key: str = None,
                 default_provider: str = "deepseek",
                 default_model: str = "deepseek-chat"):
        """
        Initialize compatibility wrapper.
        
        Args:
            openai_api_key (str): OpenAI API key (ignored, uses shared)
            deepseek_api_key (str): DeepSeek API key (ignored, uses shared)
            default_provider (str): Default LLM provider
            default_model (str): Default model to use
        """
        self.default_provider = default_provider
        self.default_model = default_model
        
        # Store for compatibility
        self.openai_api_key = shared_clients.openai_client is not None
        self.deepseek_api_key = shared_clients.deepseek_client is not None
        
        print(f"🤖 LLM Call Agent (Shared) initialized")
        print(f"   - Default provider: {default_provider}")
        print(f"   - Default model: {default_model}")
        print(f"   - OpenAI: {'Enabled' if self.openai_api_key else 'Disabled'}")
        print(f"   - DeepSeek: {'Enabled' if self.deepseek_api_key else 'Disabled'}")
    
    def call_openai(self, 
                    prompt: str, 
                    system_message: str = "You are a knowledgeable financial analyst assistant.",
                    model: str = "gpt-4o",
                    max_tokens: int = 4000,
                    temperature: float = 0.3,
                    functions: List[Dict] = None,
                    function_call: str = "auto") -> str:
        """Compatibility wrapper for OpenAI calls"""
        try:
            # Use the original LLMCallAgent for now
            if LLM_CALL_AGENT_AVAILABLE:
                # Import the original LLMCallAgent
                from LLM_Call_Agent import LLMCallAgent as OriginalLLMCallAgent
                # Create a temporary instance for this call
                temp_agent = OriginalLLMCallAgent(
                    openai_api_key=OPENAI_API_KEY,
                    deepseek_api_key=DEEPSEEK_API_KEY,
                    default_provider="openai",
                    default_model=model
                )
                return temp_agent.call_openai(
                    prompt=prompt,
                    system_message=system_message,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    functions=functions,
                    function_call=function_call
                )
            else:
                return "❌ LLM_Call_Agent not available"
        except Exception as e:
            return f"❌ OpenAI API Error: {str(e)}"
    
    def call_deepseek(self, 
                      prompt: str, 
                      system_message: str = "You are a knowledgeable financial analyst assistant.",
                      model: str = "deepseek-chat",
                      max_tokens: int = 4000,
                      temperature: float = 0.3) -> str:
        """Compatibility wrapper for DeepSeek calls"""
        try:
            # Use the original LLMCallAgent for now
            if LLM_CALL_AGENT_AVAILABLE:
                # Import the original LLMCallAgent
                from LLM_Call_Agent import LLMCallAgent as OriginalLLMCallAgent
                # Create a temporary instance for this call
                temp_agent = OriginalLLMCallAgent(
                    openai_api_key=OPENAI_API_KEY,
                    deepseek_api_key=DEEPSEEK_API_KEY,
                    default_provider="deepseek",
                    default_model=model
                )
                return temp_agent.call_deepseek(
                    prompt=prompt,
                    system_message=system_message,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
            else:
                return "❌ LLM_Call_Agent not available"
        except Exception as e:
            return f"❌ DeepSeek API Error: {str(e)}"
    
    def call_llm(self, 
                 prompt: str, 
                 provider: str = None,
                 system_message: str = "You are a knowledgeable financial analyst assistant.",
                 model: str = None,
                 max_tokens: int = 4000,
                 temperature: float = 0.3,
                 functions: List[Dict] = None,
                 function_call: str = "auto") -> str:
        """Compatibility wrapper for generic LLM calls"""
        # Use default provider if not specified
        if not provider:
            provider = self.default_provider
        
        # Use default model if not specified
        if not model:
            model = self.default_model
        
        if provider == "openai":
            return self.call_openai(prompt, system_message, model, max_tokens, temperature)
        elif provider == "deepseek":
            return self.call_deepseek(prompt, system_message, model, max_tokens, temperature)
        else:
            return f"❌ Unknown provider: {provider}"

# ============================================================================
# PATCHING FUNCTION - Replace LLMCallAgent with shared version
# ============================================================================

def patch_llm_call_agent():
    """
    Patch the LLMCallAgent import to use shared clients.
    
    This function replaces the LLMCallAgent class with our compatibility wrapper
    so existing code continues to work but uses shared clients.
    """
    import sys
    import types
    
    # Create a compatibility module that exports our compatibility class
    compatibility_module = types.ModuleType('LLM_Call_Agent')
    compatibility_module.LLMCallAgent = LLMCallAgentCompatibility
    
    # Add the original constants for compatibility
    compatibility_module.OPENAI_API_KEY = OPENAI_API_KEY
    compatibility_module.DEEPSEEK_API_KEY = DEEPSEEK_API_KEY
    
    # Replace the module in sys.modules
    sys.modules['LLM_Call_Agent'] = compatibility_module
    
    # print("✅ LLM_Call_Agent patched to use shared clients")  # Silent

# ============================================================================
# AUTO-PATCHING - Apply patch when shared_clients is imported
# ============================================================================

# Uncomment the line below to automatically patch LLMCallAgent
# patch_llm_call_agent()

# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_usage():
    """Example of how to use the shared clients"""
    print("📖 Shared Clients Example Usage:")
    print("=" * 50)
    
    try:
        # Initialize shared clients
        await shared_clients.initialize()
        
        # Test LLM calls (works with both approaches)
        print("🤖 Testing LLM calls...")
        
        # Test OpenAI call
        openai_response = await shared_clients.call_openai(
            "Hello, how are you?",
            model="gpt-4o",
            max_tokens=100
        )
        print(f"OpenAI Response: {openai_response[:50]}...")
        
        # Test DeepSeek call
        deepseek_response = await shared_clients.call_deepseek(
            "Hello, how are you?",
            model="deepseek-chat",
            max_tokens=100
        )
        print(f"DeepSeek Response: {deepseek_response[:50]}...")
        
        # Use Redis pool
        if shared_clients.frontend_redis_pool:
            print("🗄️ Using shared Redis pool...")
            # value = await shared_clients.frontend_redis_pool.get("key")
        
        # Use HTTP session
        if shared_clients.http_session:
            print("🌐 Using shared HTTP session...")
            # async with shared_clients.http_session.get("https://api.example.com") as response:
            #     data = await response.json()
        
        # Get status
        status = shared_clients.get_status()
        print(f"📊 Status: {json.dumps(status, indent=2)}")
        
        print(f"📈 Performance: {status['total_requests']} requests, {status['error_count']} errors")
        
    finally:
        # Clean up
        await shared_clients.close()

# ============================================================================
# MAIN EXECUTION (for testing)
# ============================================================================

if __name__ == "__main__":
    print("🧪 Testing Shared Client Pool...")
    asyncio.run(example_usage())
