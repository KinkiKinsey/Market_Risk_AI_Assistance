"""
Q&Q.AI Complete Demo Workflow
==============================

This script demonstrates the complete end-to-end workflow of the Q&Q.AI system:
1. Fetch news from FMP API
2. Load Brain & Alpha (qualitative intelligence)
3. Analyze news impact with LangGraph
4. Generate quantitative metrics
5. Visualize complete report

Author: Q&Q.AI Team
Date: 2025-10-24
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import core modules
from fmp_news_fetcher import get_news
from visualize_qq_ai_report_impact_chains import visualize_qq_ai_report

# Import Brain & Alpha
sys.path.insert(0, os.path.join(os.getcwd(), 'Mid_Agent_Folder'))
from Hedge_Fund_Brain import hedgefundbrain

# Import Quant Impact Agent
from Sub_Agent_Folder.Quant_Impact_Agent.Quant_Impact_Incremental_Update import run_incremental_update


def demo_complete_analysis(
    ticker: str = "TGT",
    news_days: int = 2,
    language: str = "English",
    generate_report: bool = True
) -> Dict[str, Any]:
    """
    Run complete Q&Q.AI analysis pipeline
    
    Args:
        ticker: Stock ticker symbol
        news_days: Number of days of news to fetch
        language: "English" or "Chinese"
        generate_report: Whether to generate HTML report
    
    Returns:
        dict: Complete analysis results
    """
    
    print("=" * 80)
    print("🚀 Q&Q.AI COMPLETE ANALYSIS PIPELINE")
    print("=" * 80)
    print(f"📊 Ticker: {ticker}")
    print(f"📰 News Days: {news_days}")
    print(f"🌍 Language: {language}")
    print(f"📈 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    results = {}
    
    # =========================================================================
    # STEP 1: FETCH NEWS FROM FMP API
    # =========================================================================
    print("\n📰 STEP 1: Fetching news from FMP API...")
    try:
        news_list = get_news(ticker, news_days)
        news_texts = [item['news'] for item in news_list]
        dates = [item['date'] for item in news_list]
        links = [item['link'] for item in news_list]
        
        print(f"   ✅ Fetched {len(news_list)} news items")
        results['news_count'] = len(news_list)
        results['news_list'] = news_list
        results['news_texts'] = news_texts
        results['dates'] = dates
        results['links'] = links
    except Exception as e:
        print(f"   ❌ Error fetching news: {e}")
        return results
    
    # =========================================================================
    # STEP 2: LOAD BRAIN & ALPHA (QUALITATIVE INTELLIGENCE)
    # =========================================================================
    print("\n🧠 STEP 2: Loading Brain & Alpha (Qualitative Intelligence)...")
    try:
        brain_alpha_result = hedgefundbrain(
            ticker=ticker,
            language=language,
            force_refresh=False  # Use cache if available
        )
        
        brain = brain_alpha_result['brain']
        alpha = brain_alpha_result['alpha']
        
        print(f"   ✅ Brain loaded:")
        print(f"      - Macro: {len(brain.get('Macro', []))} factors")
        print(f"      - Sector: {len(brain.get('Sector', []))} factors")
        print(f"      - Market: {len(brain.get('Market', []))} factors")
        print(f"      - Micro: {len(brain.get('Micro', []))} factors")
        print(f"   ✅ Alpha loaded: {len(alpha)} insights")
        
        results['brain'] = brain
        results['alpha'] = alpha
    except Exception as e:
        print(f"   ❌ Error loading brain/alpha: {e}")
        # Create dummy brain/alpha for demo
        brain = {"Macro": [], "Sector": [], "Market": [], "Micro": []}
        alpha = []
        results['brain'] = brain
        results['alpha'] = alpha
    
    # =========================================================================
    # STEP 3: ANALYZE NEWS IMPACT WITH LANGGRAPH
    # =========================================================================
    print("\n🤖 STEP 3: Analyzing news impact with LangGraph...")
    try:
        # Import analyze_news_impact (assumes it's in notebook/imported)
        # For demo, we'll create dummy impact chains
        print("   ⚠️  Using demo impact chains (import analyze_news_impact for real analysis)")
        
        impact_chains = []
        for i, news in enumerate(news_texts[:5]):  # Limit to 5 for demo
            impact_chains.append({
                'news_index': i + 1,
                'news_snippet': news[:100] + "..." if len(news) > 100 else news,
                'impact_chain': f"News {i+1} → Market reaction → Financial impact",
                'affected_metric': ['Revenue', 'COGS', 'Operating Expenses', 'Gross Margin'][i % 4],
                'direction': ['Increase', 'Decrease', 'Neutral'][i % 3],
                'sentiment': ['Positive', 'Negative', 'Neutral'][i % 3],
                'confidence': 0.7 + (i * 0.05),
                'expectation_reasoning': f"Expected impact based on historical patterns for news type {i+1}",
                'think_count': 0
            })
        
        print(f"   ✅ Generated {len(impact_chains)} impact chains")
        results['impact_chains'] = impact_chains
    except Exception as e:
        print(f"   ❌ Error analyzing news: {e}")
        results['impact_chains'] = []
    
    # =========================================================================
    # STEP 4: GENERATE QUANTITATIVE METRICS
    # =========================================================================
    print("\n📊 STEP 4: Generating quantitative metrics...")
    try:
        quant_result = run_incremental_update(
            ticker=ticker,
            language=language,
            force_refresh=False
        )
        
        macro_df = quant_result.get('macro_total_impact_df')
        micro_df = quant_result.get('micro_total_impact_df')
        factor_time_df = quant_result.get('factor_time_df')
        risk_reward = quant_result.get('Factor_Risk_Reward')
        risk_share = quant_result.get('risk_share_index')
        
        print(f"   ✅ Quantitative metrics generated:")
        print(f"      - Macro factors: {len(macro_df) if macro_df is not None else 0}")
        print(f"      - Micro factors: {len(micro_df) if micro_df is not None else 0}")
        print(f"      - Factor time data: {len(factor_time_df) if factor_time_df is not None else 0}")
        
        results['macro_df'] = macro_df
        results['micro_df'] = micro_df
        results['factor_time_df'] = factor_time_df
        results['risk_reward'] = risk_reward
        results['risk_share'] = risk_share
    except Exception as e:
        print(f"   ❌ Error generating quant metrics: {e}")
        results['macro_df'] = None
        results['micro_df'] = None
        results['factor_time_df'] = None
        results['risk_reward'] = None
        results['risk_share'] = None
    
    # =========================================================================
    # STEP 5: VISUALIZE COMPLETE REPORT
    # =========================================================================
    if generate_report:
        print("\n🎨 STEP 5: Generating visualization report...")
        try:
            visualize_qq_ai_report(
                ticker=ticker,
                impact_chains=results['impact_chains'],
                dates=results['dates'],
                links=results['links'],
                macro_df=results.get('macro_df'),
                micro_df=results.get('micro_df'),
                risk_reward_data=results.get('risk_reward'),
                risk_share_index=results.get('risk_share'),
                factor_time_df=results.get('factor_time_df'),
                language=language
            )
            print("   ✅ Report generated and opened in browser")
        except Exception as e:
            print(f"   ❌ Error generating report: {e}")
    
    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📊 Summary:")
    print(f"   - News items analyzed: {results.get('news_count', 0)}")
    print(f"   - Impact chains generated: {len(results.get('impact_chains', []))}")
    print(f"   - Brain factors loaded: {sum(len(brain.get(k, [])) for k in brain.keys()) if 'brain' in results else 0}")
    print(f"   - Alpha insights: {len(results.get('alpha', []))}")
    print(f"   - Quantitative factors: {len(results.get('macro_df', [])) if results.get('macro_df') is not None else 0}")
    print("=" * 80)
    
    return results


def demo_news_only(ticker: str = "AAPL", days: int = 7):
    """Quick demo: Fetch and display news only"""
    print(f"\n📰 Fetching {days} days of news for {ticker}...")
    news_list = get_news(ticker, days)
    
    print(f"\n✅ Found {len(news_list)} news items:\n")
    for i, item in enumerate(news_list[:5], 1):
        print(f"{i}. [{item['date']}]")
        print(f"   {item['news'][:100]}...")
        print(f"   🔗 {item['link']}\n")
    
    return news_list


def demo_brain_only(ticker: str = "MSFT", language: str = "English"):
    """Quick demo: Load brain & alpha only"""
    print(f"\n🧠 Loading Brain & Alpha for {ticker}...")
    result = hedgefundbrain(ticker=ticker, language=language)
    
    brain = result['brain']
    alpha = result['alpha']
    
    print(f"\n✅ Brain Structure:")
    for layer, factors in brain.items():
        print(f"   {layer}: {len(factors)} factors")
        if factors:
            print(f"      Example: {factors[0].get('factor_name', 'N/A')}")
    
    print(f"\n✅ Alpha Insights: {len(alpha)}")
    for i, insight in enumerate(alpha[:2], 1):
        print(f"   {i}. {insight}")
    
    return result


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                  Q&Q.AI DEMO WORKFLOW                        ║
    ║          Quantitative & Qualitative AI Analysis              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Run complete analysis
    print("\n🎯 Running complete analysis demo...")
    results = demo_complete_analysis(
        ticker="TGT",
        news_days=2,
        language="English",
        generate_report=True
    )
    
    print("\n✅ Demo complete! Check your browser for the visualization.")
    print("\n💡 You can also run:")
    print("   - demo_news_only('AAPL', 7)  # Just fetch news")
    print("   - demo_brain_only('MSFT')     # Just load brain/alpha")

