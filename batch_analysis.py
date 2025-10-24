"""
Batch Analysis Script for Multiple Tickers
===========================================

Analyze multiple tickers in batch and compare results.

Usage:
    python batch_analysis.py
    
    # Or import:
    from batch_analysis import batch_analyze
    results = batch_analyze(['AAPL', 'MSFT', 'GOOGL'])
"""

import os
import sys
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fmp_news_fetcher import get_news
from test_data_generator import generate_test_data


def batch_analyze(
    tickers: List[str],
    news_days: int = 7,
    use_test_data: bool = True,
    save_results: bool = True
) -> Dict[str, Any]:
    """
    Analyze multiple tickers in batch
    
    Args:
        tickers: List of ticker symbols
        news_days: Days of news to analyze
        use_test_data: Use test data instead of real API
        save_results: Save results to JSON file
    
    Returns:
        dict: Batch analysis results
    """
    
    print("=" * 80)
    print("📊 BATCH ANALYSIS - Q&Q.AI")
    print("=" * 80)
    print(f"🎯 Tickers: {', '.join(tickers)}")
    print(f"📰 News Days: {news_days}")
    print(f"🧪 Test Mode: {'ON' if use_test_data else 'OFF'}")
    print("=" * 80)
    
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'config': {
            'tickers': tickers,
            'news_days': news_days,
            'test_mode': use_test_data
        },
        'ticker_results': {}
    }
    
    for i, ticker in enumerate(tickers, 1):
        print(f"\n[{i}/{len(tickers)}] Analyzing {ticker}...")
        
        try:
            if use_test_data:
                # Use test data
                test_data = generate_test_data(ticker, news_days)
                news_count = len(test_data['news_list'])
                impact_count = len(test_data['impact_chains'])
                
                # Calculate sentiment scores
                positive = sum(1 for c in test_data['impact_chains'] if c['sentiment'] == 'Positive')
                negative = sum(1 for c in test_data['impact_chains'] if c['sentiment'] == 'Negative')
                neutral = impact_count - positive - negative
                
                avg_confidence = sum(c['confidence'] for c in test_data['impact_chains']) / impact_count if impact_count > 0 else 0
                
            else:
                # Use real data
                news_list = get_news(ticker, news_days)
                news_count = len(news_list)
                
                # Would need to run actual analysis here
                impact_count = 0
                positive = negative = neutral = 0
                avg_confidence = 0
            
            # Store results
            results['ticker_results'][ticker] = {
                'success': True,
                'news_count': news_count,
                'impact_count': impact_count,
                'sentiment': {
                    'positive': positive,
                    'negative': negative,
                    'neutral': neutral,
                    'sentiment_ratio': (positive - negative) / impact_count if impact_count > 0 else 0
                },
                'avg_confidence': avg_confidence
            }
            
            print(f"   ✅ Success: {news_count} news, {impact_count} impacts")
            print(f"      Sentiment: +{positive} / -{negative} / ={neutral}")
            print(f"      Avg Confidence: {avg_confidence:.3f}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            results['ticker_results'][ticker] = {
                'success': False,
                'error': str(e)
            }
    
    # Generate comparison summary
    print("\n" + "=" * 80)
    print("📊 BATCH ANALYSIS SUMMARY")
    print("=" * 80)
    
    comparison_df = create_comparison_table(results)
    print("\n" + comparison_df.to_string())
    
    # Save results
    if save_results:
        output_file = f"batch_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\n💾 Results saved to: {output_file}")
    
    return results


def create_comparison_table(results: Dict) -> pd.DataFrame:
    """Create comparison table from batch results"""
    
    rows = []
    for ticker, data in results['ticker_results'].items():
        if data['success']:
            rows.append({
                'Ticker': ticker,
                'News': data['news_count'],
                'Impacts': data['impact_count'],
                'Positive': data['sentiment']['positive'],
                'Negative': data['sentiment']['negative'],
                'Neutral': data['sentiment']['neutral'],
                'Sentiment Ratio': f"{data['sentiment']['sentiment_ratio']:+.2f}",
                'Avg Confidence': f"{data['avg_confidence']:.3f}"
            })
        else:
            rows.append({
                'Ticker': ticker,
                'News': 'ERROR',
                'Impacts': 'ERROR',
                'Positive': '-',
                'Negative': '-',
                'Neutral': '-',
                'Sentiment Ratio': '-',
                'Avg Confidence': '-'
            })
    
    return pd.DataFrame(rows)


def compare_tickers(
    tickers: List[str],
    metric: str = 'sentiment_ratio'
) -> pd.DataFrame:
    """
    Compare tickers by specific metric
    
    Args:
        tickers: List of tickers to compare
        metric: Metric to compare ('sentiment_ratio', 'avg_confidence', etc.)
    
    Returns:
        DataFrame with comparison
    """
    
    results = batch_analyze(tickers, use_test_data=True, save_results=False)
    
    comparison = []
    for ticker, data in results['ticker_results'].items():
        if data['success']:
            if metric == 'sentiment_ratio':
                value = data['sentiment']['sentiment_ratio']
            elif metric == 'avg_confidence':
                value = data['avg_confidence']
            elif metric == 'news_count':
                value = data['news_count']
            else:
                value = 0
            
            comparison.append({
                'Ticker': ticker,
                'Value': value
            })
    
    df = pd.DataFrame(comparison).sort_values('Value', ascending=False)
    
    print(f"\n🏆 Ranking by {metric}:")
    print("=" * 40)
    for i, row in enumerate(df.itertuples(), 1):
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        print(f"{emoji} {row.Ticker}: {row.Value:.3f}")
    
    return df


if __name__ == "__main__":
    # Demo: Analyze retail sector
    retail_tickers = ['TGT', 'WMT', 'COST', 'HD', 'LOW']
    
    print("\n🛒 Analyzing Retail Sector...")
    results = batch_analyze(retail_tickers, news_days=7, use_test_data=True)
    
    print("\n\n📈 Ranking by Sentiment...")
    compare_tickers(retail_tickers, metric='sentiment_ratio')
    
    print("\n\n🎯 Ranking by Confidence...")
    compare_tickers(retail_tickers, metric='avg_confidence')

