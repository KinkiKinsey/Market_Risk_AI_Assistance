#!/usr/bin/env python3
"""
FastAPI Server for Q&Q.AI Frontend - REAL DATA ONLY, NO MOCK
Handles API requests from Next.js frontend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import sys
import os
import asyncio
import importlib
import json
import time

# Add backend directory to path (all imports are now in same directory)
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# Import REAL functions - NO MOCK DATA
import fmp_news_fetcher
from hedge_fund_analyst_with_sentiment import analyze_news_impact

# For brain and quant, we'll import them only when needed to avoid path issues
# These will be imported dynamically in the request handlers

# Initialize FastAPI app
app = FastAPI(title="Q&Q.AI API Server")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function
def extract_news_text_date_link(news_list: List[Dict[str, str]]) -> tuple:
    """Extract news texts, dates, and links from news list"""
    news_texts = []
    dates = []
    links = []
    
    for item in news_list:
        news_texts.append(item.get('news', ''))
        dates.append(item.get('date', ''))
        links.append(item.get('link', ''))
    
    return news_texts, dates, links

# Request/Response Models
class NewsRequest(BaseModel):
    ticker: str
    days: int = 30

class NewsResponse(BaseModel):
    news: List[Dict[str, str]]
    dates: List[str]
    links: List[str]
    count: int

class ImpactRequest(BaseModel):
    ticker: str
    news_list: List[str]
    dates: List[str]
    links: List[str]
    
class TreemapData(BaseModel):
    factor: str
    impact: float
    abs_impact: float

class TreemapResponse(BaseModel):
    macro_data: List[TreemapData]
    micro_data: List[TreemapData]
    impact_chains: List[Dict[str, Any]]

# Cache for brain data
brain_cache = {}

# Helper functions to dynamically import and call real functions
async def get_brain_data(ticker):
    """Get brain data using real hedge fund brain"""
    try:
        # Dynamically import to avoid path issues
        from Source_File.Agent_Folder.Mid_Agent_Folder.Hedge_Fund_Brain import hedgefundbrain
        # Try to get shared_clients if available
        try:
            from shared_clients import shared_clients
            if not shared_clients._initialized:
                await shared_clients.initialize()
            brain, alpha = await hedgefundbrain(ticker, shared_clients=shared_clients)
        except ImportError:
            # Fallback if shared_clients not available
            brain, alpha = await hedgefundbrain(ticker, shared_clients=None)
        return brain, alpha
    except Exception as e:
        print(f"⚠️ Error getting brain: {e}")
        # Return minimal data structure as fallback
        return {}, []

async def get_quant_data(ticker):
    """Get quantitative data using real quant impact agent"""
    try:
        from Source_File.Agent_Folder.Sub_Agent_Folder.Quant_Impact_Agent.Quant_Impact_Incremental_Update import run_incremental_update
        # Try to get shared_clients if available
        try:
            from shared_clients import shared_clients
            if not shared_clients._initialized:
                await shared_clients.initialize()
            return await run_incremental_update(ticker, language="English", shared_clients=shared_clients)
        except ImportError:
            # Fallback - but Quant Impact requires shared_clients
            print(f"⚠️ Quant Impact requires shared_clients")
            return {}
    except Exception as e:
        print(f"⚠️ Error getting quant data: {e}")
        import traceback
        traceback.print_exc()
        return {}

# API Routes
@app.get("/")
async def root():
    """Health check endpoint"""
    return {"message": "Q&Q.AI API Server is running - REAL DATA ONLY"}

@app.post("/api/news", response_model=NewsResponse)
async def get_news(request: NewsRequest):
    """
    Get REAL news for a ticker from FMP API
    Limits to 10 items as requested
    """
    try:
        # Reload module to clear cache
        importlib.reload(fmp_news_fetcher)
        from fmp_news_fetcher import get_news
        
        # Fetch REAL news
        news_list = get_news(request.ticker, request.days)
        
        # Limit to 10 news items
        news_list = news_list[:10]
        
        # Extract texts, dates, and links
        news_texts, dates, links = extract_news_text_date_link(news_list)
        
        return NewsResponse(
            news=news_list,
            dates=dates,
            links=links,
            count=len(news_list)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze-impact")
async def analyze_impact(request: ImpactRequest):
    """
    Analyze news impact using REAL AI analysis
    """
    try:
        # Reload modules
        importlib.reload(fmp_news_fetcher)
        from hedge_fund_analyst_with_sentiment import analyze_news_impact
        
        # Get brain and alpha for the ticker (use cache if available)
        if request.ticker not in brain_cache:
            print(f"🧠 Getting brain for {request.ticker}...")
            brain, alpha = await get_brain_data(request.ticker)
            brain_cache[request.ticker] = (brain, alpha)
        else:
            print(f"✅ Using cached brain for {request.ticker}")
            brain, alpha = brain_cache[request.ticker]
        
        # Get REAL quantitative data
        print(f"📊 Getting quantitative data for {request.ticker}...")
        quant_result = await get_quant_data(request.ticker)
        
        macro_df = quant_result.get('macro_total_impact_df')
        micro_df = quant_result.get('micro_total_impact_df')
        
        # Analyze REAL impact chains
        print(f"🔍 Analyzing {len(request.news_list)} news items...")
        impact_chains = analyze_news_impact(brain, alpha, request.news_list)
        
        # Prepare treemap data from REAL quant data
        macro_data = []
        if macro_df is not None and not macro_df.empty:
            for _, row in macro_df.iterrows():
                macro_data.append({
                    "factor": row['factor'],
                    "impact": float(row['final_impact']),
                    "abs_impact": abs(float(row['final_impact']))
                })
        
        micro_data = []
        if micro_df is not None and not micro_df.empty:
            for _, row in micro_df.iterrows():
                micro_data.append({
                    "factor": row['factor'],
                    "impact": float(row['final_impact']),
                    "abs_impact": abs(float(row['final_impact']))
                })
        
        return {
            "impact_chains": impact_chains,
            "macro_data": macro_data,
            "micro_data": micro_data,
            "ticker": request.ticker
        }
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
        print(f"❌ Error: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)

@app.post("/api/custom-news-impact")
async def custom_news_impact(request: Dict[str, Any]):
    """
    Analyze custom market news using REAL AI
    """
    try:
        news_text = request.get('news_text', '')
        ticker = request.get('ticker', 'N/A')
        
        # Get brain and alpha
        if ticker not in brain_cache:
            brain, alpha = await get_brain_data(ticker)
            brain_cache[ticker] = (brain, alpha)
        else:
            brain, alpha = brain_cache[ticker]
        
        # Analyze single news item
        impact_chains = analyze_news_impact(brain, alpha, [news_text])
        
        # Get quantitative data
        quant_result = await get_quant_data(ticker)
        macro_df = quant_result.get('macro_total_impact_df')
        micro_df = quant_result.get('micro_total_impact_df')
        
        # Prepare data
        macro_data = []
        if macro_df is not None and not macro_df.empty:
            for _, row in macro_df.head(5).iterrows():  # Limit to 5 for custom
                macro_data.append({
                    "factor": row['factor'],
                    "impact": float(row['final_impact']),
                    "abs_impact": abs(float(row['final_impact']))
                })
        
        micro_data = []
        if micro_df is not None and not micro_df.empty:
            for _, row in micro_df.head(5).iterrows():
                micro_data.append({
                    "factor": row['factor'],
                    "impact": float(row['final_impact']),
                    "abs_impact": abs(float(row['final_impact']))
                })
        
        return {
            "impact_chains": impact_chains,
            "macro_data": macro_data,
            "micro_data": micro_data,
            "ticker": ticker
        }
    except Exception as e:
        import traceback
        error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_msg)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)