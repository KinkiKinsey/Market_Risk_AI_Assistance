"""
CSV Analyzer for Downloaded Q&Q.AI Reports
===========================================

Analyze the CSV files downloaded from Q&Q.AI reports.
Provides sentiment analysis, statistics, and insights.

Usage:
    from utilities.csv_analyzer import analyze_csv
    
    stats = analyze_csv('TGT_news_impact_analysis.csv')
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from pathlib import Path


def analyze_csv(csv_path: str) -> Dict[str, Any]:
    """
    Analyze Q&Q.AI CSV export
    
    Args:
        csv_path: Path to CSV file
    
    Returns:
        dict: Analysis results with statistics and insights
    """
    
    print(f"📊 Analyzing: {csv_path}")
    
    # Load CSV
    df = pd.read_csv(csv_path)
    
    # Basic statistics
    total_news = len(df)
    positive_count = df['positive'].sum()
    negative_count = df['negative'].sum()
    neutral_count = df['neutral'].sum()
    
    # Sentiment distribution
    sentiment_dist = {
        'positive': int(positive_count),
        'negative': int(negative_count),
        'neutral': int(neutral_count),
        'positive_pct': (positive_count / total_news * 100) if total_news > 0 else 0,
        'negative_pct': (negative_count / total_news * 100) if total_news > 0 else 0,
        'neutral_pct': (neutral_count / total_news * 100) if total_news > 0 else 0
    }
    
    # Confidence statistics
    confidence_stats = {
        'mean': df['confidence'].mean(),
        'median': df['confidence'].median(),
        'std': df['confidence'].std(),
        'min': df['confidence'].min(),
        'max': df['confidence'].max()
    }
    
    # Sentiment by metric
    metric_sentiment = df.groupby('sentiment')['financial_impact'].apply(list).to_dict()
    
    # Date range
    df['date'] = pd.to_datetime(df['date'])
    date_range = {
        'start': df['date'].min().strftime('%Y-%m-%d'),
        'end': df['date'].max().strftime('%Y-%m-%d'),
        'days': (df['date'].max() - df['date'].min()).days + 1
    }
    
    # High confidence insights (> 0.8)
    high_confidence = df[df['confidence'] > 0.8]
    
    # Sentiment score (weighted by confidence)
    sentiment_score = (
        (df['positive'] * df['confidence']).sum() -
        (df['negative'] * df['confidence']).sum()
    ) / df['confidence'].sum() if df['confidence'].sum() > 0 else 0
    
    results = {
        'total_news': total_news,
        'sentiment_distribution': sentiment_dist,
        'confidence_stats': confidence_stats,
        'date_range': date_range,
        'high_confidence_count': len(high_confidence),
        'sentiment_score': sentiment_score,
        'metric_sentiment': metric_sentiment
    }
    
    # Print summary
    print("\n" + "=" * 60)
    print("ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"\n📰 Total News Items: {total_news}")
    print(f"📅 Date Range: {date_range['start']} to {date_range['end']} ({date_range['days']} days)")
    print(f"\n💚 Positive: {positive_count} ({sentiment_dist['positive_pct']:.1f}%)")
    print(f"❤️  Negative: {negative_count} ({sentiment_dist['negative_pct']:.1f}%)")
    print(f"🤍 Neutral: {neutral_count} ({sentiment_dist['neutral_pct']:.1f}%)")
    print(f"\n🎯 Average Confidence: {confidence_stats['mean']:.3f}")
    print(f"🎯 High Confidence Items (>0.8): {len(high_confidence)}")
    print(f"\n📊 Overall Sentiment Score: {sentiment_score:.3f}")
    if sentiment_score > 0.2:
        print("   → Strongly Positive")
    elif sentiment_score > 0:
        print("   → Moderately Positive")
    elif sentiment_score > -0.2:
        print("   → Moderately Negative")
    else:
        print("   → Strongly Negative")
    
    return results


def get_top_impacts(csv_path: str, n: int = 5) -> pd.DataFrame:
    """Get top N news items by confidence"""
    df = pd.read_csv(csv_path)
    top = df.nlargest(n, 'confidence')[['date', 'news', 'financial_impact', 'sentiment', 'confidence']]
    
    print(f"\n🔝 Top {n} High-Confidence Impacts:")
    print("=" * 60)
    for idx, row in top.iterrows():
        print(f"\n{row['sentiment'].upper()} ({row['confidence']:.2f})")
        print(f"📰 {row['news'][:100]}...")
        print(f"💰 Impact: {row['financial_impact']}")
    
    return top


def sentiment_timeline(csv_path: str) -> pd.DataFrame:
    """Create sentiment timeline"""
    df = pd.read_csv(csv_path)
    df['date'] = pd.to_datetime(df['date'])
    
    # Group by date
    timeline = df.groupby(df['date'].dt.date).agg({
        'positive': 'sum',
        'negative': 'sum',
        'neutral': 'sum',
        'confidence': 'mean'
    }).reset_index()
    
    timeline['net_sentiment'] = timeline['positive'] - timeline['negative']
    
    print("\n📈 Sentiment Timeline:")
    print("=" * 60)
    for _, row in timeline.iterrows():
        date_str = str(row['date'])
        net = row['net_sentiment']
        emoji = "💚" if net > 0 else "❤️" if net < 0 else "🤍"
        print(f"{date_str}: {emoji} Net={net:+.0f} (Pos={row['positive']:.0f}, Neg={row['negative']:.0f}, Neu={row['neutral']:.0f})")
    
    return timeline


def export_summary(csv_path: str, output_path: str = None):
    """Export analysis summary to text file"""
    results = analyze_csv(csv_path)
    
    if output_path is None:
        output_path = csv_path.replace('.csv', '_summary.txt')
    
    with open(output_path, 'w') as f:
        f.write("Q&Q.AI NEWS IMPACT ANALYSIS SUMMARY\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total News Items: {results['total_news']}\n")
        f.write(f"Date Range: {results['date_range']['start']} to {results['date_range']['end']}\n\n")
        f.write("SENTIMENT DISTRIBUTION:\n")
        f.write(f"  Positive: {results['sentiment_distribution']['positive']} ({results['sentiment_distribution']['positive_pct']:.1f}%)\n")
        f.write(f"  Negative: {results['sentiment_distribution']['negative']} ({results['sentiment_distribution']['negative_pct']:.1f}%)\n")
        f.write(f"  Neutral: {results['sentiment_distribution']['neutral']} ({results['sentiment_distribution']['neutral_pct']:.1f}%)\n\n")
        f.write(f"Average Confidence: {results['confidence_stats']['mean']:.3f}\n")
        f.write(f"Overall Sentiment Score: {results['sentiment_score']:.3f}\n")
    
    print(f"\n✅ Summary exported to: {output_path}")


if __name__ == "__main__":
    # Demo with sample data
    print("CSV ANALYZER DEMO")
    print("=" * 60)
    print("\n📁 Looking for CSV files in current directory...")
    
    csv_files = list(Path('.').glob('*_news_impact_analysis.csv'))
    
    if csv_files:
        csv_path = str(csv_files[0])
        print(f"✅ Found: {csv_path}\n")
        
        # Run analysis
        results = analyze_csv(csv_path)
        
        # Show top impacts
        get_top_impacts(csv_path, n=3)
        
        # Show timeline
        sentiment_timeline(csv_path)
        
        # Export summary
        export_summary(csv_path)
    else:
        print("❌ No CSV files found. Export a report from Q&Q.AI first!")

