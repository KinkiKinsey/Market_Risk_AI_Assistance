"""
Centralized Configuration Module for Q&Q.AI Backend
Loads all API keys and URLs from config.env file
"""
import os
from pathlib import Path
from typing import Optional

# Get the directory where this config.py file is located
CONFIG_DIR = Path(__file__).parent
CONFIG_ENV_FILE = CONFIG_DIR / "config.env"

def load_config():
    """Load environment variables from config.env file"""
    if CONFIG_ENV_FILE.exists():
        with open(CONFIG_ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # Set environment variable if not already set
                        if key and value and not os.getenv(key):
                            os.environ[key] = value

# Load config on module import
load_config()

# ============================================================================
# API KEYS
# ============================================================================

# LLM API Keys
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')

# Financial Data API Keys
FMP_API_KEY = os.getenv('FMP_API_KEY', '')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')

# Web Scraping API Keys
FIRECRAWL_API_KEY = os.getenv('FIRECRAWL_API_KEY', '')

# ============================================================================
# API BASE URLs
# ============================================================================

# Financial Modeling Prep API
FMP_BASE_URL = os.getenv('FMP_BASE_URL', 'https://financialmodelingprep.com')
FMP_API_V3_URL = f"{FMP_BASE_URL}/api/v3"
FMP_STABLE_URL = f"{FMP_BASE_URL}/stable"

# DeepSeek API
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com')

# Firecrawl API
FIRECRAWL_BASE_URL = os.getenv('FIRECRAWL_BASE_URL', 'https://api.firecrawl.dev/v2')

# Tavily API
TAVILY_BASE_URL = os.getenv('TAVILY_BASE_URL', 'https://api.tavily.com')

# DEX Screener API (no key required)
DEXSCREENER_BASE_URL = os.getenv('DEXSCREENER_BASE_URL', 'https://api.dexscreener.com')

# ============================================================================
# REDIS CONFIGURATION
# ============================================================================

# Frontend Redis
FRONTEND_REDIS_HOST = os.getenv('FRONTEND_REDIS_HOST', 'localhost')
FRONTEND_REDIS_PORT = int(os.getenv('FRONTEND_REDIS_PORT', '6379'))
FRONTEND_REDIS_USERNAME = os.getenv('FRONTEND_REDIS_USERNAME', '')
FRONTEND_REDIS_PASSWORD = os.getenv('FRONTEND_REDIS_PASSWORD', '')

# Stock Trend Redis
STOCK_TREND_REDIS_HOST = os.getenv('STOCK_TREND_REDIS_HOST', 'localhost')
STOCK_TREND_REDIS_PORT = int(os.getenv('STOCK_TREND_REDIS_PORT', '6379'))
STOCK_TREND_REDIS_USERNAME = os.getenv('STOCK_TREND_REDIS_USERNAME', '')
STOCK_TREND_REDIS_PASSWORD = os.getenv('STOCK_TREND_REDIS_PASSWORD', '')

# Connection Pool Settings
REDIS_MAX_CONNECTIONS = int(os.getenv('REDIS_MAX_CONNECTIONS', '20'))
HTTP_MAX_CONNECTIONS = int(os.getenv('HTTP_MAX_CONNECTIONS', '50'))
HTTP_MAX_PER_HOST = int(os.getenv('HTTP_MAX_PER_HOST', '20'))
HTTP_TIMEOUT = int(os.getenv('HTTP_TIMEOUT', '10'))

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_fmp_api_key() -> str:
    """Get FMP API key"""
    return FMP_API_KEY

def get_openai_api_key() -> str:
    """Get OpenAI API key"""
    return OPENAI_API_KEY

def get_deepseek_api_key() -> str:
    """Get DeepSeek API key"""
    return DEEPSEEK_API_KEY

def get_firecrawl_api_key() -> str:
    """Get Firecrawl API key"""
    return FIRECRAWL_API_KEY

def get_tavily_api_key() -> str:
    """Get Tavily API key"""
    return TAVILY_API_KEY

# ============================================================================
# VALIDATION
# ============================================================================

def validate_config():
    """Validate that required API keys are set"""
    missing = []
    if not OPENAI_API_KEY and not DEEPSEEK_API_KEY:
        missing.append("OPENAI_API_KEY or DEEPSEEK_API_KEY")
    if not FMP_API_KEY:
        missing.append("FMP_API_KEY")
    
    if missing:
        print(f"⚠️ Warning: Missing API keys: {', '.join(missing)}")
        return False
    return True

# Validate on import
if __name__ != "__main__":
    validate_config()

