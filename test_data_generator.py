"""
Test Data Generator for Q&Q.AI System
======================================

Generates realistic test data for testing the Q&Q.AI pipeline without
needing live API calls or database access.

Usage:
    from test_data_generator import generate_test_data
    
    test_data = generate_test_data("AAPL")
    # Returns: brain, alpha, news_list, impact_chains, quant_data
"""

import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
import pandas as pd


def generate_test_brain(ticker: str) -> Dict[str, List[Dict]]:
    """Generate test brain with 4 layers"""
    
    macro_factors = [
        {
            "factor_name": "Federal Reserve Interest Rate Policy",
            "factor_description": "Fed maintains hawkish stance with rates at 5.25-5.50%",
            "impact": "negative",
            "confidence": 0.85
        },
        {
            "factor_name": "US GDP Growth Acceleration",
            "factor_description": "Q3 GDP growth exceeded expectations at 3.2%",
            "impact": "positive",
            "confidence": 0.78
        },
        {
            "factor_name": "Consumer Confidence Index Rising",
            "factor_description": "Consumer confidence reached 18-month high",
            "impact": "positive",
            "confidence": 0.82
        }
    ]
    
    sector_factors = [
        {
            "factor_name": "Retail Sector Digital Transformation",
            "factor_description": "E-commerce penetration accelerating across retail",
            "impact": "positive",
            "confidence": 0.75
        },
        {
            "factor_name": "Supply Chain Normalization",
            "factor_description": "Global supply chains returning to pre-pandemic efficiency",
            "impact": "positive",
            "confidence": 0.80
        }
    ]
    
    market_factors = [
        {
            "factor_name": f"{ticker} vs S&P 500 Beta",
            "factor_description": f"{ticker} showing lower volatility than market",
            "impact": "neutral",
            "confidence": 0.70
        },
        {
            "factor_name": "Sector Rotation Into Consumer Discretionary",
            "factor_description": "Institutional investors increasing exposure to consumer stocks",
            "impact": "positive",
            "confidence": 0.72
        }
    ]
    
    micro_factors = [
        {
            "factor_name": f"{ticker} Same-Store Sales Growth",
            "factor_description": "Comparable store sales up 4.2% YoY",
            "impact": "positive",
            "confidence": 0.88
        },
        {
            "factor_name": f"{ticker} Cost Reduction Initiative",
            "factor_description": "Company announced $500M cost savings program",
            "impact": "positive",
            "confidence": 0.90
        },
        {
            "factor_name": f"{ticker} Market Share Gains",
            "factor_description": "Gaining market share in key demographics",
            "impact": "positive",
            "confidence": 0.76
        }
    ]
    
    return {
        "Macro": macro_factors,
        "Sector": sector_factors,
        "Market": market_factors,
        "Micro": micro_factors
    }


def generate_test_alpha(ticker: str) -> List[Dict]:
    """Generate test alpha insights"""
    
    alpha_insights = [
        {
            "insight": f"{ticker} shows consistent alpha generation with daily excess return of 0.08%",
            "metric": "alpha_daily",
            "value": 0.0008,
            "confidence": 0.82
        },
        {
            "insight": f"Market beta of 1.15 indicates {ticker} amplifies market movements",
            "metric": "beta",
            "value": 1.15,
            "confidence": 0.90
        },
        {
            "insight": "Risk-adjusted returns (Sharpe ratio 1.4) exceed industry average",
            "metric": "sharpe_ratio",
            "value": 1.4,
            "confidence": 0.85
        }
    ]
    
    return alpha_insights


def generate_test_news(ticker: str, days: int = 7) -> List[Dict[str, str]]:
    """Generate realistic test news items"""
    
    news_templates = [
        {
            "title": f"{ticker} Reports Strong Q3 Earnings",
            "text": f"{ticker} announced third-quarter earnings that beat analyst expectations, with revenue up 8% YoY and EPS exceeding forecasts by $0.12. The company raised full-year guidance citing strong consumer demand.",
            "sentiment": "positive"
        },
        {
            "title": f"{ticker} Announces Cost Reduction Program",
            "text": f"{ticker} unveiled a comprehensive cost reduction initiative targeting $500 million in annual savings. The program includes workforce optimization and operational efficiency improvements.",
            "sentiment": "mixed"
        },
        {
            "title": f"{ticker} Faces Supply Chain Headwinds",
            "text": f"{ticker} warned investors about persistent supply chain challenges impacting inventory levels. Management expects these issues to pressure margins in the near term.",
            "sentiment": "negative"
        },
        {
            "title": f"{ticker} Launches New Product Line",
            "text": f"{ticker} introduced an innovative product line targeting millennial consumers. Early market reception has been positive with strong pre-order numbers.",
            "sentiment": "positive"
        },
        {
            "title": f"Analysts Upgrade {ticker} to Buy",
            "text": f"Major investment bank upgraded {ticker} from Hold to Buy, citing improved fundamentals and attractive valuation. Price target raised to $XX.",
            "sentiment": "positive"
        },
        {
            "title": f"{ticker} CEO Announces Succession Plan",
            "text": f"{ticker} announced a leadership transition with the current CEO stepping down next year. The board has identified internal and external candidates.",
            "sentiment": "neutral"
        },
        {
            "title": f"{ticker} Expands E-commerce Capabilities",
            "text": f"{ticker} invested $200M in digital infrastructure to enhance online shopping experience. The initiative includes AI-powered personalization and faster delivery options.",
            "sentiment": "positive"
        }
    ]
    
    news_list = []
    base_date = datetime.now()
    
    for i in range(min(days, len(news_templates))):
        template = news_templates[i]
        news_date = base_date - timedelta(days=i)
        
        news_list.append({
            "news": f"{template['title']}. {template['text']}",
            "date": news_date.strftime("%Y-%m-%d %H:%M:%S"),
            "link": f"https://example.com/news/{ticker.lower()}/{i+1}"
        })
    
    return news_list


def generate_test_impact_chains(
    news_list: List[Dict],
    brain: Dict,
    alpha: List
) -> List[Dict[str, Any]]:
    """Generate test impact chains"""
    
    impact_chains = []
    metrics = ["Revenue", "COGS", "Operating Expenses", "Gross Margin", "Net Income"]
    directions = ["Increase", "Decrease", "Neutral"]
    sentiments = ["Positive", "Negative", "Neutral"]
    
    for i, news_item in enumerate(news_list):
        news_text = news_item['news']
        
        # Determine sentiment based on keywords
        if any(word in news_text.lower() for word in ['strong', 'beat', 'exceed', 'raised', 'positive']):
            sentiment = "Positive"
            direction = random.choice(["Increase", "Increase", "Neutral"])
        elif any(word in news_text.lower() for word in ['warns', 'challenges', 'pressure', 'headwinds']):
            sentiment = "Negative"
            direction = random.choice(["Decrease", "Decrease", "Neutral"])
        else:
            sentiment = "Neutral"
            direction = "Neutral"
        
        metric = metrics[i % len(metrics)]
        
        impact_chains.append({
            "news_index": i + 1,
            "news_snippet": news_text[:100] + "..." if len(news_text) > 100 else news_text,
            "impact_chain": f"{news_item['news'][:50]}... → Market reaction → {metric} {direction.lower()}",
            "affected_metric": metric,
            "direction": direction,
            "sentiment": sentiment,
            "confidence": 0.65 + random.random() * 0.3,
            "expectation_reasoning": f"Historical patterns suggest {metric.lower()} will {direction.lower()} based on similar news",
            "think_count": random.randint(0, 2)
        })
    
    return impact_chains


def generate_test_quant_data(ticker: str) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Generate test quantitative data (macro_df, micro_df, factor_time_df)"""
    
    # Macro factors
    macro_data = {
        "factor": [
            "Federal Reserve Rate Hike",
            "US GDP Growth",
            "Consumer Confidence",
            "Trade Policy Changes"
        ],
        "final_impact": [-0.035, 0.042, 0.028, -0.015],
        "probability": [0.85, 0.78, 0.82, 0.65],
        "confidence": [0.90, 0.82, 0.85, 0.70]
    }
    macro_df = pd.DataFrame(macro_data)
    
    # Micro factors
    micro_data = {
        "factor": [
            f"{ticker} Same-Store Sales",
            f"{ticker} Cost Reduction",
            f"{ticker} Market Share Gains",
            f"{ticker} Digital Transformation"
        ],
        "final_impact": [0.055, 0.038, 0.025, 0.042],
        "probability": [0.88, 0.90, 0.76, 0.72],
        "confidence": [0.92, 0.88, 0.80, 0.75]
    }
    micro_df = pd.DataFrame(micro_data)
    
    # Factor time data
    factor_time_data = {
        "factor": macro_data["factor"] + micro_data["factor"],
        "period": ["Q3 2025"] * (len(macro_data["factor"]) + len(micro_data["factor"])),
        "duration_days": [90] * (len(macro_data["factor"]) + len(micro_data["factor"])),
        "scope": ["Global", "National", "National", "International"] + ["Company", "Company", "Industry", "Company"]
    }
    factor_time_df = pd.DataFrame(factor_time_data)
    
    return macro_df, micro_df, factor_time_df


def generate_test_data(
    ticker: str = "AAPL",
    news_days: int = 7
) -> Dict[str, Any]:
    """
    Generate complete test dataset for Q&Q.AI system
    
    Args:
        ticker: Stock ticker symbol
        news_days: Number of days of news to generate
    
    Returns:
        dict with keys: brain, alpha, news_list, impact_chains, 
                        macro_df, micro_df, factor_time_df
    """
    
    print(f"🎲 Generating test data for {ticker}...")
    
    # Generate all components
    brain = generate_test_brain(ticker)
    alpha = generate_test_alpha(ticker)
    news_list = generate_test_news(ticker, news_days)
    impact_chains = generate_test_impact_chains(news_list, brain, alpha)
    macro_df, micro_df, factor_time_df = generate_test_quant_data(ticker)
    
    print(f"   ✅ Generated:")
    print(f"      - Brain: {sum(len(v) for v in brain.values())} factors")
    print(f"      - Alpha: {len(alpha)} insights")
    print(f"      - News: {len(news_list)} items")
    print(f"      - Impact Chains: {len(impact_chains)}")
    print(f"      - Quant Data: {len(macro_df)} macro + {len(micro_df)} micro factors")
    
    return {
        "ticker": ticker,
        "brain": brain,
        "alpha": alpha,
        "news_list": news_list,
        "impact_chains": impact_chains,
        "macro_df": macro_df,
        "micro_df": micro_df,
        "factor_time_df": factor_time_df,
        "dates": [item['date'] for item in news_list],
        "links": [item['link'] for item in news_list]
    }


if __name__ == "__main__":
    # Demo usage
    print("=" * 80)
    print("TEST DATA GENERATOR DEMO")
    print("=" * 80)
    
    test_data = generate_test_data("TGT", news_days=5)
    
    print("\n📊 Sample Output:")
    print(f"\n1. Brain (Macro layer):")
    for factor in test_data['brain']['Macro'][:2]:
        print(f"   - {factor['factor_name']}: {factor['impact']} ({factor['confidence']})")
    
    print(f"\n2. News Items:")
    for news in test_data['news_list'][:3]:
        print(f"   - [{news['date']}] {news['news'][:80]}...")
    
    print(f"\n3. Impact Chains:")
    for chain in test_data['impact_chains'][:3]:
        print(f"   - {chain['affected_metric']} {chain['direction']} (confidence: {chain['confidence']:.2f})")
    
    print("\n✅ Test data generated successfully!")

