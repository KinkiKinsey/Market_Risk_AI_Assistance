"""
Quant Impact Storage Agent - EXACT COPY from Dynamic_Alpha.ipynb

This agent implements the complete analyst pipeline from Dynamic_Alpha.ipynb:
1. Get ticker → Get sector → Get double beta
2. Get factors → Get date ranges → Beta filter impact  
3. Generate impact metrics → Store in database
4. Generate 6 metrics: risk_share_index, macro_volatility_df, micro_volatility_df, impact_metrics_df, macro_total_impact_df, micro_total_impact_df
5. Generate treemap visualization

Each stock analysis stores impact metrics as DataFrame format.
"""

import asyncio
import sys
import os
from pathlib import Path
from typing import Dict, List, Any, Union, Optional, Tuple
import json
import redis
import re
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from io import StringIO
from scipy import stats
import webbrowser
import tempfile
import threading
import time

# Add project root to path
ROOT_SENTINEL = "LLM_Call_Agent.py"
def find_repo_root(start: Path) -> Path:
    for path in (start, *start.parents):
        if (path / ROOT_SENTINEL).exists():
            return path
    raise FileNotFoundError(f"Could not locate {ROOT_SENTINEL} upward from {start}")

repo_root = find_repo_root(Path.cwd())
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))

from LLM_Call_Agent import LLMCallAgent
from langchain.output_parsers import PydanticOutputParser
from langchain_core.pydantic_v1 import BaseModel, Field

# =============================================================================
# PYDANTIC MODELS (EXACT SAME AS DYNAMIC_ALPHA.IPYNB)
# =============================================================================

class FactorSet(BaseModel):
    factor_1: str = Field(description="Keyword for the top catalyst")
    factor_2: str = Field(description="Keyword for the second catalyst.")
    factor_3: str = Field(description="Keyword for the third catalyst.")
    factor_4: str = Field(description="Keyword for the fourth catalyst.")
    factor_5: str = Field(description="Keyword for the fifth catalyst.")
    factor_6: str = Field(description="Keyword for the sixth catalyst.")
    factor_7: str = Field(description="Keyword for the seventh catalyst.")
    factor_8: str = Field(description="Keyword for the eighth catalyst.")
    factor_9: str = Field(description="Keyword for the ninth catalyst.")
    factor_10: str = Field(description="Keyword for the tenth catalyst.")
    factor_11: str = Field(description="Keyword for the eleventh catalyst.")
    factor_12: str = Field(description="Keyword for the twelfth catalyst.")
    factor_13: str = Field(description="Keyword for the thirteenth catalyst.")
    factor_14: str = Field(description="Keyword for the fourteenth catalyst.")
    factor_15: str = Field(description="Keyword for the fifteenth catalyst.")
    factor_16: str = Field(description="Keyword for the sixteenth catalyst.")

class FactorPayload(BaseModel):
    ticker: str = Field(description="Ticker symbol in uppercase.")
    macro: FactorSet = Field(description="Macro-level catalyst keywords.")
    micro: FactorSet = Field(description="Company-level catalyst keywords.")

# LangChain parser expects Pydantic v2's model_json_schema; shim it for v1.
FactorSet.model_json_schema = classmethod(lambda cls: cls.schema())
FactorPayload.model_json_schema = classmethod(lambda cls: cls.schema())

parser = PydanticOutputParser(pydantic_object=FactorPayload)

class DateRangePayload(BaseModel):
    ticker: str = Field(description="Ticker symbol in uppercase")
    macro: Dict[str, List[List[str]]] = Field(description="Macro factor to date ranges mapping")
    micro: Dict[str, List[List[str]]] = Field(description="Micro factor to date ranges mapping")

# LangChain parser expects Pydantic v2's model_json_schema; shim it for v1.
DateRangePayload.model_json_schema = classmethod(lambda cls: cls.schema())

date_range_parser = PydanticOutputParser(pydantic_object=DateRangePayload)

# Redis Configuration
REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
REDIS_PORT = 16376
REDIS_USERNAME = "default"
REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
COLLECTION_NAME = "Stock_Trend_INFOS"

# FMP API Configuration
FMP_API_KEY = "9dfbbfa29d93f4793f246e8fb5ca5e74"

# =============================================================================
# EXACT FUNCTIONS FROM DYNAMIC_ALPHA.IPYNB
# =============================================================================

def get_system_instructions(language: str = "English") -> str:
    """Get system instructions with language support."""
    base_instructions = f"""
You are a senior equity strategist. Extract the most impactful market drivers from stock intelligence.

**SMART FACTOR DETECTION:**
- **REAL DRIVER FOCUS**: If earnings miss but guidance raised → price up → factor = "Guidance Raised Better Than Expected" (NOT "Earnings Miss")
- **COMPREHENSIVE NAMING**: If no single driver, use full context: "Revenue Miss But Strong Guidance"
- **MARKET IMPACT**: Focus on what actually moved the stock price, not surface headlines
- **CONTEXT AWARENESS**: Consider the full story - what was the net market reaction?

**RULES:**
- Generate 10 high-quality factors per scope (macro + micro = 20 total)
- Include expectation/delivery context: "Fed Rate Cut Expectation", "Guidance Raised Better Than Expected"
- Keep names under 60 characters
- MACRO: market-wide events (Fed policy, inflation, trade)
- MICRO: company-specific events (earnings, guidance, products, management)
- Ground in provided context only - never invent events
- Focus on real market movers, not noise

**EXAMPLES:**
- Good: "Guidance Raised Better Than Expected" (if price went up despite earnings miss)
- Good: "Revenue Miss But Strong Guidance" (if mixed signals)
- Bad: "Earnings Miss" (if guidance was the real driver)

{parser.get_format_instructions()}
""".strip()
    
    if language.lower() != "english":
        language_instruction = f"\n\nIMPORTANT: Output ALL factor names in {language} language only. Do NOT use English."
        return base_instructions + language_instruction
    else:
        return base_instructions

def _extract_json_payload(raw: str) -> str:
    """Strip markdown fences and clamp to the outermost JSON braces."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return cleaned

def build_factor_prompt(
    ticker: str, 
    read_information: Union[str, Dict[str, Any]],
    language: str = "English"
) -> str:
    """Human prompt body sent to the LLM."""
    if isinstance(read_information, (dict, list)):
        serialized_context = json.dumps(read_information, ensure_ascii=False, indent=2)
    else:
          serialized_context = str(read_information)

    base_prompt = (
        f"Ticker: {ticker}\n\n"
        "Stock intelligence snapshot:\n"
        f"{serialized_context}\n\n"
        "**SMART FACTOR DETECTION**: Focus on what actually moved the stock price.\n"
        "- If earnings miss but guidance raised → price up → factor = 'Guidance Raised Better Than Expected'\n"
        "- If mixed signals → use comprehensive name: 'Revenue Miss But Strong Guidance'\n"
        "- Focus on the REAL driver, not surface headlines\n\n"
        "Task: Extract MACRO and MICRO factors with expectation/delivery context.\n"
        "MACRO: market-wide events (Fed policy, inflation, trade). MICRO: company events (earnings, guidance, products)."
    )
    
    if language.lower() != "english":
        language_instruction = f"\n\nIMPORTANT: Output ALL factor names in {language} language only. Do NOT use English."
        return base_prompt + language_instruction
    else:
        return base_prompt

def analyze_trend_complexity(read_information: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze trend complexity to determine optimal factor count"""
    if not isinstance(read_information, dict):
        return {"complexity_score": 3, "factor_count": 6, "reason": "default_fallback"}
    
    historical_trends = read_information.get('historical_trends', {})
    if not historical_trends:
        return {"complexity_score": 3, "factor_count": 6, "reason": "no_trends"}
    
    # Calculate complexity indicators
    trend_count = len(historical_trends)
    total_news_articles = 0
    total_trend_duration = 0
    avg_trend_magnitude = 0
    
    for trend_key, trend_data in historical_trends.items():
        # Count news articles
        news_data = trend_data.get('news_data', [])
        total_news_articles += len(news_data)
        
        # Calculate trend duration
        start_date = trend_data.get('start_date', '')
        end_date = trend_data.get('end_date', '')
        if start_date and end_date:
            try:
                from datetime import datetime
                duration = (datetime.strptime(end_date, '%Y-%m-%d') - 
                           datetime.strptime(start_date, '%Y-%m-%d')).days
                total_trend_duration += duration
            except:
                pass
        
        # Calculate trend magnitude (if available)
        trend_magnitude = trend_data.get('trend_magnitude', 0)
        avg_trend_magnitude += abs(trend_magnitude)
    
    # Calculate complexity score (0-10 scale)
    complexity_score = 0
    
    # Trend count factor (0-3 points)
    if trend_count <= 5:
        complexity_score += 1
    elif trend_count <= 10:
        complexity_score += 2
    else:
        complexity_score += 3
    
    # News volume factor (0-3 points)
    avg_news_per_trend = total_news_articles / max(trend_count, 1)
    if avg_news_per_trend <= 3:
        complexity_score += 1
    elif avg_news_per_trend <= 6:
        complexity_score += 2
    else:
        complexity_score += 3
    
    # Trend duration factor (0-2 points)
    avg_duration = total_trend_duration / max(trend_count, 1)
    if avg_duration <= 7:
        complexity_score += 1
    else:
        complexity_score += 2
    
    # Trend magnitude factor (0-2 points)
    avg_magnitude = avg_trend_magnitude / max(trend_count, 1)
    if avg_magnitude >= 0.05:  # 5%+ average movement
        complexity_score += 2
    elif avg_magnitude >= 0.02:  # 2%+ average movement
        complexity_score += 1
    
    # Map complexity score to factor count
    if complexity_score <= 3:
        factor_count = 4
        reason = "low_complexity"
    elif complexity_score <= 6:
        factor_count = 6
        reason = "medium_complexity"
    elif complexity_score <= 8:
        factor_count = 8
        reason = "high_complexity"
    else:
        factor_count = 10
        reason = "very_high_complexity"
    
    return {
        "complexity_score": complexity_score,
        "factor_count": factor_count,
        "reason": reason,
        "trend_count": trend_count,
        "total_news": total_news_articles,
        "avg_news_per_trend": avg_news_per_trend,
        "avg_duration": avg_duration,
        "avg_magnitude": avg_magnitude
    }

def count_trends_in_period(read_information: Union[str, Dict[str, Any]]) -> int:
    """Count the number of trends in the period (legacy function)"""
    complexity_analysis = analyze_trend_complexity(read_information)
    return complexity_analysis["trend_count"]

def generate_stock_factors(
    ticker: str,
    read_information: Union[str, Dict[str, Any]],
    provider: str = "deepseek",
    model_override: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 700,  # Reduced since we only need macro + micro
    language: str = "English"
) -> FactorPayload:
    """Call the LLM and parse keyword factors via LangChain."""
    # FIXED FACTOR COUNT: 10 factors per scope (macro + micro = 20 total)
    smart_factor_count = 10
    
    print(f"   🔢 Generating {smart_factor_count} factors per scope (FIXED MODE)")
    
    prompt = build_factor_prompt(ticker, read_information, language)
    system_instructions = get_system_instructions(language)

    if provider == "deepseek":
        model = model_override or "deepseek-chat"
    else:
        provider = "openai"
        model = model_override or "gpt-4o"

    llm_agent = LLMCallAgent(default_provider=provider, default_model=model)

    if provider == "deepseek":
        raw_response = llm_agent.call_deepseek(
            prompt=prompt,
            system_message=system_instructions,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        raw_response = llm_agent.call_openai(
            prompt=prompt,
            system_message=system_instructions,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    if not raw_response:
        raise ValueError("Empty response from LLM")

    cleaned = _extract_json_payload(raw_response)
    try:
        return parser.parse(cleaned)
    except Exception as exc:
        raise ValueError(f"LLM response could not be parsed:\n{raw_response}") from exc

def quant_market_expectation_read_agent(ticker: str):
    """Read stock trend data from Redis - MVP version (no async)"""
    redis_key = f"{COLLECTION_NAME}:{ticker.upper()}_trends"

    client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        username=REDIS_USERNAME,
        password=REDIS_PASSWORD,
        decode_responses=True,
    )

    data = client.get(redis_key)
    if data is None:
        print(f"No stock trend payload stored for {ticker}")
        return None

    return json.loads(data)

def get_date_range_system_instructions(language: str = "English") -> str:
    """Get system instructions for date range mapping."""
    base_instructions = f"""
You are a meticulous financial analyst. Given the stock intelligence and historical trends,
map each factor to specific date ranges when those events actually occurred.

Rules:
- For each factor, provide actual date ranges when the event happened
- Use format: ["YYYY-MM-DD", "YYYY-MM-DD"] for each date range
- A factor can have multiple date ranges (e.g., Fed Rate Cut happened multiple times)
- Only use dates that actually exist in the historical data
- If no specific dates are available, provide empty list []
- Focus on major events that would impact stock price
- Be conservative - only include dates you're confident about
- IMPORTANT: You MUST include macro and micro sections (NO sector)
- IMPORTANT: Keep response concise to avoid truncation 
{date_range_parser.get_format_instructions()}
""".strip()
    
    if language.lower() != "english":
        language_instruction = f"\n\nIMPORTANT: Output ALL content in {language} language only. Do NOT use English."
        return base_instructions + language_instruction
    else:
        return base_instructions

def build_date_range_prompt(ticker: str, factor_payload: FactorPayload, read_information: Dict[str, Any], language: str) -> str:
    """Build prompt for date range mapping."""
    # Create factor summary - DYNAMIC based on actual factors available
    macro_factors = []
    micro_factors = []
    
    # Dynamically extract factors based on what's available
    i = 1
    while True:
        macro_attr = f'factor_{i}'
        micro_attr = f'factor_{i}'
        
        if hasattr(factor_payload.macro, macro_attr) and hasattr(factor_payload.micro, micro_attr):
            macro_factors.append(getattr(factor_payload.macro, macro_attr))
            micro_factors.append(getattr(factor_payload.micro, micro_attr))
            i += 1
        else:
            break
    
    factor_summary = f"Macro factors: {', '.join(macro_factors)}\nMicro factors: {', '.join(micro_factors)}"
    
    # Create trend summary from historical data
    trend_summary = {}
    if 'historical_trends' in read_information:
        for trend_key, trend_data in read_information['historical_trends'].items():
            summary = trend_data.get("summary", {})
            trend_summary[trend_key] = {
                "period": trend_data.get("current", ""),
                "macro_reason": summary.get("macro_reason", ""),
                "micro_reason": summary.get("micro_reason", "")
            }
    
    trend_context = json.dumps(trend_summary, indent=2, ensure_ascii=False)
    
    base_prompt = (
        f"Ticker: {ticker}\n\n"
        f"Factor keywords (macro/micro):\n{factor_summary}\n\n"
        "Historical trend context (with dates and reasons):\n"
        f"{trend_context}\n\n"
        
        "Task: For each factor, map to specific date ranges when those events occurred. "
        "Use the historical trend data to identify actual dates. "
        "Return date ranges in format: [\"start_date\", \"end_date\"]"
        "IMPORTANT: Include macro and micro sections (NO sector) and keep response concise."
    )
    
    if language.lower() != "english":
        language_instruction = f"\n\nIMPORTANT: Output ALL content in {language} language only. Do NOT use English."
        return base_prompt + language_instruction
    else:
        return base_prompt

def map_factors_to_date_ranges(
    ticker: str,
    factor_payload: FactorPayload,
    read_information: Dict[str, Any],
    provider: str = "deepseek",
    model_override: str | None = None,
    temperature: float = 0.0,
    max_tokens: int = 4000,  # Increased to handle large TSLA data
    language: str = "English"
) -> Tuple[DateRangePayload, pd.DataFrame]:
    """Map factors to date ranges using LLM."""
    prompt = build_date_range_prompt(ticker, factor_payload, read_information, language)
    system_instructions = get_date_range_system_instructions(language)

    if provider == "deepseek":
        model = model_override or "deepseek-chat"
    else:
        provider = "openai"
        model = model_override or "gpt-4o"

    llm_agent = LLMCallAgent(default_provider=provider, default_model=model)

    if provider == "deepseek":
        raw_response = llm_agent.call_deepseek(
            prompt=prompt,
            system_message=system_instructions,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )
    else:
        raw_response = llm_agent.call_openai(
            prompt=prompt,
            system_message=system_instructions,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    if not raw_response:
        raise ValueError("Empty response from LLM during date range mapping")

    cleaned = raw_response.strip().strip("`")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]

    # Check if response is complete
    if not cleaned.endswith("}"):
        print(f"⚠️ Response may be truncated. Last 100 chars: {cleaned[-100:]}")
        # Try to fix incomplete JSON
        if '"micro"' not in cleaned:
            cleaned += ', "micro": {}}'
        elif '"macro"' not in cleaned:
            cleaned += ', "macro": {}}'
        else:
            # More aggressive JSON repair for truncated responses
            print("🔧 Attempting advanced JSON repair...")
            # Count open vs close braces
            open_braces = cleaned.count('{')
            close_braces = cleaned.count('}')
            missing_braces = open_braces - close_braces
            
            # Add missing closing braces
            cleaned += '}' * missing_braces
            
            # Ensure proper JSON structure
            if not cleaned.strip().endswith('}'):
                cleaned = cleaned.rstrip() + '}'
            
            print(f"🔧 Added {missing_braces} missing closing braces")

    # COMPLETE JSON REPAIR - NO FALLBACKS
    # Fix incomplete JSON by completing the structure
    if not cleaned.endswith("}"):
        print(f"⚠️ Truncated response detected. Repairing JSON...")
        
        # Find the last complete factor entry
        lines = cleaned.split('\n')
        repaired_lines = []
        in_micro_section = False
        in_macro_section = False
        
        for line in lines:
            if '"micro"' in line:
                in_micro_section = True
                in_macro_section = False
            elif '"macro"' in line:
                in_macro_section = True
                in_micro_section = False
            
            # If line ends with incomplete factor (missing closing bracket)
            if in_micro_section and line.strip().endswith(':'):
                # Complete the incomplete factor
                line = line.rstrip(':') + ': []'
            elif in_macro_section and line.strip().endswith(':'):
                # Complete the incomplete factor  
                line = line.rstrip(':') + ': []'
            
            repaired_lines.append(line)
        
        # Reconstruct the JSON
        cleaned = '\n'.join(repaired_lines)
        
        # Ensure proper closing
        open_braces = cleaned.count('{')
        close_braces = cleaned.count('}')
        missing_braces = open_braces - close_braces
        
        if missing_braces > 0:
            cleaned += '\n' + '}' * missing_braces
        
        print(f"🔧 JSON repair completed")

    try:
        date_range_result = date_range_parser.parse(cleaned)
        
        # CREATE FACTOR-TIME MAPPING DataFrame
        import pandas as pd
        from datetime import datetime
        
        factor_time_mapping = []
        
        # Process macro factors
        for factor_name, date_ranges in date_range_result.macro.items():
            for date_range in date_ranges:
                if date_range:  # Skip empty ranges
                    start_date, end_date = date_range
                    factor_time_mapping.append({
                        'factor_name': factor_name,
                        'scope': 'macro',
                        'start_date': start_date,
                        'end_date': end_date,
                        'time_interval': f"{start_date} to {end_date}",
                        'duration_days': (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days if start_date and end_date else 0
                    })
        
        # Process micro factors
        for factor_name, date_ranges in date_range_result.micro.items():
            for date_range in date_ranges:
                if date_range:  # Skip empty ranges
                    start_date, end_date = date_range
                    factor_time_mapping.append({
                        'factor_name': factor_name,
                        'scope': 'micro',
                        'start_date': start_date,
                        'end_date': end_date,
                        'time_interval': f"{start_date} to {end_date}",
                        'duration_days': (datetime.strptime(end_date, '%Y-%m-%d') - datetime.strptime(start_date, '%Y-%m-%d')).days if start_date and end_date else 0
                    })
        
        # Create DataFrame
        factor_time_df = pd.DataFrame(factor_time_mapping)
        
        return date_range_result, factor_time_df
        
    except Exception as exc:
        print(f"❌ Raw response: {raw_response}")
        print(f"❌ Cleaned response: {cleaned}")
        raise ValueError(f"Date range mapping response could not be parsed:\n{raw_response}") from exc

def step1_get_factors(ticker: str, language: str = "English"):
    """Step 1: Get micro + macro factors (no sector)"""
    print(f"🔍 Step 1: Getting MICRO + MACRO factors for {ticker}")
    
    # Read stock intelligence from Redis
    read_information = quant_market_expectation_read_agent(ticker)
    if not read_information:
        raise ValueError(f"No stock intelligence found for {ticker}")
        
    # Generate factors using LLM
    factor_result = generate_stock_factors(
        ticker=ticker, 
        read_information=read_information,
        language=language
    )
    
    # FIXED FACTOR EXTRACTION: 10 factors per scope
    smart_factor_count = 10
    
    print(f"   📊 Extracting {smart_factor_count} factors per scope (FIXED MODE)")
    
    # Extract factors dynamically
    macro_factors = []
    micro_factors = []
    
    for i in range(1, smart_factor_count + 1):
        try:
            macro_factor = getattr(factor_result.macro, f'factor_{i}', None)
            micro_factor = getattr(factor_result.micro, f'factor_{i}', None)
            
            if macro_factor:
                macro_factors.append(macro_factor)
            if micro_factor:
                micro_factors.append(micro_factor)
        except AttributeError:
            # Factor doesn't exist, skip it
            continue
    
    print(f"✅ Generated {len(macro_factors)} macro factors")
    print(f"✅ Generated {len(micro_factors)} micro factors")
    
    # Debug: Show actual factors extracted
    if macro_factors:
        print(f"   📋 Macro factors: {macro_factors[:3]}{'...' if len(macro_factors) > 3 else ''}")
    if micro_factors:
        print(f"   📋 Micro factors: {micro_factors[:3]}{'...' if len(micro_factors) > 3 else ''}")
    
    return {
        "factor_payload": factor_result,
        "macro_factors": macro_factors,
        "micro_factors": micro_factors,
        "read_information": read_information
    }
    
def get_stock_prices_fmp(ticker: str, start_date: str, end_date: str, api_key: str = None) -> pd.DataFrame:
    """Get stock prices from FMP API"""
    if api_key is None:
        api_key = FMP_API_KEY
    
    url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"
    params = {
        'from': start_date,
        'to': end_date,
        'apikey': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if 'historical' in data:
            df = pd.DataFrame(data['historical'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            return df[['date', 'close']]
        else:
            print(f"❌ No historical data found for {ticker}")
            return pd.DataFrame()
            
    except Exception as e:
        print(f"❌ Error fetching data for {ticker}: {e}")
        return pd.DataFrame()

def calculate_annual_volatility(ticker: str, start_date: str, end_date: str) -> float:
    """Calculate annual volatility for the stock"""
    try:
        stock_df = get_stock_prices_fmp(ticker, start_date, end_date)
        if stock_df.empty:
            print(f"❌ No price data found for {ticker} volatility calculation")
            return 0.0
        
        stock_df['daily_return'] = stock_df['close'].pct_change()
        stock_df = stock_df.dropna()
        
        if len(stock_df) < 10:
            print(f"❌ Insufficient data for volatility calculation ({len(stock_df)} days)")
            return 0.0
        
        daily_volatility = stock_df['daily_return'].std()
        annual_volatility = daily_volatility * np.sqrt(252)
        
        print(f"   📊 Annual Volatility for {ticker}: {annual_volatility:.4f} ({annual_volatility*100:.2f}%)")
        return annual_volatility
    except Exception as e:
        print(f"❌ Error calculating volatility for {ticker}: {e}")
        return 0.0

def map_date_range_to_trend_data(start_date: str, end_date: str, historical_trends: Dict[str, Any]) -> Dict[str, Any]:
    """
    Map a date range to the corresponding trend data using exact key matching
    Returns stock return rate and SPY return rate for the period
    """
    # Clean dates first
    def clean_date(date_str):
        """Clean malformed dates like '2022024-10-11' -> '2024-10-11'"""
        if not date_str:
            return None
        # Remove duplicate year patterns
        cleaned = date_str.replace('2022024', '2024').replace('20202024', '2024')
        return cleaned
    
    start_date_clean = clean_date(start_date)
    end_date_clean = clean_date(end_date)
    
    if not start_date_clean or not end_date_clean:
        print(f"⚠️ Invalid dates: {start_date} to {end_date}")
        return {
            "stock_daily_return": 0.0,
            "spy_daily_return": 0.0,
            "trend_key": "invalid_dates"
        }
    
    # Create the exact period key format that matches your database
    period_key = f"{start_date_clean} to {end_date_clean}"
    
    # Look for exact match in trend periods
    for trend_key, trend_data in historical_trends.items():
        trend_period = trend_data.get('current', '')  # This contains "2025-07-07 to 2025-07-23"
        
        if period_key == trend_period:
            stock_return = trend_data.get('day average_return', 0.0)
            spy_return = trend_data.get('SPY_return_rate', 0.0)
            
            # Handle None values
            if stock_return is None:
                stock_return = 0.0
            if spy_return is None:
                spy_return = 0.0
                
            return {
                "stock_daily_return": stock_return,
                "spy_daily_return": spy_return,
                "trend_key": trend_key
            }
    
    # If no exact match found, try to find closest match
    print(f"⚠️ No exact trend data found for period {period_key}")
    
    # Debug: show available periods
    available_periods = [trend_data.get('current', '') for trend_data in historical_trends.values()]
    print(f"🔍 Available periods: {available_periods[:3]}...")  # Show first 3
    
    return {
        "stock_daily_return": 0.0,
        "spy_daily_return": 0.0,
        "trend_key": "no_match"
    }

def step3_beta_filtering(ticker: str, step2_result: Any, read_information: Dict[str, Any], 
                        market_beta: float = 1.2777, alpha_daily: float = 0.0, market_ticker: str = "SPY", 
                        risk_free_rate: float = 0.025) -> Dict[str, Any]:
    """
    Step 3: Beta Filtering - Calculate real market data and beta-adjusted impact
    DAILY RETURNS: Use daily returns throughout
    NOW USES SPY_RETURN_RATE from stock trend database instead of fetching SPY data
    INCLUDES VOLATILITY NORMALIZATION using annual_volatility / 15.874
    
    Args:
        ticker: Stock ticker (e.g., 'UNH')
        step2_result: Date ranges from Step 2
        read_information: Stock trend data from Step 1 (contains historical_trends)
        market_ticker: Market benchmark (default: 'SPY') - not used anymore
        risk_free_rate: Annual risk-free rate (default: 2.5%)
    
    Returns:
        dict: Beta-filtered factor impacts with volatility normalization
    """
    print(f"🔍 Step 3: Beta filtering for {ticker}")
    print(f"   Using SPY_return_rate from stock trend database")
    print(f"   Using market beta: {market_beta:.4f}")
    print(f"   Using alpha (daily): {alpha_daily:.6f} ({alpha_daily*100:.4f}%)")
    print(f"   Risk-free rate: {risk_free_rate:.1%} annual")
    
    # Extract historical trends from read_information
    historical_trends = read_information.get('historical_trends', {})
    if not historical_trends:
        print("❌ No historical trends found in read_information")
        return {"error": "No historical trends found"}
    
    print(f"   Found {len(historical_trends)} historical trend periods")
    
    # Get date ranges for macro and micro factors
    macro_date_ranges = step2_result.macro
    micro_date_ranges = step2_result.micro
    
    # Calculate date range for fetching data (get all dates needed)
    all_dates = []
    for factor_ranges in macro_date_ranges.values():
        all_dates.extend(factor_ranges)
    for factor_ranges in micro_date_ranges.values():
        all_dates.extend(factor_ranges)
    
    if not all_dates:
        print("❌ No date ranges found")
        return {"error": "No date ranges found"}
    
    # Get overall date range
    min_date = min([min(date_range) for date_range in all_dates if date_range])
    max_date = max([max(date_range) for date_range in all_dates if date_range])
    
    print(f"   Processing date ranges from {min_date} to {max_date}")
    
    # Calculate annual volatility for the stock
    annual_volatility = calculate_annual_volatility(ticker, min_date, max_date)
    volatility_factor = annual_volatility / 15.874
    
    print(f"   🔧 Volatility Factor (vol/15.874): {volatility_factor:.4f}")
    
    # Calculate risk-free rate for the period (daily)
    risk_free_rate_period = risk_free_rate
    
    # Process macro factors
    macro_results = {}
    print(f"\n Processing {len(macro_date_ranges)} macro factors...")
    
    for factor_name, date_ranges in macro_date_ranges.items():
        factor_impacts = []
        
        for start_date, end_date in date_ranges:
            # Get stock and SPY returns from historical trends
            trend_data = map_date_range_to_trend_data(start_date, end_date, historical_trends)
            stock_daily_return = trend_data["stock_daily_return"]
            spy_daily_return = trend_data["spy_daily_return"]
            
            # Calculate risk-free return for this period (daily)
            from datetime import datetime
            
            # Clean and validate dates
            def clean_date(date_str):
                """Clean malformed dates like '2022024-10-11' -> '2024-10-11'"""
                if not date_str:
                    return None
                # Remove duplicate year patterns
                cleaned = date_str.replace('2022024', '2024').replace('20202024', '2024')
                try:
                    datetime.strptime(cleaned, '%Y-%m-%d')
                    return cleaned
                except ValueError:
                    print(f"⚠️ Invalid date format: {date_str}")
                    return None
            
            start_date_clean = clean_date(start_date)
            end_date_clean = clean_date(end_date)
            
            if not start_date_clean or not end_date_clean:
                print(f"⚠️ Skipping invalid date range: {start_date} to {end_date}")
                continue
                
            days = (datetime.strptime(end_date_clean, '%Y-%m-%d') - datetime.strptime(start_date_clean, '%Y-%m-%d')).days
            risk_free_daily = risk_free_rate_period / 365  # Daily risk-free rate
            
            # Calculate beta-adjusted macro impact (CORRECT FORMULA)
            real_macro_impact = market_beta * spy_daily_return
            
            # Calculate micro impact (what's left after macro)
            real_micro_impact = stock_daily_return - real_macro_impact
            
            # Apply volatility normalization to micro impact
            if real_micro_impact > 0:
                normalized_micro_impact = real_micro_impact - volatility_factor
            else:
                normalized_micro_impact = real_micro_impact + volatility_factor
            
            factor_impacts.append({
                "period": f"{start_date} to {end_date}",
                "days": days,
                "stock_daily_return": stock_daily_return,  # DAILY return from trend data
                "spy_daily_return": spy_daily_return,      # DAILY return from trend data
                "risk_free_daily": risk_free_daily,
                "real_macro_impact": real_macro_impact,
                "real_micro_impact": real_micro_impact,
                "normalized_micro_impact": normalized_micro_impact,
                "volatility_factor": volatility_factor,
                "trend_key": trend_data["trend_key"]
            })
        
        macro_results[factor_name] = factor_impacts
        print(f"   ✅ {factor_name}: {len(factor_impacts)} periods")
    
    # Process micro factors
    micro_results = {}
    print(f"\n Processing {len(micro_date_ranges)} micro factors...")
    
    for factor_name, date_ranges in micro_date_ranges.items():
        if not date_ranges:  # Skip empty date ranges
            continue
            
        factor_impacts = []
        
        for start_date, end_date in date_ranges:
            # Get stock and SPY returns from historical trends
            trend_data = map_date_range_to_trend_data(start_date, end_date, historical_trends)
            stock_daily_return = trend_data["stock_daily_return"]
            spy_daily_return = trend_data["spy_daily_return"]
            
            # Calculate risk-free return for this period (daily)
            
            # Clean and validate dates
            def clean_date(date_str):
                """Clean malformed dates like '2022024-10-11' -> '2024-10-11'"""
                if not date_str:
                    return None
                # Remove duplicate year patterns
                cleaned = date_str.replace('2022024', '2024').replace('20202024', '2024')
                try:
                    datetime.strptime(cleaned, '%Y-%m-%d')
                    return cleaned
                except ValueError:
                    print(f"⚠️ Invalid date format: {date_str}")
                    return None
            
            start_date_clean = clean_date(start_date)
            end_date_clean = clean_date(end_date)
            
            if not start_date_clean or not end_date_clean:
                print(f"⚠️ Skipping invalid date range: {start_date} to {end_date}")
                continue
                
            days = (datetime.strptime(end_date_clean, '%Y-%m-%d') - datetime.strptime(start_date_clean, '%Y-%m-%d')).days
            risk_free_daily = risk_free_rate_period / 365  # Daily risk-free rate
            
            # Calculate beta-adjusted macro impact (CORRECT FORMULA)
            real_macro_impact = market_beta * spy_daily_return
            
            # Calculate micro impact (what's left after macro)
            real_micro_impact = stock_daily_return - real_macro_impact
            
            # Apply volatility normalization to micro impact
            if real_micro_impact > 0:
                normalized_micro_impact = real_micro_impact - volatility_factor
            else:
                normalized_micro_impact = real_micro_impact + volatility_factor
            
            factor_impacts.append({
                "period": f"{start_date} to {end_date}",
                "days": days,
                "stock_daily_return": stock_daily_return,  # DAILY return from trend data
                "spy_daily_return": spy_daily_return,      # DAILY return from trend data
                "risk_free_daily": risk_free_daily,
                "real_macro_impact": real_macro_impact,
                "real_micro_impact": real_micro_impact,
                "normalized_micro_impact": normalized_micro_impact,
                "volatility_factor": volatility_factor,
                "trend_key": trend_data["trend_key"]
            })
        
        micro_results[factor_name] = factor_impacts
        print(f"   ✅ {factor_name}: {len(factor_impacts)} periods")
    
    # Calculate weighted averages (using duration as weights)
    def calculate_weighted_averages(factor_results: Dict[str, List[Dict]]) -> Dict[str, Dict[str, float]]:
        """Calculate weighted averages for each factor"""
        weighted_results = {}
        
        for factor_name, impacts in factor_results.items():
            if not impacts:
                continue
                
            total_duration = sum(impact['days'] for impact in impacts)
            weighted_macro_sum = sum(impact['days'] * impact['real_macro_impact'] for impact in impacts)
            weighted_micro_sum = sum(impact['days'] * impact['real_micro_impact'] for impact in impacts)
            weighted_normalized_micro_sum = sum(impact['days'] * impact['normalized_micro_impact'] for impact in impacts)
            
            weighted_results[factor_name] = {
                "weighted_macro_impact": weighted_macro_sum / total_duration if total_duration > 0 else 0,
                "weighted_micro_impact": weighted_micro_sum / total_duration if total_duration > 0 else 0,
                "weighted_normalized_micro_impact": weighted_normalized_micro_sum / total_duration if total_duration > 0 else 0,
                "total_duration": total_duration,
                "periods": len(impacts)
            }
        
        return weighted_results
    
    macro_weighted = calculate_weighted_averages(macro_results)
    micro_weighted = calculate_weighted_averages(micro_results)
    
    print(f"\n✅ Beta filtering completed!")
    print(f"   Processed {len(macro_results)} macro factors")
    print(f"   Processed {len(micro_results)} micro factors")
    print(f"   Used SPY_return_rate from stock trend database")
    print(f"   Applied volatility normalization: {volatility_factor:.4f}")
    
    return {
        "ticker": ticker,
        "market_beta": market_beta,
        "alpha_daily": alpha_daily,
        "risk_free_rate": risk_free_rate,
        "annual_volatility": annual_volatility,
        "volatility_factor": volatility_factor,
        "macro_results": macro_results,
        "micro_results": micro_results,
        "macro_weighted": macro_weighted,
        "micro_weighted": micro_weighted,
        "data_period": f"{min_date} to {max_date}"
    }

def step4_impact_metrics(step3_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Step 4: Generate final impact metrics in Quant Agent format
    
    Args:
        step3_result: Beta filtering results from Step 3 (with daily returns)
    
    Returns:
        dict: Final aggregated metrics matching Quant Agent format
    """
    print(f"🔍 Step 4: Generating impact metrics for {step3_result['ticker']}")
    
    # Extract data from step3_result
    macro_weighted = step3_result['macro_weighted']
    micro_weighted = step3_result['micro_weighted']
    market_beta = step3_result['market_beta']
    risk_free_rate = step3_result['risk_free_rate']
    
    # Convert to Quant Agent format
    aggregated_metrics = {
        "macro": {},
        "micro": {}
    }
    
    # Process macro factors
    print(f"\n Processing {len(macro_weighted)} macro factors...")
    
    for factor_name, factor_data in macro_weighted.items():
        # Calculate variance from the weighted impacts
        macro_impact = factor_data['weighted_macro_impact']
        total_duration = factor_data['total_duration']
        periods = factor_data['periods']
        
        # Estimate variance (this could be improved with actual variance calculation)
        # For now, use a reasonable estimate based on typical market variance
        estimated_variance = abs(macro_impact) * 0.1  # 10% of absolute impact as variance estimate
        
        aggregated_metrics["macro"][factor_name] = {
            "weighted_mean": macro_impact,
            "weighted_variance": estimated_variance,
            "total_duration": total_duration,
            "periods": periods
        }
        
        print(f"   ✅ {factor_name}: μ={macro_impact:.4f}, σ²={estimated_variance:.4f}")
    
    # Process micro factors
    print(f"\n Processing {len(micro_weighted)} micro factors...")
    
    for factor_name, factor_data in micro_weighted.items():
        # Calculate variance from the weighted impacts
        micro_impact = factor_data['weighted_micro_impact']
        total_duration = factor_data['total_duration']
        periods = factor_data['periods']
        
        # Estimate variance (this could be improved with actual variance calculation)
        # For now, use a reasonable estimate based on typical micro variance
        estimated_variance = abs(micro_impact) * 0.15  # 15% of absolute impact as variance estimate
        
        aggregated_metrics["micro"][factor_name] = {
            "weighted_mean": micro_impact,
            "weighted_variance": estimated_variance,
            "total_duration": total_duration,
            "periods": periods
        }
        
        print(f"   ✅ {factor_name}: μ={micro_impact:.4f}, σ²={estimated_variance:.4f}")
    
    # Generate summary DataFrame in Quant Agent format
    summary_data = []
    
    for scope, factors in aggregated_metrics.items():
        for factor_name, factor_data in factors.items():
            summary_data.append({
                "scope": scope,
                "factor": factor_name,
                "trend_count": factor_data["periods"],
                "weighted_mean": factor_data["weighted_mean"],
                "weighted_variance": factor_data["weighted_variance"],
                "average_duration": factor_data["total_duration"] / factor_data["periods"] if factor_data["periods"] > 0 else 0,
                "total_duration": factor_data["total_duration"]
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    return {
        "ticker": step3_result['ticker'],
        "market_beta": market_beta,
        "risk_free_rate": risk_free_rate,
        "aggregated_metrics": aggregated_metrics,
        "summary_df": summary_df
    }

def step2_get_date_ranges(ticker: str, factor_result: Dict[str, Any], language: str = "English"):
    """Step 2: Map micro + macro factors to date ranges"""
    print(f"🔍 Step 2: Mapping MICRO + MACRO factors to date ranges for {ticker}")
    
    factor_payload = factor_result["factor_payload"]
    read_information = factor_result["read_information"]
    
    # Map factors to date ranges using LLM
    date_range_result, factor_time_df = map_factors_to_date_ranges(
        ticker=ticker,
        factor_payload=factor_payload,
        read_information=read_information,
        language=language
    )
    
    print(f"✅ Mapped macro factors to date ranges")
    print(f"✅ Mapped micro factors to date ranges")
    
    # Return the result (map_factors_to_date_ranges already handles the factor_time_df)
    return date_range_result, factor_time_df
    
# =============================================================================
# QUANT IMPACT RISK ANALYSIS FUNCTIONS (FROM DYNAMIC_ALPHA.IPYNB)
# =============================================================================

def calculate_trend_weighted_score(summary_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate trend-weighted scores for each factor
    
    Args:
        summary_df: DataFrame with columns ['scope', 'factor', 'trend_count', 'weighted_mean', 'weighted_variance']
    
    Returns:
        DataFrame with additional columns for trend-weighted metrics
    """
    # Calculate total trend count across all factors
    total_trends = summary_df['trend_count'].sum()
    
    # Calculate trend weight score (trend_count / total_trends)
    summary_df['trend_weight_score'] = summary_df['trend_count'] / total_trends
    
    # Calculate score-weighted mean and variance
    summary_df['score_weighted_mean'] = summary_df['trend_weight_score'] * summary_df['weighted_mean']
    summary_df['score_weighted_variance'] = summary_df['trend_weight_score'] * summary_df['weighted_variance']
    
    return summary_df

def calculate_macro_micro_risk_share(summary_df: pd.DataFrame) -> Dict[str, float]:
    """
    Calculate Macro vs Micro Risk Share Index
    
    Args:
        summary_df: DataFrame with trend-weighted metrics
    
    Returns:
        Dict with macro and micro risk share percentages
    """
    # Sum contributions by scope
    macro_contributions = summary_df[summary_df['scope'] == 'macro']['score_weighted_variance'].sum()
    micro_contributions = summary_df[summary_df['scope'] == 'micro']['score_weighted_variance'].sum()
    
    total_contributions = macro_contributions + micro_contributions
    
    if total_contributions == 0:
        return {"macro_risk_share": 0.0, "micro_risk_share": 0.0}
    
    macro_risk_share = (macro_contributions / total_contributions) * 100
    micro_risk_share = (micro_contributions / total_contributions) * 100
    
    return {
        "macro_risk_share": macro_risk_share,
        "micro_risk_share": micro_risk_share,
        "risk_environment": f"Current risk environment is {micro_risk_share:.1f}% company-driven, {macro_risk_share:.1f}% macro-driven."
    }

def calculate_factor_volatility_separated(summary_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate Factor Volatility DataFrames with HIGH/LOW classification - SEPARATED by macro/micro
    
    Args:
        summary_df: DataFrame with trend-weighted metrics
    
    Returns:
        Tuple of (macro_volatility_df, micro_volatility_df)
    """
    volatility_df = summary_df.copy()
    
    # Calculate volatility (square root of weighted variance)
    volatility_df['volatility'] = np.sqrt(volatility_df['weighted_variance'])
    volatility_df['score_weighted_volatility'] = np.sqrt(volatility_df['score_weighted_variance'])
    
    # Separate by scope
    macro_volatility_df = volatility_df[volatility_df['scope'] == 'macro'].copy()
    micro_volatility_df = volatility_df[volatility_df['scope'] == 'micro'].copy()
    
    # Classify volatility levels for macro factors
    if not macro_volatility_df.empty:
        macro_volatility_median = macro_volatility_df['volatility'].median()
        macro_volatility_df['volatility_level'] = macro_volatility_df['volatility'].apply(
            lambda x: 'HIGH' if x > macro_volatility_median else 'LOW'
        )
    
    # Classify volatility levels for micro factors
    if not micro_volatility_df.empty:
        micro_volatility_median = micro_volatility_df['volatility'].median()
        micro_volatility_df['volatility_level'] = micro_volatility_df['volatility'].apply(
            lambda x: 'HIGH' if x > micro_volatility_median else 'LOW'
        )
    
    return macro_volatility_df, micro_volatility_df

def calculate_risk_reward_ratio(summary_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate Risk-Reward Ratio for each factor
    
    Args:
        summary_df: DataFrame with trend-weighted metrics
    
    Returns:
        DataFrame with risk-reward ratio calculations
    """
    impact_metrics_df = summary_df.copy()
    
    # Calculate risk-reward ratio (absolute mean / volatility)
    impact_metrics_df['risk_reward_ratio'] = np.abs(impact_metrics_df['weighted_mean']) / np.sqrt(impact_metrics_df['weighted_variance'])
    
    # Handle division by zero
    impact_metrics_df['risk_reward_ratio'] = impact_metrics_df['risk_reward_ratio'].replace([np.inf, -np.inf], 0)
    
    return impact_metrics_df

def calculate_final_impact_separated(summary_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Calculate Total Impact DataFrames - SEPARATED by macro/micro
    Formula: total_impact = (1 + weighted_mean)^average_duration - 1
    
    Args:
        summary_df: DataFrame with columns ['scope', 'factor', 'weighted_mean', 'average_duration']
    
    Returns:
        Tuple of (macro_total_impact_df, micro_total_impact_df)
    """
    # Separate macro and micro data
    macro_df = summary_df[summary_df['scope'] == 'macro'].copy()
    micro_df = summary_df[summary_df['scope'] == 'micro'].copy()
    
    # Calculate total impact using compound return formula
    # Formula: (1 + daily_return_rate)^average_duration - 1
    # Apply stabilization: cap micro impact duration at 7 days maximum
    macro_df['final_impact'] = (1 + macro_df['weighted_mean']) ** macro_df['average_duration'] - 1
    micro_df['stabilized_duration'] = micro_df['average_duration'].clip(upper=7)  # Cap at 7 days
    micro_df['final_impact'] = (1 + micro_df['weighted_mean']) ** micro_df['stabilized_duration'] - 1
    
    # Sort by total impact (highest first)
    macro_df = macro_df.sort_values('final_impact', ascending=False)
    micro_df = micro_df.sort_values('final_impact', ascending=False)
    
    # Return only factor name and total impact
    macro_total_impact = macro_df[['factor', 'final_impact']].reset_index(drop=True)
    micro_total_impact = micro_df[['factor', 'final_impact']].reset_index(drop=True)
    
    return macro_total_impact, micro_total_impact

def generate_impact_summary_schema(summary_df, language="English"):
    """
    Let LLM analyze the whole dataset and classify factors by row numbers
    """
    
    print("🔍 Letting LLM analyze dataset and classify factors...")
    
    # Add row index as column for LLM reference
    summary_df_with_index = summary_df.reset_index()
    
    # Create dataset string for LLM
    dataset_str = summary_df_with_index.to_string(index=False)
    
    # LLM analyzes and outputs mappings
    prompt = f"""
You are a financial analyst expert. Analyze the dataset below and classify factors into neutral categories.

DATASET:
{dataset_str}

REQUIREMENTS:
1. Classify into <=3 neutral categories for each scope (macro, micro, sector)
2. For each category, list the ROW NUMBERS (index column) that belong to it
3. Use neutral English names like "Monetary Policy", "Trade Policy", "Company Performance", etc.
4. Output clean JSON structure
5. If something is relative with the industry, the sector, (ex: mention about this industry valuation) consider it as sector 
6. You should extract the factors name and corresponding weight average in original numerical value 

EXAMPLE OUTPUT:
{{
    "macro_factors": [
        {{
            "factor_name": "Monetary Policy Impact",
            "row_numbers": [0, 8, 9],
            "max_return": "0.99",
            "min_return": "-0.57"
        }}
    ],
    "micro_factors": [
        {{
            "factor_name": "Company Performance", 
            "row_numbers": [20, 21],
            "max_return": "3.23",
            "min_return": "-1.28"
        }}
    ],
    "sector_factors": [
        {{
            "factor_name": "Technology Trends",
            "row_numbers": [13, 16],
            "max_return": "0.87",
            "min_return": "-0.34"
        }}
    ]
}}

Return ONLY the JSON structure, no other text.

You must return the text in the following language:
{language}
"""
    
    try:
        llm = LLMCallAgent()
        
        print("🤖 Calling LLM to analyze dataset...")
        response = llm.call_llm(prompt, model="deepseek-chat")
        
        # Parse JSON response
        json_start = response.find('{')
        json_end = response.rfind('}') + 1
        json_str = response[json_start:json_end]
        
        classification = json.loads(json_str)
        
        # Calculate max/min from actual weighted_mean values using row numbers
        result = {}
        
        for category, factors in classification.items():
            result[category] = []
            
            for factor_group in factors:
                row_numbers = factor_group['row_numbers']
                
                # Get weighted_mean values for these rows
                factor_df = summary_df.iloc[row_numbers]
                weighted_values = factor_df['weighted_mean']  # keep the original value
                
                updated_group = {
                    "factor_name": factor_group['factor_name'],
                    "row_numbers": row_numbers,
                    "sub_factors": list(factor_df['factor']),  # Factor names from those rows
                    "max_return": f"{weighted_values.max()}",
                    "min_return": f"{weighted_values.min()}",
                    "raw_values": list(weighted_values)  # Actual weighted_mean values
                }
                
                result[category].append(updated_group)
        
        print("✅ Schema Generated!")
        print(f"📊 Macro: {len(result.get('macro_factors', []))} groups")
        print(f"📊 Micro: {len(result.get('micro_factors', []))} groups") 
        print(f"📊 Sector: {len(result.get('sector_factors', []))} groups")

        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": str(e)}


def convert_schema_to_compound_datasets(schema_result, summary_df):
    """
    Convert schema result into clean DataFrame with COMPOUND FORMULA applied
    Formula: (1 + weighted_mean)^average_duration - 1
    """
    print("🔄 Converting schema to compound datasets...")
    
    # Safe formatting for arrays with < 3 elements
    def safe_format_array(arr, fmt, max_show=3):
        if len(arr) == 0:
            return '[]'
        elif len(arr) == 1:
            return f'[{fmt.format(arr[0])}]'
        elif len(arr) == 2:
            return f'[{fmt.format(arr[0])}, {fmt.format(arr[1])}]'
        else:
            shown = arr[:max_show]
            formatted = ', '.join([fmt.format(x) for x in shown])
            return f'[{formatted}, ...]' + (f', +{len(arr)-max_show} more' if len(arr) > max_show else '')
    
    # Convert to flat structure with compound calculations
    all_factors = []
    
    for category, factor_groups in schema_result.items():
        for group in factor_groups:
            category_name = category.replace('_factors', '').title()
            row_numbers = group['row_numbers']
            
            # Get the relevant rows from summary_df
            factor_rows = summary_df.iloc[row_numbers]
            
            # Calculate compound returns for each sub-factor
            weighted_means = factor_rows['weighted_mean'].values
            avg_durations = factor_rows['average_duration'].values
            
            # Apply compound formula: (1 + weighted_mean)^average_duration - 1
            compound_returns = []
            for wm, duration in zip(weighted_means, avg_durations):
                compound = (1 + wm) ** duration - 1
                compound_returns.append(compound)
            
            compound_returns = np.array(compound_returns)
            
            max_compound = compound_returns.max()
            min_compound = compound_returns.min()
            max_min_ratio = max_compound / min_compound if min_compound != 0 else float('inf')
            
            factor_row = {
                'category': category_name,
                'factor_name': group['factor_name'],
                'max_compound_return': max_compound,
                'min_compound_return': min_compound,
                'max_min_ratio': max_min_ratio,
                'return_range': max_compound - min_compound,
                'sub_factor_count': len(group['sub_factors']),
                'sub_factors': ' | '.join(group['sub_factors']),
                'row_numbers': str(group['row_numbers']),
                'weighted_means': safe_format_array(weighted_means, '{:.4f}'),
                'avg_durations': safe_format_array(avg_durations, '{:.1f}'),
                'compound_returns': safe_format_array(compound_returns, '{:.3f}')
            }
            
            all_factors.append(factor_row)
    
    # Create DataFrame
    clean_df = pd.DataFrame(all_factors)
    
    # Sort by max_compound_return (highest to lowest)
    clean_df = clean_df.sort_values('max_compound_return', ascending=False).reset_index(drop=True)
    
    print("📊 Compound Dataset Generated!")
    print(f"   Total factor categories: {len(clean_df)}")
    
    return clean_df


def quant_impact_risk_analysis(summary_df: pd.DataFrame) -> Tuple[Dict[str, float], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Complete Quant Impact Risk Analysis Pipeline - UPDATED to return separate macro/micro volatility DataFrames and total impact DataFrames
    
    Args:
        summary_df: DataFrame with columns ['scope', 'factor', 'trend_count', 'weighted_mean', 'weighted_variance', 'total_duration']
    
    Returns:
        Tuple of:
        1. Macro vs Micro Risk Share Index
        2. Macro Factor Volatility DataFrame (with HIGH/LOW classification)
        3. Micro Factor Volatility DataFrame (with HIGH/LOW classification)  
        4. Risk-Reward Ratio DataFrame (first 3 columns only)
        5. Macro Total Impact DataFrame (factor, total_impact)
        6. Micro Total Impact DataFrame (factor, total_impact)
    """
    print("🔍 Starting Quant Impact Risk Analysis...")
    
    # Step 1: Calculate trend-weighted scores
    print("📊 Calculating trend-weighted scores...")
    enhanced_df = calculate_trend_weighted_score(summary_df.copy())
    
    # Step 2: Calculate Macro vs Micro Risk Share
    print("📈 Calculating Macro vs Micro Risk Share...")
    risk_share_index = calculate_macro_micro_risk_share(enhanced_df)
    
    # Step 3: Calculate Factor Volatility (SEPARATED by macro/micro)
    print("📉 Calculating Factor Volatility (separated)...")
    macro_volatility_df, micro_volatility_df = calculate_factor_volatility_separated(enhanced_df)
    
    # Step 4: Calculate Risk-Reward Ratio (first 3 columns only)
    print("⚖️ Calculating Risk-Reward Ratio...")
    impact_metrics_df = calculate_risk_reward_ratio(enhanced_df)
    
    # Step 5: Calculate Total Impact (SEPARATED by macro/micro)
    print("💥 Calculating Total Impact (compound formula)...")
    macro_total_impact_df, micro_total_impact_df = calculate_final_impact_separated(enhanced_df)
    
    print("✅ Quant Impact Risk Analysis completed!")
    print(f"   📊 Macro volatility factors: {len(macro_volatility_df)}")
    print(f"   📊 Micro volatility factors: {len(micro_volatility_df)}")
    print(f"   💥 Macro total impact factors: {len(macro_total_impact_df)}")
    print(f"   💥 Micro total impact factors: {len(micro_total_impact_df)}")
    
    return risk_share_index, macro_volatility_df, micro_volatility_df, impact_metrics_df, macro_total_impact_df, micro_total_impact_df

# =============================================================================
# TREEMAP VISUALIZATION FUNCTION (FROM DYNAMIC_ALPHA.IPYNB)
# =============================================================================

def generate_and_display_react_treemap(macro_df, micro_df, factor_time_df=None):
    """
    Generate React treemap with red/green colors and increased transparency
    
    Args:
        macro_df: DataFrame with macro factors and impacts
        micro_df: DataFrame with micro factors and impacts
        factor_time_df: Optional DataFrame with factor time intervals for card flip functionality
    """
    # Prepare data
    macro_data = []
    for _, row in macro_df.iterrows():
        macro_data.append({
            'factor': row['factor'],
            'impact': float(row['final_impact']),
            'abs_impact': abs(float(row['final_impact']))
        })
    
    micro_data = []
    for _, row in micro_df.iterrows():
        micro_data.append({
            'factor': row['factor'],
            'impact': float(row['final_impact']),
            'abs_impact': abs(float(row['final_impact']))
        })
    
    macro_data.sort(key=lambda x: x['abs_impact'], reverse=True)
    micro_data.sort(key=lambda x: x['abs_impact'], reverse=True)
    
    # Prepare factor time data for card flip functionality
    factor_time_data = {}
    if factor_time_df is not None and not factor_time_df.empty:
        for _, row in factor_time_df.iterrows():
            factor_name = row['factor_name']
            if factor_name not in factor_time_data:
                factor_time_data[factor_name] = []
            factor_time_data[factor_name].append({
                'start_date': row['start_date'],
                'end_date': row['end_date'],
                'time_interval': row['time_interval'],
                'duration_days': row['duration_days'],
                'scope': row['scope']
            })
    
    import json
    macro_json = json.dumps(macro_data, ensure_ascii=False)
    micro_json = json.dumps(micro_data, ensure_ascii=False)
    factor_time_json = json.dumps(factor_time_data, ensure_ascii=False)
    
    # Create HTML with red/green colors and increased transparency
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q&Q.AI - Impact Analysis</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            color: #ffffff;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }}

        .main-container {{
            position: relative;
            z-index: 2;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        .logo-section {{
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 20px;
            background: transparent;
        }}

        .logo-svg {{
            width: 500px;
            height: 200px;
            filter: drop-shadow(0 0 40px rgba(102, 126, 234, 0.8));
            animation: pulse-glow 4s ease-in-out infinite;
        }}

        @keyframes pulse-glow {{
            0%, 100% {{ filter: drop-shadow(0 0 40px rgba(102, 126, 234, 0.8)); }}
            50% {{ filter: drop-shadow(0 0 60px rgba(118, 75, 162, 1)); }}
        }}

        .logo-text {{
            font-size: 48px;
            font-weight: 200;
            color: #ffffff;
            letter-spacing: 12px;
            margin-top: 30px;
            text-shadow: 0 0 30px rgba(102, 126, 234, 0.8);
        }}

        .logo-description {{
            font-size: 20px;
            font-weight: 100;
            color: #a0aec0;
            letter-spacing: 4px;
            margin-top: 15px;
            opacity: 0.9;
        }}
        
        .tab-container {{
            display: flex;
            justify-content: center;
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border-radius: 12px;
            padding: 4px;
            width: fit-content;
            margin-left: auto;
            margin-right: auto;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .tab-button {{
            padding: 12px 24px;
            border: none;
            background: transparent;
            color: #a0aec0;
            cursor: pointer;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
        }}
        
        .tab-button.active {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }}
        
        .tab-button:hover:not(.active) {{
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }}
        
        .treemap-container {{
            width: 100%;
            height: 650px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            position: relative;
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(20px);
            overflow: hidden;
        }}
        
        .legend {{
            display: flex;
            justify-content: center;
            margin-top: 25px;
            gap: 40px;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 16px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(20px);
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }}
        
        .legend-color.positive {{
            background: linear-gradient(135deg, #10b981, #059669);
        }}
        
        .legend-color.negative {{
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }}
        
        .treemap-tooltip {{
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 12px 16px;
            border-radius: 8px;
            font-size: 13px;
            pointer-events: none;
            z-index: 1000;
            max-width: 250px;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
            border: 1px solid rgba(102, 126, 234, 0.3);
        }}
        
        .treemap-tooltip strong {{
            color: #fbbf24;
            font-weight: 600;
        }}
        
        .return-rate {{
            color: #10b981;
            font-weight: 600;
        }}
        
        .negative-rate {{
            color: #ef4444;
            font-weight: 600;
        }}
    </style>
</head>
<body>
    <div class="main-container">
        <div class="logo-section">
            <svg class="logo-svg" viewBox="0 0 360 150" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <linearGradient id="cleanGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#667eea;stop-opacity:1">
                            <animate attributeName="stop-color" 
                                    values="#667eea;#764ba2;#667eea" 
                                    dur="4s" repeatCount="indefinite"/>
                        </stop>
                        <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1">
                            <animate attributeName="stop-color" 
                                    values="#764ba2;#667eea;#764ba2" 
                                    dur="4s" repeatCount="indefinite"/>
                        </stop>
                    </linearGradient>
                    <filter id="subtleGlow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                        <feMerge> 
                            <feMergeNode in="coloredBlur"/>
                            <feMergeNode in="SourceGraphic"/>
                        </feMerge>
                    </filter>
                </defs>
                
                <!-- First Ellipse (Quantitative) -->
                <ellipse cx="150" cy="65" rx="50" ry="25" 
                      fill="none"
                      stroke="url(#cleanGradient)" 
                      stroke-width="5"
                      filter="url(#subtleGlow)"
                      opacity="0.9">
                    <animate attributeName="opacity" values="0.9;1;0.9" dur="3s" repeatCount="indefinite"/>
                </ellipse>

                <!-- Second Ellipse (Qualitative) -->
                <ellipse cx="210" cy="85" rx="50" ry="25" 
                      fill="none"
                      stroke="url(#cleanGradient)" 
                      stroke-width="5"
                      filter="url(#subtleGlow)"
                      opacity="0.9">
                    <animate attributeName="opacity" values="0.9;1;0.9" dur="3s" repeatCount="indefinite" begin="1.5s"/>
                </ellipse>

                <!-- Intersection area highlight -->
                <ellipse cx="180" cy="75" rx="20" ry="12" 
                      fill="url(#cleanGradient)" 
                      opacity="0.25"
                      filter="url(#subtleGlow)">
                    <animate attributeName="opacity" values="0.25;0.4;0.25" dur="3s" repeatCount="indefinite"/>
                </ellipse>
            </svg>
            <div class="logo-text">Q&Q.AI</div>
            <div class="logo-description">Quantitative & Qualitative AI Investment Analysis System</div>
        </div>
        
        <div class="tab-container">
            <button class="tab-button active" onclick="switchTab('macro')">Macro Factors</button>
            <button class="tab-button" onclick="switchTab('micro')">Micro Factors</button>
        </div>
        
        <div id="treemap" class="treemap-container"></div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color positive"></div>
                <span>Positive Return</span>
            </div>
            <div class="legend-item">
                <div class="legend-color negative"></div>
                <span>Negative Return</span>
            </div>
        </div>
    </div>

    <script>
        const macroData = {macro_json};
        const microData = {micro_json};
        const FactorTimeData = {factor_time_json};
        
        let currentData = macroData;
        
        // Create tooltip
        const tooltip = d3.select("body").append("div")
            .attr("class", "treemap-tooltip")
            .style("opacity", 0);
        
        // Function to wrap text into multiple lines
        function wrapText(text, width, fontSize) {{
            const words = text.split(' ');
            const lines = [];
            let currentLine = words[0];
            
            for (let i = 1; i < words.length; i++) {{
                const word = words[i];
                const testLine = currentLine + ' ' + word;
                const testWidth = testLine.length * fontSize * 0.6; // Approximate character width
                
                if (testWidth < width) {{
                    currentLine = testLine;
                }} else {{
                    lines.push(currentLine);
                    currentLine = word;
                }}
            }}
            lines.push(currentLine);
            return lines;
        }}
        
        function renderTreemap(data) {{
            const container = d3.select("#treemap");
            container.selectAll("*").remove();
            
            const width = container.node().offsetWidth;
            const height = 650;
            
            // Create treemap layout
            const treemap = d3.treemap()
                .size([width - 4, height - 4])
                .padding(2);
            
            // Prepare hierarchy
            const root = d3.hierarchy({{children: data}})
                .sum(d => d.abs_impact)
                .sort((a, b) => b.value - a.value);
            
            // Generate treemap
            treemap(root);
            
            // Create SVG container
            const svg = container
                .append("svg")
                .attr("width", width)
                .attr("height", height);
            
            // Create nodes
            const nodes = svg.selectAll(".node")
                .data(root.leaves())
                .enter().append("g")
                .attr("class", "node")
                .attr("transform", d => `translate(${{d.x0}}, ${{d.y0}})`);
            
            // Add rectangles with RED/GREEN colors and INCREASED TRANSPARENCY
            nodes.append("rect")
                .attr("width", d => d.x1 - d.x0)
                .attr("height", d => d.y1 - d.y0)
                .attr("class", d => d.data.impact >= 0 ? "positive" : "negative")
                .style("fill", d => d.data.impact >= 0 ? "rgba(16, 185, 129, 0.7)" : "rgba(239, 68, 68, 0.7)")  // Red/Green with 70% opacity
                .style("stroke", "#fff")
                .style("stroke-width", 2)
                .style("cursor", "pointer")
                .on("click", function(event, d) {{
                    toggleFactorCard(d.data.factor);
                }})
                .on("mouseover", function(event, d) {{
                    tooltip.transition()
                        .duration(200)
                        .style("opacity", .9);
                    tooltip.html(`
                        <strong>${{d.data.factor}}</strong><br/>
                        <span class="${{d.data.impact >= 0 ? 'return-rate' : 'negative-rate'}}">
                            Return Rate: ${{(d.data.impact * 100).toFixed(2)}}%
                        </span><br/>
                        <small>Click to view time intervals</small>
                    `)
                        .style("left", (event.pageX + 10) + "px")
                        .style("top", (event.pageY - 28) + "px");
                }})
                .on("mouseout", function(d) {{
                    tooltip.transition()
                        .duration(500)
                        .style("opacity", 0);
                }});
            
            // Calculate relative font sizes based on data range
            const impacts = data.map(d => d.abs_impact);
            const maxImpact = Math.max(...impacts);
            const minImpact = Math.min(...impacts);
            const impactRange = maxImpact - minImpact;
            
            // Add event names in TOP LEFT with BETTER VISIBILITY
            nodes.each(function(d) {{
                const node = d3.select(this);
                const rectWidth = d.x1 - d.x0;
                const rectHeight = d.y1 - d.y0;
                const normalizedImpact = (d.data.abs_impact - minImpact) / impactRange;
                
                // Bigger font size for better visibility
                const eventFontSize = 12 + (normalizedImpact * 10); // Range from 12px to 22px
                
                // Wrap text for event names
                const lines = wrapText(d.data.factor, rectWidth - 12, eventFontSize);
                const lineHeight = eventFontSize * 1.2;
                
                // Position event names in TOP LEFT with better contrast
                lines.forEach((line, i) => {{
                    node.append("text")
                        .attr("x", 8)  // Left margin
                        .attr("y", 16 + (i * lineHeight))  // Top margin
                        .attr("text-anchor", "start")
                        .attr("dominant-baseline", "middle")
                        .style("fill", "#ffffff")  // White text for good contrast
                        .style("font-size", eventFontSize + "px")
                        .style("font-weight", "900")  // Extra bold
                        .style("text-shadow", "2px 2px 4px rgba(0,0,0,0.8)")  // Black shadow
                        .text(line);
                }});
            }});
            
            // Add BIG IMPACT RATES in CENTER with better visibility
            nodes.append("text")
                .attr("x", d => (d.x1 - d.x0) / 2)
                .attr("y", d => (d.y1 - d.y0) / 2)
                .attr("text-anchor", "middle")
                .attr("dominant-baseline", "middle")
                .style("fill", "#ffffff")  // White text for good contrast
                .style("font-size", d => {{
                    const normalizedImpact = (d.data.abs_impact - minImpact) / impactRange;
                    const fontSize = 18 + (normalizedImpact * 18); // Range from 18px to 36px
                    return fontSize + "px";
                }})
                .style("font-weight", "900")  // Extra bold
                .style("text-shadow", "3px 3px 6px rgba(0,0,0,0.8)")  // Black shadow
                .text(d => {{
                    const rate = (d.data.impact * 100).toFixed(1);
                    return `${{rate > 0 ? '+' : ''}}${{rate}}%`;
                }});
        }}
        
        function switchTab(tab) {{
            // Update button states
            document.querySelectorAll('.tab-button').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
            
            // Switch data and render
            currentData = tab === 'macro' ? macroData : microData;
            renderTreemap(currentData);
        }}
        
        // Initial render
        // Factor Card Flip Functionality
        function toggleFactorCard(factorName) {{
            // Check if factor has time data
            if (!FactorTimeData[factorName] || FactorTimeData[factorName].length === 0) {{
                alert(`No time interval data available for factor: ${{factorName}}`);
                return;
            }}
            
            // Create or update factor card modal
            let modal = document.getElementById('factorCardModal');
            if (!modal) {{
                modal = createFactorCardModal();
            }}
            
            // Populate modal with factor time data
            populateFactorCard(factorName, FactorTimeData[factorName]);
            
            // Show modal
            modal.style.display = 'block';
        }}
        
        function createFactorCardModal() {{
            const modal = document.createElement('div');
            modal.id = 'factorCardModal';
            modal.style.cssText = `
                display: none;
                position: fixed;
                z-index: 1000;
                left: 0;
                top: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0,0,0,0.5);
                backdrop-filter: blur(5px);
            `;
            
            const modalContent = document.createElement('div');
            modalContent.style.cssText = `
                background-color: #1a202c;
                margin: 5% auto;
                padding: 20px;
                border: 1px solid #2d3748;
                border-radius: 12px;
                width: 80%;
                max-width: 600px;
                max-height: 80vh;
                overflow-y: auto;
                box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
            `;
            
            const closeButton = document.createElement('span');
            closeButton.innerHTML = '&times;';
            closeButton.style.cssText = `
                color: #a0aec0;
                float: right;
                font-size: 28px;
                font-weight: bold;
                cursor: pointer;
                line-height: 1;
            `;
            closeButton.onclick = () => modal.style.display = 'none';
            
            const title = document.createElement('h2');
            title.id = 'factorCardTitle';
            title.style.cssText = `
                color: #ffffff;
                margin: 0 0 20px 0;
                font-size: 24px;
                font-weight: 600;
            `;
            
            const content = document.createElement('div');
            content.id = 'factorCardContent';
            content.style.cssText = `
                color: #e2e8f0;
                line-height: 1.6;
            `;
            
            modalContent.appendChild(closeButton);
            modalContent.appendChild(title);
            modalContent.appendChild(content);
            modal.appendChild(modalContent);
            
            // Close modal when clicking outside
            modal.onclick = (event) => {{
                if (event.target === modal) {{
                    modal.style.display = 'none';
                }}
            }};
            
            document.body.appendChild(modal);
            return modal;
        }}
        
        function populateFactorCard(factorName, timeIntervals) {{
            const title = document.getElementById('factorCardTitle');
            const content = document.getElementById('factorCardContent');
            
            title.textContent = factorName;
            
            // Group intervals by scope
            const macroIntervals = timeIntervals.filter(interval => interval.scope === 'macro');
            const microIntervals = timeIntervals.filter(interval => interval.scope === 'micro');
            
            let html = '';
            
            if (macroIntervals.length > 0) {{
                html += '<div style="margin-bottom: 20px;">';
                html += '<h3 style="color: #10b981; margin: 0 0 10px 0; font-size: 18px;">📊 Macro Time Intervals</h3>';
                macroIntervals.forEach(interval => {{
                    html += createIntervalCard(interval);
                }});
                html += '</div>';
            }}
            
            if (microIntervals.length > 0) {{
                html += '<div>';
                html += '<h3 style="color: #3b82f6; margin: 0 0 10px 0; font-size: 18px;">🏢 Micro Time Intervals</h3>';
                microIntervals.forEach(interval => {{
                    html += createIntervalCard(interval);
                }});
                html += '</div>';
            }}
            
            content.innerHTML = html;
        }}
        
        function createIntervalCard(interval) {{
            const duration = interval.duration_days || 0;
            const startDate = new Date(interval.start_date).toLocaleDateString();
            const endDate = new Date(interval.end_date).toLocaleDateString();
            
            return `
                <div style="
                    background: linear-gradient(135deg, #2d3748 0%, #4a5568 100%);
                    border: 1px solid #4a5568;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 10px 0;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="color: #ffffff; font-weight: 600; font-size: 16px;">
                            ${{interval.time_interval}}
                        </span>
                        <span style="
                            background: ${{interval.scope === 'macro' ? '#10b981' : '#3b82f6'}};
                            color: white;
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 12px;
                            font-weight: 500;
                        ">
                            ${{interval.scope.toUpperCase()}}
                        </span>
                    </div>
                    <div style="color: #a0aec0; font-size: 14px;">
                        <div>📅 Start: ${{startDate}}</div>
                        <div>📅 End: ${{endDate}}</div>
                        <div>⏱️ Duration: ${{duration}} days</div>
                    </div>
                </div>
            `;
        }}
        
        renderTreemap(macroData);
    </script>
</body>
</html>
"""
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_file = f.name
    
    # Open in browser
    webbrowser.open(f'file://{temp_file}')
    
    print("Q&Q.AI treemap opened in browser!")
    print("Fixed: Red/Green colors with 70% opacity (increased transparency)")
    
    # Clean up temp file after a delay
    def cleanup():
        time.sleep(2)
        try:
            os.unlink(temp_file)
        except:
            pass
    
    threading.Thread(target=cleanup, daemon=True).start()
    
    return html_content

# =============================================================================
# MAIN STORAGE AGENT CLASS
# =============================================================================
    
class QuantImpactStorageAgent:
    """
    Quant Impact Storage Agent - EXACT COPY from Dynamic_Alpha.ipynb
    
    Implements the complete analyst pipeline from Dynamic_Alpha.ipynb:
    1. Get ticker → Get sector → Get double beta
    2. Get factors → Get date ranges → Beta filter impact
    3. Generate impact metrics → Store in database
    """
    
    def __init__(self, shared_clients=None, user_id: str = "default_user"):
        """
        Initialize the Quant Impact Storage Agent
        
        Args:
            shared_clients: Shared clients for LLM and Redis access
            user_id: User ID for database storage
        """
        self.shared_clients = shared_clients
        self.user_id = user_id
        self.fmp_api_key = FMP_API_KEY
        
        # Redis client for reading stock trend data and storing datasets
        self.redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            username=REDIS_USERNAME,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
    
    def store_8_datasets_as_csv(
        self,
        ticker: str,
        risk_share_index: Dict[str, float],
        macro_volatility_df: pd.DataFrame,
        micro_volatility_df: pd.DataFrame,
        impact_metrics_df: pd.DataFrame,
        macro_total_impact_df: pd.DataFrame,
        micro_total_impact_df: pd.DataFrame,
        Factor_Risk_Reward: pd.DataFrame,
        factor_time_df: pd.DataFrame,
        meta_info: Dict[str, Any]
    ) -> bool:
        """
        Store the 7 datasets as CSV in Redis with metadata
        
        Args:
            ticker: Stock ticker symbol
            risk_share_index: Risk share dictionary
            macro_volatility_df: Macro volatility DataFrame
            micro_volatility_df: Micro volatility DataFrame
            impact_metrics_df: Risk-reward DataFrame
            macro_total_impact_df: Macro total impact DataFrame
            micro_total_impact_df: Micro total impact DataFrame
            meta_info: Metadata dictionary
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            ticker = ticker.upper()
            base_key = f"Quant_Impact_INFOS:{ticker}"
            
            # Store each dataset as CSV
            datasets = {
                f"{base_key}:RISK_SHARE": json.dumps(risk_share_index),
                f"{base_key}:MACRO_VOLATILITY": macro_volatility_df.to_csv(index=False),
                f"{base_key}:MICRO_VOLATILITY": micro_volatility_df.to_csv(index=False),
                f"{base_key}:IMPACT_METRICS": impact_metrics_df.to_csv(index=False),
                f"{base_key}:MACRO_TOTAL_IMPACT": macro_total_impact_df.to_csv(index=False),
                f"{base_key}:MICRO_TOTAL_IMPACT": micro_total_impact_df.to_csv(index=False),
                f"{base_key}:FACTOR_IMPACT_METRICS": Factor_Risk_Reward.to_csv(index=False),
                f"{base_key}:FACTOR_TIME_DF": factor_time_df.to_csv(index=False),
                f"{base_key}:META_INFO": json.dumps(meta_info)
            }
            
            # Store all datasets with 30-day expiration
            pipeline = self.redis_client.pipeline()
            for key, csv_data in datasets.items():
                pipeline.setex(key, 30 * 24 * 60 * 60, csv_data)
            
            # Execute all operations
            pipeline.execute()
            
            print(f"✅ Stored 8 datasets as CSV for {ticker}")
            print(f"   Keys stored:")
            for key in datasets.keys():
                print(f"     - {key}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to store CSV datasets for {ticker}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def retrieve_8_datasets_from_csv(
        self,
        ticker: str
    ) -> Dict[str, Any]:
        """
        Retrieve the 8 datasets from CSV storage
        
        Args:
            ticker: Stock ticker symbol
        
        Returns:
            dict: Dictionary containing all 8 datasets
        """
        try:
            ticker = ticker.upper()
            base_key = f"Quant_Impact_INFOS:{ticker}"
            
            results = {}
            
            # Retrieve risk share index
            risk_share_data = self.redis_client.get(f"{base_key}:RISK_SHARE")
            if risk_share_data:
                results['risk_share_index'] = json.loads(risk_share_data)
            
            # Retrieve DataFrames
            dataframe_keys = [
                ('macro_volatility_df', f"{base_key}:MACRO_VOLATILITY"),
                ('micro_volatility_df', f"{base_key}:MICRO_VOLATILITY"),
                ('impact_metrics_df', f"{base_key}:IMPACT_METRICS"),
                ('macro_total_impact_df', f"{base_key}:MACRO_TOTAL_IMPACT"),
                ('micro_total_impact_df', f"{base_key}:MICRO_TOTAL_IMPACT"),
                ('Factor_Risk_Reward', f"{base_key}:FACTOR_IMPACT_METRICS"),
                ('factor_time_df', f"{base_key}:FACTOR_TIME_DF")
            ]
            
            for df_name, redis_key in dataframe_keys:
                csv_data = self.redis_client.get(redis_key)
                if csv_data:
                    results[df_name] = pd.read_csv(StringIO(csv_data))
            
            # Retrieve metadata
            meta_data = self.redis_client.get(f"{base_key}:META_INFO")
            if meta_data:
                results['meta_info'] = json.loads(meta_data)
            
            print(f"✅ Retrieved 8 CSV datasets for {ticker}")
            return results
            
        except Exception as e:
            print(f"❌ Failed to retrieve CSV datasets for {ticker}: {e}")
            return {}
    
    async def process_quant_impact_analysis(
        self,
        ticker: str,
        language: str = "English",
        market_ticker: str = "SPY",
        risk_free_rate: float = 0.025,
        period_days: int = 252
    ) -> Dict[str, Any]:
        """
        Process complete quant impact analysis pipeline
        
        Args:
            ticker: Stock ticker symbol
            language: Language for output
            market_ticker: Market benchmark ticker
            risk_free_rate: Risk-free rate
            period_days: Number of trading days
            
        Returns:
            dict: Complete analysis results including impact metrics
        """
        print(f"🚀 Starting Quant Impact Analysis for {ticker}")
        
        try:
            # =============================================================================
            # WARM-UP POOL: Use update_pool to warm up required agents
            # =============================================================================
            print(f"\n🔥 Warming up Market Expectation and Sector Analyst for {ticker}...")
            
            # Import update_pool
            from update_pool import update_pool
            
            # Warm up required agents
            warm_up_result = await update_pool(ticker, ["Market_Expectation_Agent", "Sector_Analyst_Agent"])
            
            if warm_up_result["status"] == "completed":
                print(f"✅ Warmed up {warm_up_result['updated_agents']} agents")
            elif warm_up_result["status"] == "all_fresh":
                print("✅ All agents already have fresh data")
            elif warm_up_result["status"] == "error":
                print(f"⚠️ Warm-up warning: {warm_up_result['error']}")
                print("Continuing with analysis...")
            
            # =============================================================================
            # MAIN PIPELINE STARTS HERE - EXACT COPY FROM DYNAMIC_ALPHA.IPYNB
            # =============================================================================
            
            # Step 1: Get factors (16 macro + 16 micro)
            step1_result = step1_get_factors(ticker, language)
            
            # Step 2: Get date ranges
            step2_result, factor_time_df = step2_get_date_ranges(ticker, step1_result, language)
            
            # Step 2.5: Calculate alpha using CAPM regression
            print("\n🧮 Step 2.5: Calculating alpha using CAPM regression...")
            
            # Calculate alpha using simple CAPM regression
            from scipy import stats
            import numpy as np
            import requests
            
            FMP_API_KEY = "9dfbbfa29d93f4793f246e8fb5ca5e74"
            
            def get_stock_prices_fmp(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
                url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"
                params = {'from': start_date, 'to': end_date, 'apikey': FMP_API_KEY}
                
                try:
                    response = requests.get(url, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    if 'historical' in data:
                        df = pd.DataFrame(data['historical'])
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.sort_values('date').reset_index(drop=True)
                        return df[['date', 'close']]
                    else:
                        return pd.DataFrame()
                except Exception as e:
                    print(f"❌ Error fetching data: {e}")
                    return pd.DataFrame()
            
            # Get stock and market data for alpha calculation
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=252)).strftime('%Y-%m-%d')  # 1 year
            
            stock_df = get_stock_prices_fmp(ticker, start_date, end_date)
            market_df = get_stock_prices_fmp("SPY", start_date, end_date)
            
            alpha_daily = 0.0  # Default alpha
            market_beta = 1.2777  # Default beta
            
            if not stock_df.empty and not market_df.empty:
                merged_df = stock_df.merge(market_df, on='date', suffixes=('_stock', '_market'))
                merged_df = merged_df.sort_values('date').reset_index(drop=True)
                
                merged_df['return_stock'] = merged_df['close_stock'].pct_change()
                merged_df['return_market'] = merged_df['close_market'].pct_change()
                merged_df = merged_df.dropna()
                
                if len(merged_df) >= 10:
                    risk_free_daily = risk_free_rate / 365
                    merged_df['excess_return_stock'] = merged_df['return_stock'] - risk_free_daily
                    merged_df['excess_return_market'] = merged_df['return_market'] - risk_free_daily
                    
                    # CAPM regression: R_stock - Rf = α + β * (R_market - Rf)
                    slope, intercept, _, _, _ = stats.linregress(
                        merged_df['excess_return_market'], merged_df['excess_return_stock']
                    )
                    
                    alpha_daily = intercept  # Daily alpha
                    market_beta = slope
                    
                    print(f"   ✅ Alpha (daily): {alpha_daily:.6f} ({alpha_daily*100:.4f}%)")
                    print(f"   ✅ Market Beta: {market_beta:.4f}")
                else:
                    print(f"   ⚠️ Insufficient data for alpha calculation, using defaults")
            else:
                print(f"   ⚠️ Could not fetch data for alpha calculation, using defaults")
            
            # Step 3: Beta filtering - REAL IMPLEMENTATION from Dynamic_Alpha.ipynb
            step3_result = step3_beta_filtering(
                ticker=ticker,
                step2_result=step2_result,
                read_information=step1_result["read_information"],
                market_beta=market_beta,
                alpha_daily=alpha_daily,
                market_ticker=market_ticker,
                risk_free_rate=risk_free_rate
            )
            
            if step3_result.get("error"):
                return {
                    "status": "error",
                    "ticker": ticker,
                    "error": step3_result["error"]
                }
            
            # Step 4: Impact metrics - REAL IMPLEMENTATION from Dynamic_Alpha.ipynb
            step4_result = step4_impact_metrics(step3_result)
            
            if step4_result.get("error"):
                return {
                    "status": "error", 
                    "ticker": ticker,
                    "error": step4_result["error"]
                }
            
            summary_df = step4_result["summary_df"]
            
            # Step 5: Generate Factor_Risk_Reward (7th dataset)
            print(f"\n🎯 Generating Factor_Risk_Reward dataset...")
            schema_result = generate_impact_summary_schema(summary_df, language=language)
            Factor_Risk_Reward = convert_schema_to_compound_datasets(schema_result, summary_df)
            
            # Step 6: Generate the 6 risk metrics using the real summary_df
            risk_share_index, macro_volatility_df, micro_volatility_df, impact_metrics_df, macro_total_impact_df, micro_total_impact_df = quant_impact_risk_analysis(summary_df)
            
            # Prepare metadata
            meta_info = {
                "ticker": ticker,
                "status": "success",
                "factors_generated": len(step1_result["macro_factors"]) + len(step1_result["micro_factors"]),
                "macro_factors": len(step1_result["macro_factors"]),
                "micro_factors": len(step1_result["micro_factors"]),
                "summary_df_rows": len(summary_df),
                "Factor_Risk_Reward_rows": len(Factor_Risk_Reward),
                "retrieved_date": datetime.now().isoformat(),
                "data_source": "quant_impact_analysis"
            }
            
            # Store the 8 datasets as CSV in Redis
            print(f"\n💾 Storing 8 datasets as CSV for {ticker}...")
            storage_success = self.store_8_datasets_as_csv(
                ticker,
                risk_share_index,
                macro_volatility_df,
                micro_volatility_df,
                impact_metrics_df,
                macro_total_impact_df,
                micro_total_impact_df,
                Factor_Risk_Reward,
                factor_time_df,
                meta_info
            )
            
            if storage_success:
                print(f"✅ Successfully stored all datasets for {ticker}")
            else:
                print(f"⚠️ Storage warning for {ticker} - datasets generated but storage failed")
            
            return {
                "status": "success",
                "ticker": ticker,
                "step1_result": step1_result,
                "step2_result": step2_result,
                "step3_result": step3_result,
                "step4_result": step4_result,
                "summary_df": summary_df,
                "macro_factors": step1_result["macro_factors"],
                "micro_factors": step1_result["micro_factors"],
                "risk_share_index": risk_share_index,
                "macro_volatility_df": macro_volatility_df,
                "micro_volatility_df": micro_volatility_df,
                "impact_metrics_df": impact_metrics_df,
                "macro_total_impact_df": macro_total_impact_df,
                "micro_total_impact_df": micro_total_impact_df,
                "Factor_Risk_Reward": Factor_Risk_Reward,
                "factor_time_df": factor_time_df,
                "meta_info": meta_info,
                "date_ranges": {
                    "macro": step2_result.macro,
                    "micro": step2_result.micro
                }
            }
            
        except Exception as e:
            print(f"❌ Error in quant impact analysis for {ticker}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "ticker": ticker
            }

# =============================================================================
# USAGE FUNCTIONS
# =============================================================================

async def get_quant_impact_data(ticker: str, language: str = "English") -> Tuple[Dict[str, float], pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Get quant impact data for a ticker - EXACT COPY from Dynamic_Alpha.ipynb
    
    Args:
        ticker: Stock ticker symbol
        language: Language for output (default: "English")
        
    Returns:
        Tuple of (risk_share_index, macro_volatility_df, micro_volatility_df, impact_metrics_df, macro_total_impact_df, micro_total_impact_df, meta_info)
    """
    try:
        # Create storage agent
        storage_agent = QuantImpactStorageAgent()
        
        # Process analysis (warm-up is now built into the storage agent)
        result = await storage_agent.process_quant_impact_analysis(ticker, language)
        
        if result["status"] != "success":
            raise Exception(f"Analysis failed: {result.get('error')}")
        
        # Extract the 6 metrics from the result
        if result["status"] == "success":
            risk_share_index = result["risk_share_index"]
            macro_volatility_df = result["macro_volatility_df"]
            micro_volatility_df = result["micro_volatility_df"]
            impact_metrics_df = result["impact_metrics_df"]
            macro_total_impact_df = result["macro_total_impact_df"]
            micro_total_impact_df = result["micro_total_impact_df"]
        else:
            # Fallback to mock data if analysis failed
            risk_share_index = {"macro_risk_share": 60.0, "micro_risk_share": 40.0}
            macro_volatility_df = pd.DataFrame()
            micro_volatility_df = pd.DataFrame()
            impact_metrics_df = pd.DataFrame()
            macro_total_impact_df = pd.DataFrame()
            micro_total_impact_df = pd.DataFrame()
        
        meta_info = {
            "ticker": ticker,
            "status": "success",
            "factors_generated": len(result.get("macro_factors", [])) + len(result.get("micro_factors", [])),
            "macro_factors": len(result.get("macro_factors", [])),
            "micro_factors": len(result.get("micro_factors", [])),
            "summary_df_rows": len(result.get("summary_df", pd.DataFrame())),
            "retrieved_date": datetime.now().isoformat(),
            "data_source": "quant_impact_analysis"
        }
        
        # Store the 8 datasets as CSV in Redis
        print(f"\n💾 Storing 8 datasets as CSV for {ticker}...")
        storage_success = self.store_8_datasets_as_csv(
            ticker,
            risk_share_index,
            macro_volatility_df,
            micro_volatility_df,
            impact_metrics_df,
            macro_total_impact_df,
            micro_total_impact_df,
            result.get("Factor_Risk_Reward", pd.DataFrame()),
            result.get("factor_time_df", pd.DataFrame()),
            meta_info
        )
        
        if storage_success:
            print(f"✅ Successfully stored all datasets for {ticker}")
        else:
            print(f"⚠️ Storage warning for {ticker} - datasets generated but storage failed")
        
        return risk_share_index, macro_volatility_df, micro_volatility_df, impact_metrics_df, macro_total_impact_df, micro_total_impact_df, meta_info
        
    except Exception as e:
        print(f"❌ Error getting quant impact data for {ticker}: {e}")
        
        # Return error response
        error_response = {"error": str(e)}
        return error_response, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), error_response
