# News_Verification.py  ─────────────────────────────────────────────────────────
# 依赖：pip install python-dotenv langchain openai youtube_transcript_api requests bs4 redis
# 环境变量：DEEPSEEK_API_KEY  TAVILY_API_KEY  OPENAI_API_KEY
# 新增功能：用户ID数据库跟踪、实时进度监控、结果持久化存储

import asyncio, json, os, re, time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
import logging
import datetime
import difflib

# ─── 第三方 ──────────────────────────────────────────────────────────
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi
import redis

# ─── LangChain / LangGraph ─────────────────────────────────────────
from langchain.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_deepseek import ChatDeepSeek
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

# ─── 环境变量 ───────────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# NOTE: Replace with your actual API keys or load from environment
DEEPSEEK_API_KEY = 'sk-43e9043c7ab8480393d34367f2ae997e'
TAVILY_API_KEY   = "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"
OPENAI_API_KEY   = "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"

# ─── Redis 配置 ─────────────────────────────────────────────────────
REDIS_CONFIG = {
    "host": "redis-16204.fcrce180.us-east-1-1.ec2.redns.redis-cloud.com",
    "port": 16204,
    "username": "default",
    "password": "9rHiMKl63iYK9ja4qja6ZjnamuixS4UG",
    "decode_responses": True
}



# ─── 基础模型 & 搜索工具 ────────────────────────────────────────────
model = ChatDeepSeek(model="deepseek-chat", api_key=DEEPSEEK_API_KEY)
tavily_search_tool = TavilySearchResults(max_results=10, tavily_api_key=TAVILY_API_KEY, search_depth="advanced", topic="finance", time_range="month")

# ─── 新功能说明 ─────────────────────────────────────────────────────
# 1. 用户ID数据库跟踪：每个用户有独立的进度和结果存储
# 2. 实时进度监控：Filter 1 (30%) → Filter 2 (60%) → Filter 3 (100%)
# 3. 结果持久化：验证结果存储在Redis中，30天有效期
# 4. 进度跟踪：实时更新到Redis，24小时有效期
# 5. 数据库键：news_verification_progress:{user_id}, news_verification_result:{user_id}


# ─── 结果结构体 ─────────────────────────────────────────────────────
class FilterStatus(Enum):
    PENDING     = "pending"
    PROCESSING  = "processing"
    PASSED      = "passed"
    FAILED      = "failed"
    SKIPPED     = "skipped"

@dataclass
class FilterResult:
    name    : str
    status  : FilterStatus
    result  : Dict[str, Any]
    details : str
    timestamp: float

@dataclass
class VerificationResult:
    statement       : str
    filters         : List[FilterResult]
    final_decision  : Optional[str]               = None
    final_reasoning : Optional[str]               = None
    reference_links : List[Dict[str, str]] | None = None

# ─── 用户数据库管理 ─────────────────────────────────────────────────────
class NewsVerificationDB:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.redis_client = None
        self._connect_redis()
        
        # Redis keys for this user - same structure as other agents
        self.progress_key = f"news_verification_progress:{user_id}"
        self.result_key = f"news_verification_result:{user_id}"
        self.frontend_progress_key = f"news_verification_frontend_progress:{user_id}"
    
    def _connect_redis(self):
        """Connect to Redis user database"""
        try:
            self.redis_client = redis.Redis(
                host=REDIS_CONFIG["host"],
                port=REDIS_CONFIG["port"],
                username=REDIS_CONFIG["username"],
                password=REDIS_CONFIG["password"],
                decode_responses=True
            )
            self.redis_client.ping()
            print(f"✅ Redis connected for user {self.user_id}")
        except Exception as e:
            print(f"❌ Redis connection failed: {e}")
            self.redis_client = None
    
    def update_progress(self, step: str, status: str, progress: int = None, details: str = ""):
        """
        Update progress in Redis - same structure as other agents
        
        Args:
            step: Current step (e.g., "source verification", "video analysis", "inference analysis")
            status: Status (e.g., "started", "completed", "failed")
            progress: Progress percentage (0-100)
            details: Additional details
        """
        if not self.redis_client:
            print("⚠️ Redis not available for progress tracking")
            return
        
        try:
            progress_data = {
                "user_id": self.user_id,
                "step": step,
                "status": status,
                "progress": progress,
                "details": details,
                "timestamp": datetime.datetime.now().isoformat(),
                "agent": "news_verification"  # Identify this agent's data
            }
            
            # Store progress update in Redis - same structure as other agents
            progress_key = self.frontend_progress_key
            
            # Get existing progress data
            existing_data = self.redis_client.hgetall(progress_key)
            
            # Create updated data structure
            updated_data = {}
            
            # Keep existing data from other agents
            for key, value in existing_data.items():
                try:
                    data = json.loads(value)
                    # Only keep data from other agents
                    if data.get("agent") != "news_verification":
                        updated_data[key] = value
                except:
                    # Keep non-JSON data (legacy)
                    updated_data[key] = value
            
            # Add/update News Verification Agent data
            news_key = f"news_verification:{step}"
            updated_data[news_key] = json.dumps(progress_data)
            
            # Store all data back to Redis
            if updated_data:
                self.redis_client.hset(progress_key, mapping=updated_data)
            
            # Set expiry to clean up old progress (24 hours)
            self.redis_client.expire(progress_key, 86400)
            
            print(f"📊 Progress Update: {step} - {status} ({progress}%)")
            
        except Exception as e:
            print(f"❌ Failed to update progress: {e}")
    
    def store_result(self, verification_result):
        """Store verification result in Redis"""
        if not self.redis_client:
            print("❌ Redis not connected. Cannot store result.")
            return False
        
        try:
            # Convert VerificationResult to dict for storage
            result_data = {
                "user_id": self.user_id,
                "statement": verification_result.statement,
                "filters": [
                    {
                        "name": f.name,
                        "status": f.status.value,
                        "result": f.result,
                        "details": f.details,
                        "timestamp": f.timestamp
                    } for f in verification_result.filters
                ],
                "final_decision": verification_result.final_decision,
                "final_reasoning": verification_result.final_reasoning,
                "reference_links": verification_result.reference_links,
                "completed_at": datetime.datetime.now().isoformat(),
                "status": "completed"
            }
            
            # Store result
            result_json = json.dumps(result_data, default=str)
            self.redis_client.set(self.result_key, result_json)
            self.redis_client.expire(self.result_key, 30 * 24 * 60 * 60)  # 30 days
            
            print(f"✅ Result stored for user {self.user_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to store result: {e}")
            return False
    
    def get_progress(self):
        """Get current progress for user"""
        if not self.redis_client:
            return {'error': 'Redis not connected'}
        
        try:
            # ✅ Use the same key that update_progress uses (frontend_progress_key)
            progress_data = self.redis_client.hgetall(self.frontend_progress_key)
            return progress_data if progress_data else {'error': 'No progress data found'}
        except Exception as e:
            return {'error': f'Failed to get progress: {e}'}
    
    def get_frontend_progress(self):
        """Get frontend progress data - same structure as other agents"""
        if not self.redis_client:
            return {'error': 'Redis not connected'}
        
        try:
            progress_data = self.redis_client.hgetall(self.frontend_progress_key)
            return progress_data if progress_data else {'error': 'No frontend progress data found'}
        except Exception as e:
            return {'error': f'Failed to get frontend progress: {e}'}
    
    def get_result(self):
        """Get verification result for user"""
        if not self.redis_client:
            return {'error': 'Redis not connected'}
        
        try:
            result_data = self.redis_client.get(self.result_key)
            if result_data:
                return json.loads(result_data)
            else:
                return {'error': 'No result found'}
        except Exception as e:
            return {'error': f'Failed to get result: {e}'}

# ─── WebSocket 回调 ────────────────────────────────────────────────
verification_callbacks: Dict[str, Any] = {}
def register_callback(sid: str, cb): verification_callbacks[sid] = cb
def unregister_callback(sid: str):    verification_callbacks.pop(sid, None)


async def notify_progress(sid: str, fname: str, status: FilterStatus,
                          details: str = "", result: Dict|None = None):
    if sid in verification_callbacks:
        try:
            await verification_callbacks[sid](fname, status, details, result)
        except Exception as e:
            logger.error(f"Error in notify_progress: {e}")

# ─── 同步 → 线程池 包装 ────────────────────────────────────────────
def deepseek_llm_sync(prompt: str, hist: List[Dict]|None = None):
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    msgs = hist[:] if hist else []
    msgs.append({"role": "user", "content": prompt})
    out  = client.chat.completions.create(model="deepseek-chat", messages=msgs)
    content = out.choices[0].message.content
    return {"content": content, "history": msgs+[{"role":"assistant","content":content}]}

async def deepseek_llm(prompt: str, hist: List[Dict]|None = None):
    return await asyncio.to_thread(deepseek_llm_sync, prompt, hist)

async def tavily_search(q: str, k: int = 3, topic: str = "finance", time_range: str = "month", include_domains: List[str] = []):
    """Fixed tavily search with better error handling and timeout, now supports time_range"""
    try:
        print("[DEBUG] tavily_search: Starting search with query:", q)
        tool = TavilySearchResults(max_results=k, topic=topic, tavily_api_key=TAVILY_API_KEY, time_range=time_range, include_domains=include_domains)
        print("[DEBUG] tavily_search: Created TavilySearchResults tool")
        
        # Try the tool first
        raw_result = await asyncio.wait_for(
            asyncio.to_thread(tool.invoke, {"query": q}),
            timeout=30.0  # 30 second timeout per search
        )
        print("[DEBUG] tavily_search: Raw result type:", type(raw_result))
        print("[DEBUG] tavily_search: Raw result:", repr(raw_result)[:500])
        
        # If the tool returned a string (error message), try using the API wrapper directly
        if isinstance(raw_result, str):
            print("[DEBUG] tavily_search: Tool returned string, trying API wrapper directly")
            if hasattr(tool, 'api_wrapper'):
                raw_result = tool.api_wrapper.raw_results(q)
                print("[DEBUG] tavily_search: API wrapper response type:", type(raw_result))
                print("[DEBUG] tavily_search: API wrapper response:", repr(raw_result)[:500])
            else:
                print("[DEBUG] tavily_search: No API wrapper available, returning empty results")
                return {"results": []}
        
        # If result is a tuple (from TavilySearchResults), take the first element
        if isinstance(raw_result, tuple):
            print("[DEBUG] tavily_search: Converting tuple result to first element")
            raw_result = raw_result[0]
            
        # Ensure result is a dictionary with a "results" key
        if not isinstance(raw_result, dict):
            print("[DEBUG] tavily_search: Result is not a dictionary, returning empty results")
            return {"results": []}
            
        if "results" not in raw_result:
            print("[DEBUG] tavily_search: Result missing 'results' key, returning empty results")
            return {"results": []}
            
        return raw_result
    except asyncio.TimeoutError:
        logger.error(f"Tavily search timeout for query: {q}")
        return {"results": []}
    except Exception as e:
        logger.error(f"Tavily search error: {e}")
        print("[DEBUG] tavily_search: Error details:", str(e))
        return {"results": []}

async def fetch_yt_transcript(vid: str, sid: str = None):
    try:
        # Add timeout to transcript fetch
        trans = await asyncio.wait_for(
            asyncio.to_thread(YouTubeTranscriptApi.get_transcript, vid),
            timeout=30.0  # 30 second timeout for transcript
        )
        if sid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, "Transcript fetched successfully")
        return trans
    except asyncio.TimeoutError:
        logger.error("YouTube transcript fetch timeout")
        if sid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, "Transcript fetch timeout")
        raise
    except Exception as e:
        logger.error(f"YouTube transcript fetch error: {e}")
        if sid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, f"Transcript error: {str(e)}")
        raise

# ─── JSON 抽取 ─────────────────────────────────────────────────────
def extract_json_block(txt: str) -> dict:
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", txt)
    js = m.group(1) if m else txt
    return json.loads(js.strip())

# ─── Agent 1  Reason Agent ─────────────────────────────────────────
async def async_reason_agent(statement: str, sid: str):
    await notify_progress(sid, "Filter 3.a: Inference Point", FilterStatus.PROCESSING, "Analyzing structure…")
    # DEBUG: Print the LLM prompt and response
    print("[DEBUG] async_reason_agent: statement:", statement)
    llm_prompt = f"""
Analyze the following statement and create a hierarchical tree structure for market impact analysis.

You are a news/fact-checking agent. Your analysis feeds investors' decision-making in stock/crypto markets.
Think about how the news or fact affects the market (noise vs real impact).

Create a tree structure with the following hierarchy:
1. Strategy/Theme (main market impact)
2. Analysis Levels (branches):
   - Macro (nation/global policy, central bank)
   - Fundamental (company-specific, financials)
   - Price (market microstructure, liquidity)
3. For each level, identify specific data points needed for verification

Output JSON strictly:
{{
  "strategy": {{
    "name": "Main market impact theme",
    "description": "Brief explanation of the strategy/theme"
  }},
  "analysis_levels": {{
    "macro": {{
      "name": "Macro-level impact",
      "data_points": [
        {{
          "name": "Specific macro data point",
          "time_interval": "Required time range",
          "purpose": "Why this data point matters",
          "data_source": "Source type"
        }}
      ]
    }},
    "fundamental": {{
      "name": "Fundamental-level impact",
      "data_points": [
        {{
          "name": "Specific fundamental data point",
          "time_interval": "Required time range",
          "purpose": "Why this data point matters",
          "data_source": "Source type"
        }}
      ]
    }},
    "price": {{
      "name": "Price-level impact",
      "data_points": [
        {{
          "name": "Specific price data point",
          "time_interval": "Required time range",
          "purpose": "Why this data point matters",
          "data_source": "Source type"
        }}
      ]
    }}
  }},
  "end_goal": "One sentence summarizing what the data will confirm"
}}

Statement:
{statement}

Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
You are a API call, you answer will directly be used by the next agent, hence you do not need to include any explanation or markdown, just the JSON object.
""".strip()
    try:
        resp   = await asyncio.wait_for(deepseek_llm(llm_prompt), timeout=120)
        print("[DEBUG] async_reason_agent: LLM response:", resp)
        result = extract_json_block(resp["content"])
        print("[DEBUG] async_reason_agent: Parsed reason JSON:", result)
        await notify_progress(sid, "Filter 3.a: Inference Point", FilterStatus.PASSED, "Structure OK", result)
        return result
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 3.a: Inference Point", FilterStatus.FAILED, str(e), err)
        return err

# ─── Agent 2  Online Data Agent (FIXED) ────────────────────────────────────
async def async_online_data_agent(reason_json: dict, sid: str):
    await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.PROCESSING, "Gathering evidence…")
    print("[DEBUG] async_online_data_agent: reason_json:", reason_json)
    
    # Initialize search_tasks list
    search_tasks = []
    
    # Extract data points from analysis levels
    data_points = []
    for level in reason_json.get("analysis_levels", {}).values():
        if isinstance(level, dict) and "data_points" in level:
            data_points.extend(level["data_points"])
    
    # Create search tasks for each data point
    for data_point in data_points[:5]:  # Limit to 5 searches
        if not isinstance(data_point, dict):
            continue
        q = data_point.get("name")
        if not q:
            continue
        purpose = data_point.get("purpose", "")
        time_interval = data_point.get("time_interval", "")
        
        # Create search query
        search_query = f"{q}. Purpose: {purpose}. Time: {time_interval}" if purpose else f"{q}. Time: {time_interval}"
        task = tavily_search(search_query, 2, "finance", time_range="month")
        search_tasks.append(task)
    
    print("[DEBUG] async_online_data_agent: search_tasks:", search_tasks)
    
    if not search_tasks:
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.PASSED, "No searches needed", {})
        return {}
    try:
        search_results = await asyncio.wait_for(
            asyncio.gather(*search_tasks, return_exceptions=True),
            timeout=60.0
        )
        # Ensure every result is a dict to prevent 'str' object has no attribute 'get'
        search_results = [ensure_dict(r) for r in search_results]
        output: Dict[str, Any] = {}
        for i, (data_point, result) in enumerate(zip(data_points, search_results)):
            # Use the data point's name as the key, or fallback to index
            key = data_point.get('name') if isinstance(data_point, dict) and 'name' in data_point else f'data_point_{i}'
            if isinstance(result, Exception):
                output[key] = []
            else:
                safe_results = []
                for r in result.get("results", []) if isinstance(result, dict) else []:
                    if isinstance(r, dict):
                        safe_results.append({
                            "title": r.get("title", ""),
                            "summary": r.get("content", "")[:500],
                            "url": r.get("url", "")
                        })
                    else:
                        print(f"[WARNING] Source Searching: result is not a dict: {r}")
                        safe_results.append({
                            "title": "Non-dict result",
                            "summary": str(r)[:500],
                            "url": ""
                        })
                output[key] = safe_results
            await notify_progress(
                sid, "Filter 3.b: Inference Evidence", FilterStatus.PROCESSING,
                f"{i+1}/{len(data_points)} searches completed"
            )
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.PASSED, "Evidence collected", output)
        return output
    except asyncio.TimeoutError:
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.FAILED, "Search timeout", {"error": "timeout"})
        return {"error": "Search timeout"}
    except Exception as e:
        await notify_progress(sid, "Filter 3.b: Inference Evidence", FilterStatus.FAILED, str(e), {"error": str(e)})
        return {"error": str(e)}

# ─── Agent 3  Decision Agent ───────────────────────────────────────
async def async_decision_agent(statement: str, evidence: dict, sid: str):
    await notify_progress(sid, "Filter 3.c: Feasibility Check", FilterStatus.PROCESSING, "Making decision…")
    
    # Handle case where evidence might contain error
    if isinstance(evidence, dict) and "error" in evidence:
        await notify_progress(sid, "Filter 3.c: Feasibility Check", FilterStatus.FAILED, "No evidence available")
        return {
            "decision": "Noise for Investment",
            "reasoning": "Unable to gather sufficient evidence due to search errors."
        }
    
    # If evidence contains verifier output, extract its reason for the prompt
    verifier_info = ""
    context_analysis_info = ""
    
    if isinstance(evidence, dict) and "verifier" in evidence:
        v = evidence["verifier"]
        if isinstance(v, dict):
            if v.get("reason"):
                verifier_info = f"Verifier Agent reason: {v['reason']}"
            elif v.get("error"):
                verifier_info = f"Verifier Agent error: {v['error']}"
            elif v.get("content"):
                verifier_info = f"Verifier Agent content: {v['content']}"
                
                # Extract context analysis if available
                try:
                    content_data = json.loads(v.get("content", "{}"))
                    if content_data.get("context_analysis"):
                        ca = content_data["context_analysis"]
                        context_analysis_info = f"""
🎯 SMART CONTEXT ANALYSIS RESULTS:
- Context Match: {ca.get('context_match', 'Unknown')}
- Context Percentage: {ca.get('context_percentage', 0):.1f}%
- Context Matches: {ca.get('context_matches', 0)}/{ca.get('total_results', 0)}
- Companies Found: {', '.join(ca.get('companies_found', []))}
- Tickers Found: {', '.join(ca.get('tickers_found', []))}
- Time Periods: {', '.join(ca.get('time_periods_found', []))}
- Financial Metrics: {', '.join(ca.get('financial_metrics_found', []))}
- Analysis: {ca.get('reason', 'No analysis available')}
"""
                except:
                    pass
    
    ev_text = "\n\n".join(
        f"Title: {r['title']}\nURL: {r['url']}\nSummary: {r['summary']}"
        for lst in evidence.get("evidence", {}).values() if isinstance(lst, list)
        for r in lst
    )[:12000]

    prompt = f"""
You are **Investment Noise Filter Agent** - your job is to determine if a statement contains INVESTMENT-RELEVANT information, not to play word games.

================================================================
STATEMENT TO ANALYZE
================================================================
{statement}

================================================================
EVIDENCE FROM MULTIPLE SOURCES
================================================================
{ev_text if ev_text else "No evidence available"}

{verifier_info}

{context_analysis_info}

================================================================
🎯 INVESTMENT NOISE FILTERING LOGIC 🎯
================================================================
**IMPORTANT: This is INVESTMENT noise filtering, not word-perfect matching!**

**PASS (Not Noise for Investment) if:**
✅ ANY credible source found (even just 1)
✅ Sources mention ANY company/stock/ticker
✅ Sources cover ANY time period
✅ Sources discuss ANY business/financial topic
✅ ANY context match found
✅ ANY investment-relevant information

**FAIL (Noise for Investment) if:**
❌ NO credible sources found at all
❌ Sources completely unrelated to business/finance
❌ Sources discuss completely different topics
❌ No business/investment relevance whatsoever

**SMART CONTEXT ANALYSIS:**
- "Earnings missed expectations" vs "Revenue missed expectations" = SAME EVENT
- "Q2 2025" vs "Second quarter 2025" = SAME PERIOD  
- "Coinbase" vs "COIN stock" = SAME COMPANY
- Focus on EVENT EXISTENCE, not exact word matching

================================================================
✦✦ HARD RULES — apply BEFORE any reasoning ✦✦
================================================================
**ALWAYS TRY TO PASS FIRST** - Only fail if absolutely no business/finance relevance found.

If the Verifier Agent failed, but ANY business/finance content was found → PASS
If the Evidence section is empty, but the statement mentions business/finance → PASS

Only return FAIL if:
{{
  "decision": "Noise for Investment",
  "reasoning": "No business or financial relevance found whatsoever."
}}

================================================================
If NONE of the hard-rule conditions fire, proceed:

• **DEFAULT TO PASS** unless clearly no business/finance relevance
• Check if ANY sources mention business/finance topics
• Determine if this has ANY investment relevance
• ≤ 150-word concise reasoning focusing on business relevance
• Return JSON with only the following two keys:

{{
  "decision": "Not Noise for Investment" | "Noise for Investment",
  "reasoning": "<your explanation ≤150 words>"
}}

Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
You are a API call, you answer will directly be used by the next agent, hence you do not need to include any explanation or markdown, just the JSON object.
""".strip()

    try:
        resp   = await asyncio.wait_for(deepseek_llm(prompt), timeout=150)
        result = extract_json_block(resp["content"])
        status = (FilterStatus.PASSED if result.get("decision", "").strip().lower() == "not noise for investment"
                  else FilterStatus.FAILED)
        await notify_progress(sid, "Filter 3.c: Feasibility Check", status, result.get("reasoning", ""), result)
        return result
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 3.c: Feasibility Check", FilterStatus.FAILED, str(e), err)
        return err

# ─── Agent 0  Verifier Agent ───────────────────────────────────────


credit_list = [
    # Major News Agencies
    "bbc.com/news",
    "reuters.com",
    "apnews.com",
    "aljazeera.com",
    "afp.com",
    
    # Financial News Sources
    "bloomberg.com",
    "wsj.com",
    "ft.com",
    "cnbc.com",
    "finance.yahoo.com",
    "forbes.com",
    "investopedia.com",
    "marketwatch.com",
    "barrons.com",
    "morningstar.com",
    "seekingalpha.com",
    "businessinsider.com",
    "fortune.com",
    
    # General News with Business Sections
    "economist.com",
    "nytimes.com",
    "washingtonpost.com",
    "npr.org",
    "npr.org/sections/business",
    "pbs.org/newshour",
    "politico.com",
    
    # Fact-Checking Sources
    "snopes.com",
    "politifact.com",
    "factcheck.org",
    "mediabiasfactcheck.com",
    "leadstories.com",
    "factcheck.afp.com",
    "reuters.com/fact-check"
]

verifier_agent = create_react_agent(
    model,
    tools=[tavily_search_tool],
    name="verifier_agent",
    prompt="""
# Investment Noise Filter Verifier Agent

**PURPOSE:** Determine if a financial statement contains INVESTMENT-RELEVANT information, not to play word games.

**STAGE 1:** Find credible sources discussing the SAME EVENT/COMPANY/PERIOD
**STAGE 2:** Analyze if sources confirm the EVENT exists (even if wording differs slightly)

================================================================
🎯 SMART CONTEXT ANALYSIS 🎯
================================================================
**PASS (FAITHFUL) if:**
✅ Sources discuss the SAME company/stock/ticker mentioned
✅ Sources cover the SAME time period/quarter mentioned  
✅ Sources discuss SIMILAR financial metrics (earnings, revenue, etc.)
✅ Context suggests the SAME market event/development
✅ Multiple sources confirm the EVENT exists

**FAIL (MISLEADING/UNVERIFIABLE) if:**
❌ Sources discuss completely different companies/events
❌ Sources cover different time periods
❌ No financial/investment relevance
❌ Sources completely contradict the core claim

**CONTEXT MATCHING EXAMPLES:**
- "Earnings missed expectations" vs "Revenue missed expectations" = SAME EVENT ✅
- "Q2 2025" vs "Second quarter 2025" = SAME PERIOD ✅
- "Coinbase" vs "COIN stock" = SAME COMPANY ✅
- "Earnings beat expectations" vs "Earnings missed expectations" = CONTRADICTION ❌

================================================================
OUTPUT FORMAT
================================================================
Return a valid JSON object with the following keys:
{
  "source": {"url": "...", "credibility": "...", "date": "..."},
  "analysis": "Context analysis focusing on EVENT confirmation, not exact word matching",
  "verdict": "FAITHFUL" | "MISLEADING" | "UNVERIFIABLE",
  "reason": "Clear explanation of why the event is confirmed or not"
}

**IMPORTANT:** Focus on EVENT EXISTENCE and CONTEXT, not perfect word matching!
Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
"""
)

async def async_verifier_agent(statement: str, sid: str):
    await notify_progress(sid, "Filter 1: Source Check", FilterStatus.PROCESSING, "Verifying text source…")
    try:
        print("[DEBUG] Filter 1: Starting tavily search...")
        search_result = await tavily_search(
            statement,
            k=10,
            topic="finance",
            time_range="month",
            include_domains=credit_list
        )
        # Ensure the result is a dictionary
        search_result = ensure_dict(search_result)
        print("[DEBUG] Filter 1: Search result type:", type(search_result))
        print("[DEBUG] Filter 1: Search result keys:", search_result.keys() if isinstance(search_result, dict) else "Not a dict")
        
        # Check if there are any results
        results = search_result.get("results", [])
        print("[DEBUG] Filter 1: Results type:", type(results))
        print("[DEBUG] Filter 1: Results length:", len(results))
        
        for idx, r in enumerate(results):
            print(f"[DEBUG] Filter 1: Result[{idx}] type: {type(r)}")
            print(f"[DEBUG] Filter 1: Result[{idx}] value: {repr(r)[:200]}")
            if isinstance(r, dict):
                print(f"[DEBUG] Filter 1: Result[{idx}] keys: {r.keys()}")
            else:
                print(f"[DEBUG] Filter 1: Result[{idx}] is not a dict!")
        
        # Only pass if at least one result is from a credit domain
        def is_credit_source(url):
            return any(domain in url for domain in credit_list)
        
        credit_results = []
        for r in results:
            if not isinstance(r, dict):
                print(f"[DEBUG] Filter 1: Skipping non-dict result: {type(r)}")
                continue
            url = r.get("url", "")
            if is_credit_source(url):
                credit_results.append(r)
                print(f"[DEBUG] Filter 1: Found credit source: {url}")
        
        # Require at least 1 credible source for verification (reduced from 2)
        if len(credit_results) < 1:
            err = {"content": f"No credible sources found for '{statement}'. Need at least 1, found {len(credit_results)}.", "passed": False}
            await notify_progress(sid, "Filter 1: Source Check", FilterStatus.FAILED, err["content"], err)
            return err
        
        # Smart context analysis for investment noise filtering
        context_analysis = analyze_investment_context(statement, credit_results)
        
        # Enhanced content with context analysis
        enhanced_content = {
            "results": credit_results,
            "context_analysis": context_analysis,
            "smart_filtering": True
        }
        
        content = json.dumps(enhanced_content)
        
        # Log context analysis for debugging
        print(f"[DEBUG] Context Analysis: {context_analysis}")
        
        await notify_progress(sid, "Filter 1: Source Check", FilterStatus.PASSED, 
                            f"Credible source found with {context_analysis['context_matches']}/{context_analysis['total_results']} context matches", 
                            {"content": content, "passed": True})
        return {"content": content, "passed": True}
    except asyncio.TimeoutError:
        err = {"error": "Verification timeout"}
        await notify_progress(sid, "Filter 1: Source Check", FilterStatus.FAILED, "Timeout", err)
        return err
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 1: Source Check", FilterStatus.FAILED, str(e), err)
        return err

# ─── Video Verifier (可选) ─────────────────────────────────────────
video_verifier_agent = create_react_agent(
    model, tools=[], name="video_verifier_agent",
    prompt="""
Locate the claim in YouTube transcript, show context and analysis.

Output:
Return a valid JSON object with the following keys:
{
  "time_location": "...",
  "context": "...",
  "analysis": "..."
}
Your output MUST be valid JSON and nothing else. Do not include any explanation or markdown, just the JSON object.
You are a API call, you answer will directly be used by the next agent, hence you do not need to include any explanation or markdown, just the JSON object.
"""
)

def extract_yid(url: str) -> Optional[str]:
    m = re.search(r"(?:youtu\\.be/|v=|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    return m.group(1) if m else None

async def search_youtube(statement: str):
    try:
        # Add timeout to YouTube search
        sr = await asyncio.wait_for(
            tavily_search(f"youtube video about {statement}", 1, "news", time_range="month"),
            timeout=30.0  # 30 second timeout for search
        )
        for r in sr.get("results", []):
            vid = extract_yid(r.get("url", ""))
            if vid:
                return vid, r.get("title", ""), r.get("content", ""), r.get("url", "")
        return None, "", "", ""
    except asyncio.TimeoutError:
        logger.error("YouTube search timeout")
        return None, "", "", ""
    except Exception as e:
        logger.error(f"YouTube search error: {e}")
        return None, "", "", ""

async def async_video_verifier(statement: str, sid: str):
    await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, "Searching YouTube…")
    
    try:
        # Search for video with timeout
        vid, title, content, url = await search_youtube(statement)
        if not vid:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, "No relevant video found")
            return {"error": "No video", "passed": False}
            
        await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, f"Found video: {title}")
        
        # Fetch transcript with timeout and progress updates
        try:
            trans = await fetch_yt_transcript(vid, sid)
        except Exception as e:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, f"Failed to get transcript: {str(e)}")
            return {"error": f"Transcript error: {str(e)}", "passed": False}
            
        # Process transcript in chunks to avoid memory issues
        chunk_size = 50  # Process 50 segments at a time
        txt_chunks = []
        for i in range(0, min(len(trans), 200), chunk_size):  # Limit to first 200 segments
            chunk = trans[i:i + chunk_size]
            txt_chunks.append("\n".join(f"[{round(t['start'],2)}] {t['text']}" for t in chunk))
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, 
                                f"Processing transcript: {i+len(chunk)}/{min(len(trans), 200)} segments")
        
        txt = "\n".join(txt_chunks)
        
        # Run video agent with timeout
        try:
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PROCESSING, "Analyzing video content...")
            resp = await asyncio.wait_for(
                asyncio.to_thread(video_verifier_agent.invoke,
                                {"messages":[{"role":"user",
                                            "content":f"statement:{statement}\\ntranscript:\\n{txt}"}]}),
                timeout=60.0  # Reduced timeout to 60 seconds
            )
            res = resp["messages"][-1].content
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.PASSED,
                                f"Video analyzed: {title}",
                                {"content": res, "video_url": url, "video_title": title})
            return {"content": res, "video_url": url, "video_title": title, "passed": True}
            
        except asyncio.TimeoutError:
            err = {"error": "Video analysis timeout"}
            await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, "Analysis timeout", err)
            return err
            
    except Exception as e:
        err = {"error": str(e)}
        await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.FAILED, str(e), err)
        return err

# ─── 主 pipeline ──────────────────────────────────────────────────
# FIXED: Pass/fail logic now properly validates agent outputs
async def verify_statement(statement: str, sid: str, use_video: bool = False) -> VerificationResult:
    filters: List[FilterResult] = []
    
    logger.info(f"Starting verification for statement: {statement[:50]}... (use_video={use_video})")

    # Verifier Agent
    ver = await async_verifier_agent(statement, sid)
    filters.append(FilterResult("Filter 1: Source Check",
                                FilterStatus.PASSED if validate_filter_result(ver, ["passed"]) and ver.get("passed") else FilterStatus.FAILED,
                                ver, ver.get("content", ""), time.time()))

    # Video Verifier - Only run if explicitly requested
    if use_video is True:
        logger.info("Running Video Verifier (use_video=True)")
        vid = await async_video_verifier(statement, sid)
        filters.append(FilterResult("Filter 2: Live Stream or Video Check",
                                    FilterStatus.PASSED if vid.get("passed") else FilterStatus.FAILED,
                                    vid, vid.get("content", vid.get("error","")), time.time()))
    else:
        logger.info("Skipping Video Verifier (use_video=False)")
        # Add skipped status for Video Verifier
        await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.SKIPPED, "Video analysis not requested")
        filters.append(FilterResult("Filter 2: Live Stream or Video Check", 
                                    FilterStatus.SKIPPED, 
                                    {"skipped": True}, 
                                    "Video analysis not requested", 
                                    time.time()))

    # Inference Points (was Reason Agent)
    reason = await async_reason_agent(statement, sid)
    filters.append(FilterResult("Filter 3.a: Inference Point",
                                FilterStatus.PASSED if validate_filter_result(reason, ["end_goal"])
                                else FilterStatus.FAILED,
                                reason, reason.get("end_goal", reason.get("error","")), time.time()))
    if "error" in reason:
        return VerificationResult(statement, filters, "Analysis Failed", "Reason agent failed")

    # Source Searching (was Online Data Agent)
    evidence = await async_online_data_agent(reason, sid)
    filters.append(FilterResult("Filter 3.b: Inference Evidence", 
                                FilterStatus.PASSED if validate_filter_result(evidence)
                                else FilterStatus.FAILED,
                                evidence, f"{len(evidence)} keys" if "error" not in evidence else evidence.get("error", ""),
                                time.time()))

    # Always call Decision Agent, even if Verifier Agent failed or evidence has error
    decision_input = {
        "verifier": ver,
        "evidence": evidence
    }
    decision = await async_decision_agent(statement, decision_input, sid)
    filters.append(FilterResult("Filter 3.c: Feasibility Check",
                                FilterStatus.PASSED if validate_filter_result(decision, ["decision", "reasoning"]) and 
                                decision.get("decision", "").strip().lower() == "not noise for investment" 
                                else FilterStatus.FAILED,
                                decision, decision.get("reasoning", decision.get("error","")), time.time()))

    # Extract reference links from evidence
    reference_links = []
    if isinstance(evidence, dict) and "error" not in evidence:
        for key, results in evidence.items():
            if isinstance(results, list):
                for r in results[:2]:  # Take top 2 results per key
                    if r.get("url"):
                        reference_links.append({
                            "reason": f"{key}: {r.get('title', '')}",
                            "url": r.get("url", "")
                        })

    return VerificationResult(
        statement       = statement,
        filters         = filters,
        final_decision  = decision.get("decision"),
        final_reasoning = decision.get("reasoning"),
        reference_links = reference_links
    )

# ─── 增强版主 pipeline (带用户ID跟踪) ─────────────────────────────────────────
async def verify_statement_with_user(statement: str, user_id: str, sid: str = None, use_video: bool = False) -> VerificationResult:
    """
    Enhanced verification function with user ID tracking and progress monitoring
    """
    if sid is None:
        sid = f"user_{user_id}_{int(time.time())}"
    
    # Initialize database connection
    db = NewsVerificationDB(user_id)
    
    # Initialize progress
    db.update_progress("starting verification", "started", 0, "Starting news verification process")
    
    filters: List[FilterResult] = []
    
    logger.info(f"Starting verification for user {user_id}: {statement[:50]}... (use_video={use_video})")

    # Filter 1: Source Check (0% → 30%)
    db.update_progress("source verification", "started", 10, "Verifying source credibility")
    ver = await async_verifier_agent(statement, sid)
    filters.append(FilterResult("Filter 1: Source Check",
                                FilterStatus.PASSED if validate_filter_result(ver, ["passed"]) and ver.get("passed") else FilterStatus.FAILED,
                                ver, ver.get("content", ""), time.time()))
    
    # Update progress based on Filter 1 result
    filter1_status = "completed" if filters[-1].status == FilterStatus.PASSED else "failed"
    db.update_progress("source verification", filter1_status, 30, 
                       f"Source verification {filter1_status}")

    # Filter 2: Video Verification (30% → 60%)
    if use_video is True:
        db.update_progress("video analysis", "started", 30, "Analyzing video content")
        vid = await async_video_verifier(statement, sid)
        filters.append(FilterResult("Filter 2: Live Stream or Video Check",
                                    FilterStatus.PASSED if vid.get("passed") else FilterStatus.FAILED,
                                    vid, vid.get("content", vid.get("error","")), time.time()))
        
        # Update progress based on Filter 2 result
        filter2_status = "completed" if filters[-1].status == FilterStatus.PASSED else "failed"
        db.update_progress("video analysis", filter2_status, 60, 
                           f"Video verification {filter2_status}")
    else:
        # Skip video verification
        await notify_progress(sid, "Filter 2: Live Stream or Video Check", FilterStatus.SKIPPED, "Video analysis not requested")
        filters.append(FilterResult("Filter 2: Live Stream or Video Check", 
                                    FilterStatus.SKIPPED, 
                                    {"skipped": True}, 
                                    "Video analysis not requested", 
                                    time.time()))
        
        # Jump to 60% since video is skipped
        db.update_progress("video analysis", "skipped", 60, "Video analysis not requested")

    # Filter 3a: Inference Point (60% → 70%)
    db.update_progress("inference analysis", "started", 60, "Analyzing market impact structure")
    reason = await async_reason_agent(statement, sid)
    filters.append(FilterResult("Filter 3.a: Inference Point",
                                FilterStatus.PASSED if validate_filter_result(reason, ["end_goal"])
                                else FilterStatus.FAILED,
                                reason, reason.get("end_goal", reason.get("error","")), time.time()))
    
    if "error" in reason:
        db.update_progress("inference analysis", "failed", 70, "Inference analysis failed")
        return VerificationResult(statement, filters, "Analysis Failed", "Reason agent failed")
    
    # Update progress for Filter 3a
    filter3a_status = "completed" if filters[-1].status == FilterStatus.PASSED else "failed"
    db.update_progress("inference analysis", filter3a_status, 70, 
                       f"Inference analysis {filter3a_status}")

    # Filter 3b: Inference Evidence (70% → 85%)
    db.update_progress("evidence gathering", "started", 70, "Gathering supporting evidence")
    evidence = await async_online_data_agent(reason, sid)
    filters.append(FilterResult("Filter 3.b: Inference Evidence", 
                                FilterStatus.PASSED if validate_filter_result(evidence)
                                else FilterStatus.FAILED,
                                evidence, f"{len(evidence)} keys" if "error" not in evidence else evidence.get("error", ""),
                                time.time()))
    
    # Update progress for Filter 3b
    filter3b_status = "completed" if filters[-1].status == FilterStatus.PASSED else "failed"
    db.update_progress("evidence gathering", filter3b_status, 85, 
                       f"Evidence gathering {filter3b_status}")

    # Filter 3c: Feasibility Check (85% → 100%)
    db.update_progress("final decision", "started", 85, "Making final decision")
    decision_input = {
        "verifier": ver,
        "evidence": evidence
    }
    decision = await async_decision_agent(statement, decision_input, sid)
    filters.append(FilterResult("Filter 3.c: Feasibility Check",
                                FilterStatus.PASSED if validate_filter_result(decision, ["decision", "reasoning"]) and 
                                decision.get("decision", "").strip().lower() == "not noise for investment" 
                                else FilterStatus.FAILED,
                                decision, decision.get("reasoning", decision.get("error","")), time.time()))

    # Update progress for Filter 3c
    filter3c_status = "completed" if filters[-1].status == FilterStatus.PASSED else "failed"
    db.update_progress("final decision", filter3c_status, 100, 
                       f"Final decision {filter3c_status}")

    # Extract reference links from evidence
    reference_links = []
    if isinstance(evidence, dict) and "error" not in evidence:
        for key, results in evidence.items():
            if isinstance(results, list):
                for r in results[:2]:  # Take top 2 results per key
                    if r.get("url"):
                        reference_links.append({
                            "reason": f"{key}: {r.get('title', '')}",
                            "url": r.get("url", "")
                        })

    # Create final result
    final_result = VerificationResult(
        statement       = statement,
        filters         = filters,
        final_decision  = decision.get("decision"),
        final_reasoning = decision.get("reasoning"),
        reference_links = reference_links
    )
    
    # Store result in database
    db.store_result(final_result)
    
    # Final progress update
    db.update_progress("verification complete", "completed", 100, 
                       f"Verification completed with decision: {final_result.final_decision}")
    
    return final_result

def get_current_week_range():
    today = datetime.date.today()
    start = today - datetime.timedelta(days=today.weekday())  # Monday
    end = start + datetime.timedelta(days=6)  # Sunday
    return start, end

async def run_verifier():
    statement = "Donald Trump said he loves Xi Jinping."
    sid = "test-session-001"  # Any string, used for progress callbacks
    result = await async_verifier_agent(statement, sid)
    print(result)

def ensure_dict(obj):
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            return {"error": "Output was not valid JSON", "raw": obj}
    return {"error": "Output was not a dict or JSON string", "raw": str(obj)}

def analyze_investment_context(statement: str, search_results: list) -> dict:
    """
    Smart context analysis for investment noise filtering
    Analyzes if multiple sources confirm the same EVENT exists
    """
    if not search_results:
        return {"context_match": False, "reason": "No search results available"}
    
    # Extract key entities from statement
    statement_lower = statement.lower()
    
    # Look for company names, tickers, time periods
    companies = []
    tickers = []
    time_periods = []
    
    # Common company patterns
    if "coinbase" in statement_lower:
        companies.append("coinbase")
        tickers.append("coin")
    if "apple" in statement_lower:
        companies.append("apple")
        tickers.append("aapl")
    if "tesla" in statement_lower:
        companies.append("tesla")
        tickers.append("tsla")
    
    # Time period patterns
    if "q2" in statement_lower or "second quarter" in statement_lower:
        time_periods.append("q2")
    if "2025" in statement_lower:
        time_periods.append("2025")
    
    # Financial metric patterns
    financial_metrics = []
    if "earnings" in statement_lower:
        financial_metrics.append("earnings")
    if "revenue" in statement_lower:
        financial_metrics.append("revenue")
    if "profit" in statement_lower:
        financial_metrics.append("profit")
    
    # Analyze search results for context matches
    context_matches = 0
    total_results = len(search_results)
    
    for result in search_results:
        if not isinstance(result, dict):
            continue
            
        content = (result.get('content', '') + ' ' + result.get('title', '')).lower()
        url = result.get('url', '').lower()
        
        # Check for company/ticker matches
        company_match = any(company in content or company in url for company in companies)
        ticker_match = any(ticker in content or ticker in url for ticker in tickers)
        
        # Check for time period matches
        time_match = any(period in content for period in time_periods)
        
        # Check for financial metric matches
        metric_match = any(metric in content for metric in financial_metrics)
        
        # If we have multiple context matches, this is likely the same event - MAKE MORE REASONABLE
        # Require company/ticker match AND either time period OR financial metric (not both)
        if (company_match or ticker_match) and (time_match or metric_match):
            context_matches += 1
    
    # Calculate context match percentage
    context_percentage = (context_matches / total_results) * 100 if total_results > 0 else 0
    
    # Determine if this is likely the same event - MAKE MORE STRICT
    is_same_event = context_percentage >= 50  # At least 50% of sources must discuss similar context
    
    return {
        "context_match": is_same_event,
        "context_percentage": context_percentage,
        "context_matches": context_matches,
        "total_results": total_results,
        "companies_found": companies,
        "tickers_found": tickers,
        "time_periods_found": time_periods,
        "financial_metrics_found": financial_metrics,
        "reason": f"Found {context_matches}/{total_results} sources with matching context ({context_percentage:.1f}%)"
    }

def validate_filter_result(result: dict, required_fields: list = None) -> bool:
    """Validate if a filter result is valid and should pass"""
    if not isinstance(result, dict):
        return False
    
    if "error" in result:
        return False
    
    if required_fields:
        for field in required_fields:
            if field not in result:
                return False
    
    return True

# ─── 测试函数 ─────────────────────────────────────────────────────
async def test_news_verification_with_user():
    """Test the enhanced verification system with user ID tracking"""
    
    # Test parameters
    test_statement = "Federal Reserve Powell indicates conditions, 'may warrant' interest rate cuts as Fed proceeds 'carefully'"
    test_user_id = "test_user_001"
    
    print("🚀 Testing News Verification with User ID Tracking...")
    print(f"📰 Statement: {test_statement}")
    print(f"👤 User ID: {test_user_id}")
    print("=" * 80)
    
    try:
        # Run verification with user tracking
        result = await verify_statement_with_user(
            statement=test_statement,
            user_id=test_user_id,
            use_video=False
        )
        
        print("\n✅ Verification Complete!")
        print("=" * 80)
        print(f"📊 Final Decision: {result.final_decision}")
        print(f"🧠 Final Reasoning: {result.final_reasoning}")
        print(f"🔗 Reference Links: {len(result.reference_links) if result.reference_links else 0}")
        
        # Show filter results
        print("\n🔍 Filter Results:")
        for filter_result in result.filters:
            status_emoji = "✅" if filter_result.status.value == "passed" else "❌" if filter_result.status.value == "failed" else "⏭️"
            print(f"{status_emoji} {filter_result.name}: {filter_result.status.value}")
            if filter_result.details:
                print(f"   Details: {filter_result.details[:100]}...")
        
        # Test database retrieval
        print("\n💾 Testing Database Retrieval...")
        db = NewsVerificationDB(test_user_id)
        
        # Get frontend progress (same format as other agents)
        frontend_progress = db.get_frontend_progress()
        print(f"📈 Frontend Progress Data: {frontend_progress}")
        
        # Get regular progress
        progress = db.get_progress()
        print(f"📊 Regular Progress Data: {progress}")
        
        stored_result = db.get_result()
        print(f"📊 Stored Result: {stored_result.get('final_decision', 'Not found')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        return None

if __name__ == "__main__":
    # Test the enhanced system
    asyncio.run(test_news_verification_with_user())