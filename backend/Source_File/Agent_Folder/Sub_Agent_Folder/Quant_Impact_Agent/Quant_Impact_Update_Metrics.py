"""
Quant Impact Update Metrics Generator
=====================================
This module computes impact metrics for a specific time period (from previous_update_time to today).
Uses the exact same pipeline as Quant_Impact_Storage_Agent but filters data by time.

USAGE:
------
from Quant_Impact_Update_Metrics import generate_update_metrics

# Generate metrics from a specific date to today
impact_df, impact_metrics_df = generate_update_metrics(
    ticker="AAPL",
    previous_update_time="2025-01-01"
)

OUTPUT:
-------
1. impact_df: DataFrame with impact metrics including all calculated columns
2. impact_metrics_df: DataFrame with final impact metrics analysis
"""

import sys
import os
import redis
import json
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple


def calculate_missing_metrics(df):
    """
    Calculate missing trend_weight_score, score_weighted_mean, score_weighted_variance, and risk_reward_ratio
    """
    # Make a copy to avoid modifying original
    df = df.copy()
    
    # Calculate total trends across all factors
    total_trends = df['trend_count'].sum()
    
    # Calculate trend_weight_score (trend_count / total_trends)
    df['trend_weight_score'] = df['trend_count'] / total_trends
    
    # Calculate score_weighted_mean and score_weighted_variance
    df['score_weighted_mean'] = df['trend_weight_score'] * df['weighted_mean']
    df['score_weighted_variance'] = df['trend_weight_score'] * df['weighted_variance']
    
    # Calculate risk_reward_ratio (absolute mean / sqrt variance)
    df['risk_reward_ratio'] = np.abs(df['weighted_mean']) / np.sqrt(df['weighted_variance'])
    
    # Handle division by zero and infinite values
    df['risk_reward_ratio'] = df['risk_reward_ratio'].replace([np.inf, -np.inf], 0)
    df['risk_reward_ratio'] = df['risk_reward_ratio'].fillna(0)
    
    return df


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

# Import required modules from the project
from LLM_Call_Agent import LLMCallAgent

# Redis Configuration - Using centralized database_connection module
# Import centralized config
try:
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import (
        STOCK_TREND_REDIS_HOST, STOCK_TREND_REDIS_PORT, 
        STOCK_TREND_REDIS_USERNAME, STOCK_TREND_REDIS_PASSWORD
    )
except ImportError:
    raise ImportError("config.py is required. Please ensure it exists in the backend directory.")

COLLECTION_NAME = "Stock_Trend_INFOS"

# Import all necessary functions from Dynamic Alpha pipeline
# We'll embed them here to ensure consistency

def read_stock_trend_data_filtered(ticker: str, previous_update_time: str) -> Dict[str, Any]:
    """
    Read stock trend data from Redis and filter by date
    
    Args:
        ticker: Stock ticker
        previous_update_time: Start date in 'YYYY-MM-DD' format
        
    Returns:
        Filtered historical trends dictionary
    """
    redis_key = f"{COLLECTION_NAME}:{ticker.upper()}_trends"
    
    # Use database_connection module
    import sys
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from Source_File.database_connection import RedisDatabaseStorage as CentralizedStorage
    db_storage = CentralizedStorage(db_type="stock_trend", shared_clients=None)
    client = db_storage.redis_client
    
    data = client.get(redis_key)
    if data is None:
        print(f"❌ No stock trend data found for {ticker}")
        return None
    
    all_trends = json.loads(data)
    
    # Filter trends by date
    filtered_trends = {}
    cutoff_date = datetime.strptime(previous_update_time, '%Y-%m-%d')
    
    # Check BOTH current_trends AND historical_trends
    all_trend_sources = [
        ('current_trends', all_trends.get('current_trends', {})),
        ('historical_trends', all_trends.get('historical_trends', {}))
    ]
    
    for source_name, trends_dict in all_trend_sources:
        for trend_key, trend_data in trends_dict.items():
            # Get the END date of this trend (not start date)
            time_data = trend_data.get('time', {})
            end_date_str = time_data.get('end', '')
            
            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                    # Include trends that END on or after the cutoff date
                    if end_date >= cutoff_date:
                        # Add source prefix to avoid key conflicts
                        source_key = f"{source_name}_{trend_key}"
                        filtered_trends[source_key] = trend_data
                        print(f"   ✅ Included {source_name}:{trend_key} (ends {end_date_str})")
                except Exception as e:
                    print(f"   ⚠️ Error parsing date for {source_name}:{trend_key}: {e}")
                    continue
    
    print(f"📅 Filtered trends: {len(filtered_trends)} periods from {previous_update_time} onwards")
    
    return {'historical_trends': filtered_trends}


# Import step functions from the notebook (we'll replicate them here)
# These are exact copies from Dynamic_Alpha.ipynb

def analyze_trend_complexity(read_information: Dict[str, Any]) -> Dict[str, Any]:
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

def count_trends_in_period(read_information: Dict[str, Any]) -> int:
    """
    Count the number of trends in the filtered period (legacy function)
    
    Args:
        read_information: Stock trend data with historical_trends
        
    Returns:
        Number of trends
    """
    complexity_analysis = analyze_trend_complexity(read_information)
    return complexity_analysis["trend_count"]


def create_dynamic_factor_set(num_factors: int):
    """
    Dynamically create a FactorSet Pydantic model with N factors
    
    Args:
        num_factors: Number of factors to generate
        
    Returns:
        Pydantic BaseModel class with dynamic fields
    """
    from langchain_core.pydantic_v1 import BaseModel, Field, create_model
    
    # Create fields dictionary for dynamic model
    fields = {}
    for i in range(1, num_factors + 1):
        fields[f'factor_{i}'] = (str, Field(description=f"Keyword for factor {i}"))
    
    # Create dynamic Pydantic model
    DynamicFactorSet = create_model('DynamicFactorSet', **fields)
    
    return DynamicFactorSet


def step1_get_factors_dynamic(ticker: str, read_information: Dict[str, Any], language: str = "English"):
    """Step 1: Get micro + macro factors (DYNAMIC based on trend count)"""
    from typing import Any, Dict, Union, List
    from langchain.output_parsers import PydanticOutputParser
    from langchain_core.pydantic_v1 import BaseModel, Field, create_model
    import re
    
    # FIXED FACTOR COUNT: 5 factors per scope (macro + micro = 10 total)
    num_factors = 5
    
    print(f"   🔢 Generating {num_factors} factors per scope (FIXED MODE)")
    
    # Create dynamic FactorSet model
    fields = {}
    for i in range(1, num_factors + 1):
        fields[f'factor_{i}'] = (str, Field(description=f"Keyword for factor {i}"))
    
    DynamicFactorSet = create_model('DynamicFactorSet', **fields)
    
    class FactorPayload(BaseModel):
        ticker: str = Field(description="Ticker symbol in uppercase")
        macro: DynamicFactorSet = Field(description="Macro-level catalyst keywords")
        micro: DynamicFactorSet = Field(description="Company-level catalyst keywords")
    
    DynamicFactorSet.model_json_schema = classmethod(lambda cls: cls.schema())
    FactorPayload.model_json_schema = classmethod(lambda cls: cls.schema())
    
    parser = PydanticOutputParser(pydantic_object=FactorPayload)
    
    def get_system_instructions(language: str = "English", num_factors: int = 5) -> str:
        base_instructions = f"""
You are a senior equity strategist. Extract the most impactful market drivers from stock intelligence.

**SMART FACTOR DETECTION:**
- **REAL DRIVER FOCUS**: If earnings miss but guidance raised → price up → factor = "Guidance Raised Better Than Expected" (NOT "Earnings Miss")
- **COMPREHENSIVE NAMING**: If no single driver, use full context: "Revenue Miss But Strong Guidance"
- **MARKET IMPACT**: Focus on what actually moved the stock price, not surface headlines
- **CONTEXT AWARENESS**: Consider the full story - what was the net market reaction?

**RULES:**
- Generate {num_factors} high-quality factors per scope (macro + micro = {num_factors*2} total)
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
    
    def build_factor_prompt(ticker: str, read_information: Union[str, Dict[str, Any]], language: str = "English") -> str:
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
    
    def _extract_json_payload(raw: str) -> str:
        cleaned = raw.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1:
            cleaned = cleaned[start : end + 1]
        return cleaned
    
    prompt = build_factor_prompt(ticker, read_information, language)
    system_instructions = get_system_instructions(language, num_factors)
    
    llm_agent = LLMCallAgent(default_provider="deepseek", default_model="deepseek-chat")
    
    # Adjust max_tokens based on number of factors
    max_tokens = min(700 + (num_factors * 20), 2000)
    
    raw_response = llm_agent.call_deepseek(
        prompt=prompt,
        system_message=system_instructions,
        model="deepseek-chat",
        max_tokens=max_tokens,
        temperature=0.1,
    )
    
    if not raw_response:
        raise ValueError("Empty response from LLM")
    
    cleaned = _extract_json_payload(raw_response)
    factor_result = parser.parse(cleaned)
    
    # Extract factors dynamically
    macro_factors = [getattr(factor_result.macro, f'factor_{i}') for i in range(1, num_factors + 1)]
    micro_factors = [getattr(factor_result.micro, f'factor_{i}') for i in range(1, num_factors + 1)]
    
    print(f"✅ Generated {len(macro_factors)} macro factors")
    print(f"✅ Generated {len(micro_factors)} micro factors")
    
    return {
        "factor_payload": factor_result,
        "macro_factors": macro_factors,
        "micro_factors": micro_factors,
        "read_information": read_information
    }


def step2_get_date_ranges(ticker: str, factor_result: Dict[str, Any], language: str = "English"):
    """Step 2: Map factors to date ranges (same as notebook)"""
    from langchain.output_parsers import PydanticOutputParser
    from langchain_core.pydantic_v1 import BaseModel, Field
    from typing import Dict, List
    
    class DateRangePayload(BaseModel):
        ticker: str = Field(description="Ticker symbol in uppercase")
        macro: Dict[str, List[List[str]]] = Field(description="Macro factor to date ranges mapping")
        micro: Dict[str, List[List[str]]] = Field(description="Micro factor to date ranges mapping")
    
    DateRangePayload.model_json_schema = classmethod(lambda cls: cls.schema())
    date_range_parser = PydanticOutputParser(pydantic_object=DateRangePayload)
    
    def get_date_range_system_instructions(language: str = "English") -> str:
        base_instructions = f"""
You are a meticulous financial analyst. Map each factor to specific date ranges when those events occurred.

Rules:
- For each factor, provide actual date ranges: ["YYYY-MM-DD", "YYYY-MM-DD"]
- A factor can have multiple date ranges
- Only use dates from the historical data
- If no dates available, provide empty list []
- IMPORTANT: Include macro and micro sections (NO sector)
- Keep response concise

{date_range_parser.get_format_instructions()}
""".strip()
        
        if language.lower() != "english":
            language_instruction = f"\n\nIMPORTANT: Output ALL content in {language} language only."
            return base_instructions + language_instruction
        else:
            return base_instructions
    
    def build_date_range_prompt(ticker: str, factor_payload, read_information: Dict[str, Any], language: str = "English") -> str:
        factor_summary = json.dumps(factor_payload.dict(), indent=2, ensure_ascii=False)
        
        historical_trends = read_information.get("historical_trends", {})
        trend_summary = {}
        
        for trend_key, trend_data in historical_trends.items():
            trend_summary[trend_key] = {
                "summary": trend_data.get("summary", ""),
                "time_period": trend_data.get("time", {}),
                "macro_reason": trend_data.get("macro_reason", ""),
                "micro_reason": trend_data.get("micro_reason", "")
            }
        
        trend_context = json.dumps(trend_summary, indent=2, ensure_ascii=False)
        
        base_prompt = (
            f"Ticker: {ticker}\n\n"
            f"Factor keywords:\n{factor_summary}\n\n"
            "Historical trend context:\n"
            f"{trend_context}\n\n"
            "Task: Map each factor to date ranges. "
            "Format: [\"start_date\", \"end_date\"]. "
            "Include macro and micro sections."
        )
        
        if language.lower() != "english":
            language_instruction = f"\n\nIMPORTANT: Output ALL content in {language} language only."
            return base_prompt + language_instruction
        else:
            return base_prompt
    
    factor_payload = factor_result["factor_payload"]
    read_information = factor_result["read_information"]
    
    prompt = build_date_range_prompt(ticker, factor_payload, read_information, language)
    system_instructions = get_date_range_system_instructions(language)
    
    llm_agent = LLMCallAgent(default_provider="deepseek", default_model="deepseek-chat")
    
    raw_response = llm_agent.call_deepseek(
        prompt=prompt,
        system_message=system_instructions,
        model="deepseek-chat",
        max_tokens=4000,
        temperature=0.0,
    )
    
    if not raw_response:
        raise ValueError("Empty response from LLM")
    
    cleaned = raw_response.strip().strip("`")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    
    if not cleaned.endswith("}"):
        print(f"⚠️ Response may be truncated. Last 100 chars: {cleaned[-100:]}")
        if '"micro"' not in cleaned:
            cleaned += ', "micro": {}}'
        elif '"macro"' not in cleaned:
            cleaned += ', "macro": {}}'
        else:
            # Advanced JSON repair
            open_braces = cleaned.count('{')
            close_braces = cleaned.count('}')
            missing_braces = open_braces - close_braces
            cleaned += '}' * missing_braces
            print(f"🔧 Added {missing_braces} missing closing braces")
    
    # COMPLETE JSON REPAIR - NO FALLBACKS
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
    except Exception as exc:
        print(f"❌ Raw response: {raw_response}")
        print(f"❌ Cleaned response: {cleaned}")
        raise ValueError(f"Date range mapping response could not be parsed:\n{raw_response}") from exc
    
    print(f"✅ Mapped macro factors to date ranges")
    print(f"✅ Mapped micro factors to date ranges")
    
    # CREATE DETAILED FACTOR-TIME INTERVAL MAPPING DF
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
    
    if not factor_time_df.empty:
        print(f"\n📊 FACTOR-TIME INTERVAL MAPPING:")
        print(f"   Total factor-time combinations: {len(factor_time_df)}")
        print(f"   Macro factors: {len(factor_time_df[factor_time_df['scope'] == 'macro'])}")
        print(f"   Micro factors: {len(factor_time_df[factor_time_df['scope'] == 'micro'])}")
        
        # Show sample
        print(f"\n📋 Sample factor-time mappings:")
        sample_df = factor_time_df.head(10)
        for _, row in sample_df.iterrows():
            print(f"   {row['factor_name']} ({row['scope']}): {row['time_interval']} ({row['duration_days']} days)")
    else:
        print("⚠️ No factor-time intervals found")
    
    # Store the DataFrame separately (can't add to Pydantic model)
    # Return both the date_range_result and the factor_time_df
    return date_range_result, factor_time_df


def step3_beta_filtering(ticker: str, step2_result, read_information: Dict[str, Any],
                        market_beta: float, alpha_daily: float = 0.0, market_ticker: str = "SPY", 
                        risk_free_rate: float = 0.025) -> Dict[str, Any]:
    """Step 3: Beta filtering with volatility normalization (same as notebook)"""
    import requests
    from datetime import datetime
    
    # Import centralized config
    import sys
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import FMP_API_KEY, FMP_API_V3_URL
    
    def get_stock_prices_fmp(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        url = f"{FMP_API_V3_URL}/historical-price-full/{ticker}"
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
    
    def calculate_annual_volatility(ticker: str, start_date: str, end_date: str) -> float:
        stock_df = get_stock_prices_fmp(ticker, start_date, end_date)
        
        if stock_df.empty:
            return 0.0
        
        stock_df['daily_return'] = stock_df['close'].pct_change()
        stock_df = stock_df.dropna()
        
        if len(stock_df) < 10:
            return 0.0
        
        daily_volatility = stock_df['daily_return'].std()
        annual_volatility = daily_volatility * np.sqrt(252)
        
        print(f"   📊 Annual Volatility: {annual_volatility:.4f} ({annual_volatility*100:.2f}%)")
        
        return annual_volatility
    
    def map_date_range_to_trend_data(start_date: str, end_date: str, historical_trends: Dict[str, Any]) -> Dict[str, float]:
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
        
        period_key = f"{start_date_clean} to {end_date_clean}"
        
        for trend_key, trend_data in historical_trends.items():
            trend_period = trend_data.get('current', '')
            
            if period_key == trend_period:
                stock_return = trend_data.get('day average_return', 0.0)
                spy_return = trend_data.get('SPY_return_rate', 0.0)
                
                if stock_return is None:
                    stock_return = 0.0
                if spy_return is None:
                    spy_return = 0.0
                
                return {
                    "stock_daily_return": stock_return,
                    "spy_daily_return": spy_return,
                    "trend_key": trend_key
                }
        
        # Debug: show available periods
        available_periods = [trend_data.get('current', '') for trend_data in historical_trends.values()]
        print(f"⚠️ No match for {period_key}. Available: {available_periods[:3]}...")
        
        return {
            "stock_daily_return": 0.0,
            "spy_daily_return": 0.0,
            "trend_key": "no_match"
        }
    
    print(f"🔍 Step 3: Beta filtering for {ticker}")
    print(f"   Using market beta: {market_beta:.4f}")
    print(f"   Using alpha (daily): {alpha_daily:.6f} ({alpha_daily*100:.4f}%)")
    
    historical_trends = read_information.get('historical_trends', {})
    if not historical_trends:
        return {"error": "No historical trends found"}
    
    macro_date_ranges = step2_result.macro
    micro_date_ranges = step2_result.micro
    
    all_dates = []
    for factor_ranges in macro_date_ranges.values():
        all_dates.extend(factor_ranges)
    for factor_ranges in micro_date_ranges.values():
        all_dates.extend(factor_ranges)
    
    if not all_dates:
        return {"error": "No date ranges found"}
    
    min_date = min([min(date_range) for date_range in all_dates if date_range])
    max_date = max([max(date_range) for date_range in all_dates if date_range])
    
    print(f"   Processing date ranges from {min_date} to {max_date}")
    
    annual_volatility = calculate_annual_volatility(ticker, min_date, max_date)
    volatility_factor = annual_volatility / 15.874
    
    print(f"   🔧 Volatility Factor: {volatility_factor:.4f}")
    
    risk_free_rate_period = 0.025
    
    # Process macro factors
    macro_results = {}
    print(f"\n📊 Processing {len(macro_date_ranges)} macro factors...")
    
    for factor_name, date_ranges in macro_date_ranges.items():
        if not date_ranges:
            continue
        
        factor_impacts = []
        
        for start_date, end_date in date_ranges:
            trend_data = map_date_range_to_trend_data(start_date, end_date, historical_trends)
            stock_daily_return = trend_data["stock_daily_return"]
            spy_daily_return = trend_data["spy_daily_return"]
            
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
            risk_free_daily = risk_free_rate_period / 365
            
            real_macro_impact = market_beta * spy_daily_return
            real_micro_impact = stock_daily_return - real_macro_impact
            
            if real_micro_impact > 0:
                normalized_micro_impact = real_micro_impact - volatility_factor
            else:
                normalized_micro_impact = real_micro_impact + volatility_factor
            
            factor_impacts.append({
                "period": f"{start_date} to {end_date}",
                "days": days,
                "stock_daily_return": stock_daily_return,
                "spy_daily_return": spy_daily_return,
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
    print(f"\n📊 Processing {len(micro_date_ranges)} micro factors...")
    
    for factor_name, date_ranges in micro_date_ranges.items():
        if not date_ranges:
            continue
        
        factor_impacts = []
        
        for start_date, end_date in date_ranges:
            trend_data = map_date_range_to_trend_data(start_date, end_date, historical_trends)
            stock_daily_return = trend_data["stock_daily_return"]
            spy_daily_return = trend_data["spy_daily_return"]
            
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
            risk_free_daily = risk_free_rate_period / 365
            
            real_macro_impact = market_beta * spy_daily_return
            real_micro_impact = stock_daily_return - real_macro_impact
            
            if real_micro_impact > 0:
                normalized_micro_impact = real_micro_impact - volatility_factor
            else:
                normalized_micro_impact = real_micro_impact + volatility_factor
            
            factor_impacts.append({
                "period": f"{start_date} to {end_date}",
                "days": days,
                "stock_daily_return": stock_daily_return,
                "spy_daily_return": spy_daily_return,
                "risk_free_daily": risk_free_daily,
                "real_macro_impact": real_macro_impact,
                "real_micro_impact": real_micro_impact,
                "normalized_micro_impact": normalized_micro_impact,
                "volatility_factor": volatility_factor,
                "trend_key": trend_data["trend_key"]
            })
        
        micro_results[factor_name] = factor_impacts
        print(f"   ✅ {factor_name}: {len(factor_impacts)} periods")
    
    # Calculate weighted averages
    def calculate_weighted_averages(factor_results):
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


def step4_impact_metrics(step3_result):
    """Step 4: Generate impact metrics (same as notebook)"""
    print(f"🔍 Step 4: Generating impact metrics")
    
    def aggregate_by_factor(factor_results, scope):
        aggregated = {}
        
        for factor_name, impacts in factor_results.items():
            if not impacts:
                continue
            
            # Extract normalized micro impacts
            normalized_impacts = [impact['normalized_micro_impact'] for impact in impacts]
            durations = [impact['days'] for impact in impacts]
            
            # Calculate weighted mean and variance
            total_duration = sum(durations)
            weighted_mean = sum(d * ni for d, ni in zip(durations, normalized_impacts)) / total_duration if total_duration > 0 else 0
            
            # Weighted variance
            weighted_variance = sum(d * (ni - weighted_mean)**2 for d, ni in zip(durations, normalized_impacts)) / total_duration if total_duration > 0 else 0
            
            trend_keys = [impact['trend_key'] for impact in impacts]
            
            # Extract expectation/delivery classification from factor name
            expectation_classification = "UNKNOWN"
            delivery_classification = "UNKNOWN"
            
            if "Expectation" in factor_name:
                expectation_classification = "EXPECTATION"
            elif "Better Than Expected" in factor_name or "Worse Than Expected" in factor_name:
                expectation_classification = "DELIVERY"
            else:
                expectation_classification = "DELIVERY"  # Default to delivery if no explicit expectation
            
            if "Better Than Expected" in factor_name:
                delivery_classification = "BETTER_THAN_EXPECTATION"
            elif "Worse Than Expected" in factor_name:
                delivery_classification = "LESS_THAN_EXPECTATION"
            elif "Expectation" in factor_name:
                delivery_classification = "N/A"
            else:
                delivery_classification = "N/A"  # Default for regular delivery
            
            aggregated[factor_name] = {
                "weighted_mean": weighted_mean,
                "weighted_variance": weighted_variance,
                "average_duration": total_duration / len(impacts) if len(impacts) > 0 else 0,
                "total_duration": total_duration,
                "trend_count": len(impacts),
                "trend_keys": trend_keys,
                "expectation_classification": expectation_classification,
                "delivery_classification": delivery_classification
            }
            
            print(f"   ✅ {factor_name}: μ={weighted_mean:.4f}, σ²={weighted_variance:.4f} [{expectation_classification}] [{delivery_classification}]")
        
        return aggregated
    
    print(f"\n📊 Processing macro factors...")
    macro_aggregated = aggregate_by_factor(step3_result["macro_results"], "macro")
    
    print(f"\n📊 Processing micro factors...")
    micro_aggregated = aggregate_by_factor(step3_result["micro_results"], "micro")
    
    # Create summary DataFrame
    summary_data = []
    
    for scope, factors in [("macro", macro_aggregated), ("micro", micro_aggregated)]:
        for factor_name, factor_data in factors.items():
            summary_data.append({
                "scope": scope,
                "factor": factor_name,
                "trend_keys": f"{scope}_{factor_name}",
                "trend_count": factor_data["trend_count"],
                "weighted_mean": factor_data["weighted_mean"],
                "weighted_variance": factor_data["weighted_variance"],
                "average_duration": factor_data["average_duration"],
                "total_duration": factor_data["total_duration"],
                "expectation_classification": factor_data["expectation_classification"],
                "delivery_classification": factor_data["delivery_classification"]
            })
    
    summary_df = pd.DataFrame(summary_data)
    
    print(f"\n✅ Impact metrics completed!")
    print(f"   Generated {len(summary_data)} factor metrics")
    
    return {
        "ticker": step3_result["ticker"],
        "market_beta": step3_result["market_beta"],
        "risk_free_rate": step3_result["risk_free_rate"],
        "macro_aggregated": macro_aggregated,
        "micro_aggregated": micro_aggregated,
        "summary_df": summary_df
    }


def generate_impact_summary_schema(summary_df: pd.DataFrame, language: str = "English") -> Dict[str, Any]:
    """Generate impact metrics schema using LLM (same as notebook)"""
    print("🔍 Generating Impact Metrics schema...")
    
    summary_df_with_index = summary_df.reset_index()
    dataset_str = summary_df_with_index.to_string(index=False)
    
    prompt = f"""
You are a financial analyst expert. Analyze the dataset and classify factors into neutral categories.

DATASET:
{dataset_str}

REQUIREMENTS:
1. Classify into <=3 neutral categories for each scope (macro, micro, sector)
2. For each category, list the ROW NUMBERS that belong to it
3. Use neutral English names like "Monetary Policy", "Trade Policy", "Company Performance"
4. Output clean JSON structure
5. Extract factor names and corresponding weighted_mean values

EXAMPLE OUTPUT:
{{
    "macro_factors": [
        {{
            "factor_name": "Monetary Policy Impact",
            "row_numbers": [0, 8, 9],
            "sub_factors": ["Fed Rate Cut", "Inflation Concerns"],
            "max_return": "0.99",
            "min_return": "-0.57"
        }}
    ],
    "micro_factors": [
        {{
            "factor_name": "Company Performance",
            "row_numbers": [20, 21],
            "sub_factors": ["Strong Revenue", "Weak Earnings"],
            "max_return": "3.23",
            "min_return": "-1.28"
        }}
    ],
    "sector_factors": []
}}

Respond with ONLY the JSON object.
"""
    
    llm_agent = LLMCallAgent(default_provider="deepseek", default_model="deepseek-chat")
    
    raw_response = llm_agent.call_deepseek(
        prompt=prompt,
        system_message="You are a financial data analyst. Respond with valid JSON only.",
        model="deepseek-chat",
        max_tokens=2000,
        temperature=0.1,
    )
    
    if not raw_response:
        raise ValueError("Empty LLM response")
    
    # Clean and parse JSON
    cleaned = raw_response.strip().strip("`")
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    
    schema_result = json.loads(cleaned)
    
    print("✅ Schema generated!")
    
    return schema_result


def convert_schema_to_compound_datasets(schema_result: Dict[str, Any], summary_df: pd.DataFrame) -> pd.DataFrame:
    """Convert schema to compound impact metrics DataFrame (same as notebook)"""
    print("🔄 Converting schema to compound datasets...")
    
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
    
    all_factors = []
    
    for category, factor_groups in schema_result.items():
        for group in factor_groups:
            category_name = category.replace('_factors', '').title()
            row_numbers = group['row_numbers']
            
            factor_rows = summary_df.iloc[row_numbers]
            
            weighted_means = factor_rows['weighted_mean'].values
            avg_durations = factor_rows['average_duration'].values
            
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
    
    clean_df = pd.DataFrame(all_factors)
    clean_df = clean_df.sort_values('max_compound_return', ascending=False).reset_index(drop=True)
    
    print("📊 Compound Dataset Generated!")
    print(f"   Total factor categories: {len(clean_df)}")
    
    return clean_df


def compute_market_beta(ticker: str, previous_update_time: str, market_ticker: str = "SPY", 
                       sector_index: str = None, risk_free_rate: float = 0.025) -> float:
    """
    Compute market beta from previous_update_time to today
    
    Args:
        ticker: Stock ticker
        previous_update_time: Start date in 'YYYY-MM-DD' format
        market_ticker: Market benchmark (default: SPY)
        sector_index: Optional sector index
        risk_free_rate: Annual risk-free rate
        
    Returns:
        market_beta value
    """
    import requests
    from scipy import stats
    
    # Import centralized config
    import sys
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import FMP_API_KEY, FMP_API_V3_URL
    
    def get_stock_prices_fmp(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        url = f"{FMP_API_V3_URL}/historical-price-full/{ticker}"
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
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"📊 Computing market beta from {previous_update_time} to {end_date}")
    
    stock_df = get_stock_prices_fmp(ticker, previous_update_time, end_date)
    market_df = get_stock_prices_fmp(market_ticker, previous_update_time, end_date)
    
    if stock_df.empty or market_df.empty:
        print("⚠️ Using default beta = 1.0")
        return 1.0
    
    merged_df = stock_df.merge(market_df, on='date', suffixes=('_stock', '_market'))
    merged_df = merged_df.sort_values('date').reset_index(drop=True)
    
    merged_df['return_stock'] = merged_df['close_stock'].pct_change()
    merged_df['return_market'] = merged_df['close_market'].pct_change()
    merged_df = merged_df.dropna()
    
    if len(merged_df) < 10:
        print("⚠️ Insufficient data, using default beta = 1.0")
        return 1.0
    
    risk_free_daily = risk_free_rate / 252
    merged_df['excess_return_stock'] = merged_df['return_stock'] - risk_free_daily
    merged_df['excess_return_market'] = merged_df['return_market'] - risk_free_daily
    
    # If sector index is provided, use orthogonal sector analysis
    if sector_index:
        sector_df = get_stock_prices_fmp(sector_index, previous_update_time, end_date)
        
        if not sector_df.empty:
            merged_df = merged_df.merge(sector_df, on='date')
            merged_df = merged_df.rename(columns={'close': 'close_sector'})
            merged_df['return_sector'] = merged_df['close_sector'].pct_change()
            merged_df['excess_return_sector'] = merged_df['return_sector'] - risk_free_daily
            merged_df = merged_df.dropna()
            
            if len(merged_df) >= 10:
                # Orthogonalize sector
                slope_sector_market, intercept_sector_market, _, _, _ = stats.linregress(
                    merged_df['excess_return_market'], merged_df['excess_return_sector']
                )
                
                merged_df['sector_residual'] = merged_df['excess_return_sector'] - (
                    slope_sector_market * merged_df['excess_return_market'] + intercept_sector_market
                )
                
                # Multiple regression
                X = np.column_stack([
                    merged_df['excess_return_market'],
                    merged_df['sector_residual']
                ])
                y = merged_df['excess_return_stock']
                
                X_with_intercept = np.column_stack([np.ones(len(X)), X])
                beta_coeffs = np.linalg.lstsq(X_with_intercept, y, rcond=None)[0]
                
                market_beta = beta_coeffs[1]
                sector_beta = beta_coeffs[2]
                
                print(f"   ✅ Beta (with sector): β_market={market_beta:.4f}, β_sector={sector_beta:.4f}")
                return market_beta
    
    # Single beta regression
    slope, intercept, _, _, _ = stats.linregress(
        merged_df['excess_return_market'], merged_df['excess_return_stock']
    )
    
    market_beta = slope
    
    print(f"   ✅ Market Beta: {market_beta:.4f}")
    
    return market_beta


def generate_update_metrics(ticker: str, previous_update_time: str, 
                           language: str = "English",
                           sector_index: str = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generate update metrics from previous_update_time to today
    
    Args:
        ticker: Stock ticker (e.g., 'AAPL')
        previous_update_time: Start date in 'YYYY-MM-DD' format
        language: Language for factor names (default: "English")
        sector_index: Optional sector index ticker (e.g., 'XLK')
        
    Returns:
        Tuple of (impact_metrics_df, final_impact_metrics_df, factor_time_df)
    """
    print(f"\n{'='*80}")
    print(f"🚀 Generating Update Metrics for {ticker}")
    print(f"📅 From: {previous_update_time} to Today")
    print(f"{'='*80}\n")
    
    # Step 1: Read and filter stock trend data
    print("📖 Step 1: Reading filtered stock trend data...")
    read_information = read_stock_trend_data_filtered(ticker, previous_update_time)
    
    if not read_information or not read_information.get('historical_trends'):
        raise ValueError(f"No stock trend data available from {previous_update_time}")
    
    # Step 2: Compute market beta for this period
    market_beta = compute_market_beta(ticker, previous_update_time, sector_index=sector_index)
    
    # Step 3: Get factors - USE DYNAMIC FACTOR LOGIC BASED ON NEW TRENDS
    print("\n🔍 Step 2: Extracting factors...")
    step1_result = step1_get_factors_dynamic(ticker, read_information, language)
    
    # Step 4: Get date ranges - USE STORAGE AGENT FUNCTION
    print("\n🗓️ Step 3: Mapping date ranges...")
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from Quant_Impact_Storage_Agent import step2_get_date_ranges
    step2_result, factor_time_df = step2_get_date_ranges(ticker, step1_result, language)
    
    # Step 4: Calculate alpha using CAPM regression
    print("\n🧮 Step 4: Calculating alpha using CAPM regression...")
    
    # Calculate alpha using simple CAPM regression
    from scipy import stats
    import numpy as np
    import requests
    
    # Import centralized config
    import sys
    import os
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    from config import FMP_API_KEY, FMP_API_V3_URL
    
    def get_stock_prices_fmp(ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        url = f"{FMP_API_V3_URL}/historical-price-full/{ticker}"
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
    stock_df = get_stock_prices_fmp(ticker, previous_update_time, end_date)
    market_df = get_stock_prices_fmp("SPY", previous_update_time, end_date)
    
    alpha_daily = 0.0  # Default alpha
    if not stock_df.empty and not market_df.empty:
        merged_df = stock_df.merge(market_df, on='date', suffixes=('_stock', '_market'))
        merged_df = merged_df.sort_values('date').reset_index(drop=True)
        
        merged_df['return_stock'] = merged_df['close_stock'].pct_change()
        merged_df['return_market'] = merged_df['close_market'].pct_change()
        merged_df = merged_df.dropna()
        
        if len(merged_df) >= 10:
            risk_free_daily = 0.025 / 365
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
            print(f"   ⚠️ Insufficient data for alpha calculation, using default alpha = 0")
    else:
        print(f"   ⚠️ Could not fetch data for alpha calculation, using default alpha = 0")
    
    # Step 5: Beta filtering with alpha - USE UPDATED FUNCTION
    print("\n⚖️ Step 5: Beta filtering with alpha...")
    step3_result = step3_beta_filtering(
        ticker=ticker,
        step2_result=step2_result,
        read_information=step1_result["read_information"],
        market_beta=market_beta,
        alpha_daily=alpha_daily,
        risk_free_rate=0.025
    )
    
    # Step 6: Impact metrics - USE STORAGE AGENT FUNCTION
    print("\n📊 Step 6: Computing impact metrics...")
    # sys.path already set above
    from Quant_Impact_Storage_Agent import step4_impact_metrics
    step4_result = step4_impact_metrics(step3_result)
    impact_metrics_df = step4_result['summary_df']
    
    # Step 7: Calculate missing metrics (trend_weight_score, score_weighted_mean, etc.)
    print("\n🔧 Step 7: Calculating missing metrics...")
    impact_metrics_df = calculate_missing_metrics(impact_metrics_df)
    
    # Step 8: Generate final impact metrics schema - USE STORAGE AGENT FUNCTIONS
    print("\n🎯 Step 8: Generating final impact metrics...")
    # sys.path already set above
    from Quant_Impact_Storage_Agent import generate_impact_summary_schema, convert_schema_to_compound_datasets
    schema_result = generate_impact_summary_schema(impact_metrics_df, language)
    final_impact_metrics_df = convert_schema_to_compound_datasets(schema_result, impact_metrics_df)
    
    print(f"\n{'='*80}")
    print(f"✅ Update Metrics Generated Successfully!")
    print(f"{'='*80}\n")
    print(f"📊 Final Impact Metrics: {len(final_impact_metrics_df)} factors")
    print(f"📅 Factor Time Mappings: {len(factor_time_df)} intervals")
    
    return impact_metrics_df, final_impact_metrics_df, factor_time_df


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    """
    Example usage:
    
    from Quant_Impact_Update_Metrics import generate_update_metrics
    
    impact_df, impact_metrics_df, factor_time_df = generate_update_metrics(
        ticker="AAPL",
        previous_update_time="2025-01-01",
        language="English"
    )
    
    print(impact_df.head())
    print(impact_metrics_df.head())
    print(factor_time_df.head())
    """
    
    # Test with a ticker
    ticker = "AAPL"
    previous_update_time = "2025-01-01"
    
    impact_df, impact_metrics_df, factor_time_df = generate_update_metrics(
        ticker=ticker,
        previous_update_time=previous_update_time,
        language="English"
    )
    
    print("\n" + "="*80)
    print("📊 IMPACT METRICS PREVIEW:")
    print("="*80)
    print(impact_df.head(10))
    
    print("\n" + "="*80)
    print("🎯 IMPACT METRICS PREVIEW:")
    print("="*80)
    print(impact_metrics_df.head(10))
    
    print("\n" + "="*80)
    print("📅 FACTOR TIME MAPPINGS PREVIEW:")
    print("="*80)
    print(factor_time_df.head(10))

