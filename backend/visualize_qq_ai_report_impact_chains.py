# Q&Q.AI Report with Impact Chains Visualization
# Updated to show News → Impact Chain → Financial Metrics
import webbrowser
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import pandas as pd

def visualize_qq_ai_report(
    ticker: str,
    impact_chains: List[Dict[str, Any]],  # Impact chains from analyst graph
    dates: Optional[List[str]] = None,  # ✅ NEW: List of dates for each news item
    links: Optional[List[str]] = None,  # ✅ NEW: List of URLs for each news item
    # Treemap parameters (unchanged)
    macro_df: Optional[pd.DataFrame] = None,
    micro_df: Optional[pd.DataFrame] = None,
    risk_reward_data: Optional[Any] = None,
    risk_share_index: Optional[Dict] = None,
    factor_time_df: Optional[pd.DataFrame] = None,
    language: str = "English"
):
    """
    Generate Q&Q.AI Report with Impact Chains + Quantitative Treemap
    
    Args:
        ticker: Stock ticker symbol
        impact_chains: List of impact chain dicts from analyze_news_impact()
        dates: List of date strings for each news item (optional)
        links: List of URL strings for each news item (optional)
        macro_df: Macro factors dataframe for treemap
        micro_df: Micro factors dataframe for treemap
        risk_reward_data: Risk/reward analysis data
        risk_share_index: Risk share index dict
        factor_time_df: Factor time intervals dataframe
        language: "English" or "Chinese"
    
    Each impact_chain should have:
        - news_index: int
        - news_snippet: str
        - impact_chain: str
        - affected_metric: str
        - direction: "Increase" | "Decrease" | "Neutral"
        - sentiment: "Positive" | "Negative" | "Neutral"
        - confidence: float (0-1)
        - expectation_reasoning: str
        - think_count: int
    
    If dates/links are provided, they will be aligned with impact_chains by index.
    """
    
    print("✅ Generating Q&Q.AI Report with Impact Chains...")
    
    # Generate dates
    analysis_date = datetime.now().strftime("%Y-%m-%d")
    report_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chain_count = len(impact_chains)
    
    # Language texts
    is_chinese = language.lower() == 'chinese'
    
    if is_chinese:
        texts = {
            "impact_chains_title": "新闻影响分析",
            "quantitative_title": "历史事件影响",
            "macro_factors": "宏观因素",
            "micro_factors": "微观因素",
            "positive_return": "正向收益",
            "negative_return": "负向收益",
            "risk_summary": "风险环境概览",
            "risk_analysis": "风险收益分析",
            "max_return": "最大收益",
            "min_return": "最小收益",
            "range": "收益区间",
            "sub_factors": "子因素:",
            "confidence_label": "置信度",
            "reasoning_label": "分析推理",
            "logo_description": "定量与定性AI投资分析系统"
        }
    else:
        texts = {
            "impact_chains_title": "News Impact Analysis",
            "quantitative_title": "Historical Events Impact",
            "macro_factors": "Macro Factors",
            "micro_factors": "Micro Factors",
            "positive_return": "Positive Return",
            "negative_return": "Negative Return",
            "risk_summary": "Risk Environment Summary",
            "risk_analysis": "Risk-Reward Analysis",
            "max_return": "Max Return",
            "min_return": "Min Return",
            "range": "Range",
            "sub_factors": "Sub-Factors:",
            "confidence_label": "Confidence",
            "reasoning_label": "Reasoning",
            "logo_description": "Quantitative & Qualitative AI Investment Analysis System"
        }
    
    texts_json = json.dumps(texts, ensure_ascii=False)
    
    # Generate Excel-style table rows HTML
    table_rows_html = ""
    news_data_json = []  # Store full news for modal
    csv_data = []  # Store data for CSV download
    
    for i, chain in enumerate(impact_chains):
        # Get sentiment-based color (GREEN = Positive, RED = Negative, GRAY = Neutral)
        sentiment = chain.get('sentiment', 'Neutral')
        if sentiment == 'Positive':
            sentiment_class = "sentiment-positive"
        elif sentiment == 'Negative':
            sentiment_class = "sentiment-negative"
        else:
            sentiment_class = "sentiment-neutral"
        
        # Get direction arrow
        direction = chain.get('direction', 'Neutral')
        if direction == 'Increase':
            direction_icon = "↑"
        elif direction == 'Decrease':
            direction_icon = "↓"
        else:
            direction_icon = "→"
        
        # Get data
        news_full = chain.get('news_snippet', 'No news')
        news_short = news_full[:80] + "..." if len(news_full) > 80 else news_full
        affected_metric = chain.get('affected_metric', 'Unknown')
        reasoning = chain.get('expectation_reasoning', 'No reasoning provided')
        news_index = chain.get('news_index', 0)
        
        # ✅ Use provided dates/links if available, otherwise fall back to chain data
        if dates and i < len(dates):
            news_date = dates[i]
        else:
            news_date = chain.get('date', 'N/A')
        
        if links and i < len(links):
            news_link = links[i]
        else:
            news_link = chain.get('link', '#')
        
        # Store full news for modal with date and link
        news_data_json.append({
            'index': news_index,
            'full_text': news_full,
            'date': news_date,
            'link': news_link
        })
        
        # Store data for CSV download
        csv_data.append({
            'date': news_date,
            'news': news_full,
            'financial_impact': f"{affected_metric} {direction_icon}",
            'reasoning': reasoning,
            'sentiment': sentiment,
            'confidence': chain.get('confidence', 0.0),
            'positive': 1 if sentiment == 'Positive' else 0,
            'negative': 1 if sentiment == 'Negative' else 0,
            'neutral': 1 if sentiment == 'Neutral' else 0,
            'url': news_link
        })
        
        table_rows_html += f"""
            <tr class="table-row" onclick="showNewsModal({news_index})">
                <td class="table-cell news-cell">
                    <div style="font-size: 0.75em; color: #6b7280; margin-bottom: 4px;">📅 {news_date}</div>
                    <div>{news_short}</div>
                </td>
                <td class="table-cell impact-cell {sentiment_class}">
                    <span class="impact-value">{affected_metric} {direction_icon}</span>
                </td>
                <td class="table-cell reasoning-cell">{reasoning}</td>
            </tr>
        """
    
    news_data_json_str = json.dumps(news_data_json)
    csv_data_json_str = json.dumps(csv_data)
    
    # Prepare treemap data (unchanged from original)
    has_treemap = macro_df is not None and micro_df is not None
    
    macro_data_json = "[]"
    micro_data_json = "[]"
    risk_data_json = "[]"
    risk_share_json = "{}"
    factor_time_json = "{}"
    
    if has_treemap:
        print("✅ Preparing treemap data...")
        
        # Prepare macro data
        macro_data = []
        for _, row in macro_df.iterrows():
            macro_data.append({
                'factor': row['factor'],
                'impact': float(row['final_impact']),
                'abs_impact': abs(float(row['final_impact']))
            })
        
        # Prepare micro data
        micro_data = []
        for _, row in micro_df.iterrows():
            micro_data.append({
                'factor': row['factor'],
                'impact': float(row['final_impact']),
                'abs_impact': abs(float(row['final_impact']))
            })
        
        # Prepare factor time data
        factor_time_data = {}
        if factor_time_df is not None and not factor_time_df.empty:
            for _, row in factor_time_df.iterrows():
                factor_name = row['factor_name']
                if factor_name not in factor_time_data:
                    factor_time_data[factor_name] = []
                factor_time_data[factor_name].append({
                    'start_date': str(row['start_date']),
                    'end_date': str(row['end_date']),
                    'time_interval': str(row['time_interval']),
                    'duration_days': int(row.get('duration_days', 0)),
                    'scope': str(row.get('scope', 'unknown'))
                })
            
            # Debug: Print what factor names we have
            print(f"   📅 Factor time data created for {len(factor_time_data)} factors")
            print(f"   📅 Sample factor names: {list(factor_time_data.keys())[:3]}")
            
            # Debug: Check if macro/micro factor names match
            if not macro_df.empty:
                macro_factors = set(macro_df['factor'].tolist())
                time_factors = set(factor_time_data.keys())
                unmatched = macro_factors - time_factors
                if unmatched:
                    print(f"   ⚠️ Macro factors NOT in time data: {list(unmatched)[:2]}")
            
            if not micro_df.empty:
                micro_factors = set(micro_df['factor'].tolist())
                time_factors = set(factor_time_data.keys())
                unmatched = micro_factors - time_factors
                if unmatched:
                    print(f"   ⚠️ Micro factors NOT in time data: {list(unmatched)[:2]}")
        
        # Convert to JSON
        macro_data_json = json.dumps(macro_data, ensure_ascii=False)
        micro_data_json = json.dumps(micro_data, ensure_ascii=False)
        
        # Handle risk_reward_data
        if risk_reward_data is not None:
            if hasattr(risk_reward_data, 'to_dict'):
                risk_data = risk_reward_data.to_dict('records')
            else:
                risk_data = risk_reward_data
            risk_data_json = json.dumps(risk_data, ensure_ascii=False, default=str)
        
        risk_share_json = json.dumps(risk_share_index if risk_share_index else {}, ensure_ascii=False)
        factor_time_json = json.dumps(factor_time_data, ensure_ascii=False)
        
        print(f"   - Macro factors: {len(macro_data)}")
        print(f"   - Micro factors: {len(micro_data)}")
    
    # Section title helper
    def get_section_title(title_text, is_quantitative=True):
        ring_class = "ring-quantitative" if is_quantitative else "ring-qualitative"
        return f"""
            <div class="section-title-with-ring">
                <div class="single-ring {ring_class}">
                    <div class="ring-glow"></div>
                </div>
                <div class="section-title-text">{title_text}</div>
            </div>
        """
    
    impact_chains_title_html = get_section_title(texts['impact_chains_title'], is_quantitative=False)
    quantitative_title_html = get_section_title(texts['quantitative_title'], is_quantitative=True)
    
    print("✅ Building HTML report...")
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q&Q.AI - Impact Chains Report</title>
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
            overflow-x: hidden;
        }}

        .main-container {{
            position: relative;
            z-index: 2;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }}

        /* Logo Section */
        .logo-section {{
            text-align: center;
            margin-bottom: 60px;
            padding: 60px 20px;
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

        .ticker-bar {{
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px 40px;
            margin-bottom: 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .ticker-symbol {{
            font-size: 2em;
            font-weight: 600;
            color: #667eea;
            text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
        }}

        .section {{
            margin-bottom: 60px;
        }}

        /* Section Title */
        .section-title-with-ring {{
            display: flex;
            align-items: center;
            gap: 15px;
            font-size: 2em;
            font-weight: 300;
            letter-spacing: 3px;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
            text-transform: uppercase;
        }}

        .single-ring {{
            width: 25px;
            height: 25px;
            border: 2px solid;
            border-radius: 50%;
            position: relative;
            animation: ring-pulse 2s ease-in-out infinite;
        }}

        .ring-quantitative {{
            border-color: #667eea;
            box-shadow: 0 0 15px rgba(102, 126, 234, 0.6);
        }}

        .ring-qualitative {{
            border-color: #764ba2;
            box-shadow: 0 0 15px rgba(118, 75, 162, 0.6);
        }}

        @keyframes ring-pulse {{
            0%, 100% {{ transform: scale(1); opacity: 0.8; }}
            50% {{ transform: scale(1.1); opacity: 1; }}
        }}

        .section-title-text {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        /* Impact Card Styles */
        .impact-card {{
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 25px 30px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
        }}

        .impact-card:hover {{
            background: rgba(255, 255, 255, 0.05);
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
        }}

        .impact-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 20px;
        }}

        .impact-title-section {{
            display: flex;
            align-items: center;
            gap: 15px;
            flex: 1;
        }}

        .impact-number {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            font-size: 1.2em;
            flex-shrink: 0;
        }}

        .impact-title {{
            font-size: 0.9em;
            font-weight: 500;
            color: #ffffff;
            line-height: 1.4;
            flex: 1;
        }}

        .impact-header-right {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .metric-badge {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 12px 20px;
            border-radius: 25px;
            font-weight: 700;
            font-size: 1.1em;
            border: 2px solid;
            white-space: nowrap;
        }}

        .metric-badge.increase {{
            background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(34, 197, 94, 0.1));
            color: #10b981;
            border-color: rgba(16, 185, 129, 0.4);
        }}

        .metric-badge.decrease {{
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
            color: #ef4444;
            border-color: rgba(239, 68, 68, 0.4);
        }}

        .metric-badge.neutral {{
            background: linear-gradient(135deg, rgba(160, 174, 192, 0.2), rgba(148, 163, 184, 0.1));
            color: #a0aec0;
            border-color: rgba(160, 174, 192, 0.4);
        }}

        .metric-arrow {{
            font-size: 1.5em;
            font-weight: bold;
        }}

        .expand-toggle {{
            font-size: 20px;
            color: #667eea;
            transition: all 0.3s ease;
            background: rgba(102, 126, 234, 0.1);
            padding: 8px 12px;
            border-radius: 50%;
        }}

        .expand-toggle.expanded {{
            transform: rotate(180deg);
        }}

        /* ========================================
           EXCEL-STYLE TABLE STYLES
           ======================================== */
        .excel-table-container {{
            background: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
            margin-top: 20px;
        }}

        .excel-table {{
            width: 100%;
            border-collapse: collapse;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            font-size: 14px;
        }}

        .table-header {{
            background: #e5e7eb;
            border-bottom: 2px solid #d1d5db;
        }}

        .header-cell {{
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            color: #1f2937;
            border-right: 1px solid #d1d5db;
        }}

        .header-cell:last-child {{
            border-right: none;
        }}

        .table-row {{
            border-bottom: 1px solid #e5e7eb;
            transition: background-color 0.15s ease;
            cursor: pointer;
        }}

        .table-row:hover {{
            background-color: #eff6ff;
        }}

        .table-cell {{
            padding: 12px 16px;
            color: #374151;
            border-right: 1px solid #e5e7eb;
            vertical-align: top;
        }}

        .table-cell:last-child {{
            border-right: none;
        }}

        .news-cell {{
            color: #2563eb;
            font-weight: 500;
            width: 40%;
        }}

        .news-cell:hover {{
            text-decoration: underline;
        }}

        .impact-cell {{
            width: 20%;
            text-align: center;
            font-weight: 600;
        }}

        /* Sentiment-based colors (GREEN = Positive, RED = Negative) */
        .impact-cell.sentiment-positive {{
            background: #f0fdf4;
            color: #16a34a;
        }}

        .impact-cell.sentiment-negative {{
            background: #fef2f2;
            color: #dc2626;
        }}

        .impact-cell.sentiment-neutral {{
            background: #f9fafb;
            color: #6b7280;
        }}

        .reasoning-cell {{
            width: 40%;
            color: #6b7280;
            line-height: 1.5;
        }}

        /* Download Button Styles */
        .download-btn {{
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
        }}

        .download-btn:hover {{
            background: linear-gradient(135deg, #2563eb, #1e40af);
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(59, 130, 246, 0.4);
        }}

        .download-btn:active {{
            transform: translateY(0);
            box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
        }}

        .impact-value {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}

        /* News Modal */
        .news-modal {{
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            z-index: 9999;
            align-items: center;
            justify-content: center;
        }}

        .news-modal.active {{
            display: flex;
        }}

        .news-modal-content {{
            background: #ffffff;
            border-radius: 16px;
            padding: 32px;
            max-width: 700px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
        }}

        .news-modal-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 20px;
        }}

        .news-modal-title {{
            font-size: 20px;
            font-weight: 600;
            color: #1f2937;
        }}

        .news-modal-close {{
            background: none;
            border: none;
            font-size: 32px;
            color: #9ca3af;
            cursor: pointer;
            line-height: 1;
        }}

        .news-modal-close:hover {{
            color: #6b7280;
        }}

        .news-modal-body {{
            color: #374151;
            line-height: 1.7;
            font-size: 15px;
        }}

        .impact-content {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease;
            margin-top: 0;
        }}

        .impact-content.expanded {{
            max-height: 1000px;
            margin-top: 25px;
        }}

        /* Chain Flow */
        .chain-flow {{
            display: flex;
            align-items: center;
            flex-wrap: wrap;
            gap: 15px;
            margin-bottom: 25px;
            padding: 20px;
            background: rgba(118, 75, 162, 0.05);
            border-radius: 15px;
            border: 1px solid rgba(118, 75, 162, 0.2);
        }}

        .step, .final-step {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 15px 20px;
            border-radius: 15px;
            background: rgba(102, 126, 234, 0.1);
            border: 2px solid rgba(102, 126, 234, 0.3);
            min-width: 150px;
            transition: all 0.3s ease;
        }}

        .step:hover, .final-step:hover {{
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(0,0,0,0.3);
            background: rgba(102, 126, 234, 0.2);
        }}

        .final-step {{
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.1));
            border-color: rgba(239, 68, 68, 0.4);
        }}

        .step-number {{
            background: rgba(0,0,0,0.3);
            width: 25px;
            height: 25px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.9em;
            flex-shrink: 0;
        }}

        .step-text {{
            flex: 1;
            font-size: 0.75em;
            color: #e2e8f0;
            line-height: 1.3;
        }}

        .arrow {{
            color: #667eea;
            font-size: 1.5em;
            font-weight: bold;
        }}

        /* Impact Details */
        .impact-details {{
            display: flex;
            flex-direction: column;
            gap: 20px;
        }}

        .detail-row {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.2);
            border-radius: 12px;
            border-left: 3px solid #667eea;
        }}

        .detail-label {{
            font-weight: 600;
            color: #667eea;
            min-width: 120px;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
        }}

        .confidence-bar-container {{
            flex: 1;
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .confidence-bar {{
            height: 25px;
            background: linear-gradient(90deg, #10b981, #059669);
            border-radius: 12px;
            transition: width 0.5s ease;
            box-shadow: 0 0 15px rgba(16, 185, 129, 0.5);
            position: relative;
        }}

        .confidence-text {{
            font-weight: 700;
            color: #10b981;
            font-size: 1.1em;
        }}

        .reasoning-text {{
            flex: 1;
            color: #cbd5e0;
            line-height: 1.6;
            font-size: 1em;
        }}

        /* Treemap styles (UNCHANGED - copied from original) */
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
            margin-bottom: 25px;
        }}
        
        /* Modal styles */
        .detail-modal {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 0;
            visibility: hidden;
            transition: all 0.3s ease;
        }}
        
        .detail-modal.show {{
            opacity: 1;
            visibility: visible;
        }}
        
        .modal-content {{
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid #667eea;
            border-radius: 16px;
            padding: 30px;
            max-width: 500px;
            width: 90%;
            text-align: center;
            transform: scale(0.8);
            transition: transform 0.3s ease;
        }}
        
        .detail-modal.show .modal-content {{
            transform: scale(1);
        }}
        
        .modal-close {{
            position: absolute;
            top: 10px;
            right: 15px;
            background: none;
            border: none;
            color: #fff;
            font-size: 24px;
            cursor: pointer;
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

        .legend {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 30px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 10px;
        }}

        .legend-color {{
            width: 25px;
            height: 25px;
            border-radius: 50%;
        }}

        .legend-color.positive {{
            background: linear-gradient(135deg, #10b981, #059669);
        }}

        .legend-color.negative {{
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }}

        /* Risk sections (keep for compatibility) */
        .risk-summary {{
            margin-top: 50px;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(102, 126, 234, 0.05);
            border-radius: 16px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            text-align: center;
        }}

        .footer {{
            text-align: center;
            padding: 40px 20px;
            margin-top: 80px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #a0aec0;
            font-size: 0.9em;
        }}

        @media (max-width: 768px) {{
            .impact-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            .chain-flow {{
                flex-direction: column;
            }}
        }}
    </style>
</head>
<body>
    <div class="main-container">
        <!-- Logo -->
        <div class="logo-section">
            <svg class="logo-svg" viewBox="0 0 360 150" xmlns="http://www.w3.org/2000/svg">
                <defs>
                    <linearGradient id="cleanGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" style="stop-color:#667eea;stop-opacity:1">
                            <animate attributeName="stop-color" values="#667eea;#764ba2;#667eea" dur="4s" repeatCount="indefinite"/>
                        </stop>
                        <stop offset="100%" style="stop-color:#764ba2;stop-opacity:1">
                            <animate attributeName="stop-color" values="#764ba2;#667eea;#764ba2" dur="4s" repeatCount="indefinite"/>
                        </stop>
                    </linearGradient>
                    <filter id="subtleGlow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
                        <feMerge><feMergeNode in="coloredBlur"/><feMergeNode in="SourceGraphic"/></feMerge>
                    </filter>
                </defs>
                <ellipse cx="150" cy="65" rx="50" ry="25" fill="none" stroke="url(#cleanGradient)" stroke-width="5" filter="url(#subtleGlow)" opacity="0.9">
                    <animate attributeName="opacity" values="0.9;1;0.9" dur="3s" repeatCount="indefinite"/>
                </ellipse>
                <ellipse cx="210" cy="85" rx="50" ry="25" fill="none" stroke="url(#cleanGradient)" stroke-width="5" filter="url(#subtleGlow)" opacity="0.9">
                    <animate attributeName="opacity" values="0.9;1;0.9" dur="3s" repeatCount="indefinite" begin="1.5s"/>
                </ellipse>
                <ellipse cx="180" cy="75" rx="20" ry="12" fill="url(#cleanGradient)" opacity="0.25" filter="url(#subtleGlow)">
                    <animate attributeName="opacity" values="0.25;0.4;0.25" dur="3s" repeatCount="indefinite"/>
                </ellipse>
            </svg>
            <div class="logo-text">Q&Q.AI</div>
            <div class="logo-description">{texts['logo_description']}</div>
        </div>

        <!-- Ticker Bar -->
        <div class="ticker-bar">
            <div class="ticker-symbol">{ticker}</div>
            <div>Analysis Date: {analysis_date}</div>
            <div>{chain_count} Impact Chains Analyzed</div>
        </div>

        <!-- Impact Chains Section -->
        <div class="section">
            {impact_chains_title_html}
            
            <!-- Download Button -->
            <div style="margin-bottom: 20px; text-align: right;">
                <button onclick="downloadCSV()" class="download-btn">
                    📥 Download CSV
                </button>
            </div>
            
            <!-- Excel-style Table -->
            <div class="excel-table-container">
                <table class="excel-table">
                    <thead>
                        <tr class="table-header">
                            <th class="header-cell">News</th>
                            <th class="header-cell">Financial Impact</th>
                            <th class="header-cell">Reasoning</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows_html}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Quantitative AI Section with TREEMAP -->
        <div class="section">
            {quantitative_title_html}
            
            <!-- Treemap Tabs -->
            <div class="tab-container">
                <button class="tab-button active" onclick="switchTab('macro')">{texts['macro_factors']}</button>
                <button class="tab-button" onclick="switchTab('micro')">{texts['micro_factors']}</button>
            </div>
            
            <!-- Treemap Container -->
            <div id="treemap" class="treemap-container"></div>
            
            <!-- Treemap Legend -->
            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color positive"></div>
                    <span>{texts['positive_return']}</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color negative"></div>
                    <span>{texts['negative_return']}</span>
                </div>
            </div>
        </div>

        <!-- Detail Modal -->
        <div id="detailModal" class="detail-modal">
            <div class="modal-content" id="modalContent">
                <!-- Content will be dynamically inserted -->
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Generated by Q&Q.AI - Quantitative & Qualitative AI Investment Analysis System</p>
            <p>Report generated on: {report_date_time}</p>
            <p>© 2025 Q&Q.AI - Bridging Data Intelligence</p>
        </div>
    </div>

    <!-- News Modal -->
    <div id="newsModal" class="news-modal">
        <div class="news-modal-content">
            <div class="news-modal-header">
                <h3 class="news-modal-title">Full News</h3>
                <button class="news-modal-close" onclick="closeNewsModal()">×</button>
            </div>
            <div id="newsModalBody" class="news-modal-body"></div>
        </div>
    </div>

    <script>
        // Data
        const ticker = "{ticker}";
        const macroData = {macro_data_json};
        const microData = {micro_data_json};
        const texts = {texts_json};
        const factorTimeData = {factor_time_json};
        const newsData = {news_data_json_str};
        const csvData = {csv_data_json_str};
        
        let currentData = macroData;
        
        // Create tooltip
        const tooltip = d3.select("body").append("div")
            .attr("class", "treemap-tooltip")
            .style("opacity", 0);

        // News Modal Functions
        function showNewsModal(newsIndex) {{
            const newsItem = newsData.find(item => item.index === newsIndex);
            if (newsItem) {{
                const modalBody = document.getElementById('newsModalBody');
                
                // Create modal content with date and clickable link
                modalBody.innerHTML = `
                    <div style="margin-bottom: 15px;">
                        <strong style="color: #3b82f6;">📅 Date:</strong> ${{newsItem.date || 'N/A'}}
                    </div>
                    <div style="margin-bottom: 15px; line-height: 1.6;">
                        ${{newsItem.full_text}}
                    </div>
                    <div style="margin-top: 20px; padding-top: 15px; border-top: 1px solid #e5e7eb;">
                        <a href="${{newsItem.link}}" target="_blank" rel="noopener noreferrer" 
                           style="color: #3b82f6; text-decoration: none; font-weight: 500; display: inline-flex; align-items: center; gap: 5px;">
                            🔗 Read Full Article
                            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                                <polyline points="15 3 21 3 21 9"></polyline>
                                <line x1="10" y1="14" x2="21" y2="3"></line>
                            </svg>
                        </a>
                    </div>
                `;
                
                document.getElementById('newsModal').classList.add('active');
            }}
        }}

        function closeNewsModal() {{
            document.getElementById('newsModal').classList.remove('active');
        }}

        // CSV Download Function
        function downloadCSV() {{
            console.log('Download CSV clicked');
            console.log('CSV Data:', csvData);
            
            if (!csvData || csvData.length === 0) {{
                alert('No data available for download');
                return;
            }}
            
            // Create CSV content
            const headers = ['date', 'news', 'financial_impact', 'reasoning', 'sentiment', 'confidence', 'positive', 'negative', 'neutral', 'url'];
            const csvContent = [
                headers.join(','),
                ...csvData.map(row => [
                    `"${{row.date || ''}}"`,
                    `"${{(row.news || '').replace(/"/g, '""')}}"`,
                    `"${{row.financial_impact || ''}}"`,
                    `"${{(row.reasoning || '').replace(/"/g, '""')}}"`,
                    `"${{row.sentiment || ''}}"`,
                    row.confidence || 0,
                    row.positive || 0,
                    row.negative || 0,
                    row.neutral || 0,
                    `"${{row.url || ''}}"`
                ].join(','))
            ].join('\\n');
            
            // Create and download file
            const blob = new Blob([csvContent], {{ type: 'text/csv;charset=utf-8;' }});
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', `${{ticker}}_news_impact_analysis.csv`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }}

        // Close modal when clicking outside
        document.getElementById('newsModal').addEventListener('click', function(e) {{
            if (e.target === this) {{
                closeNewsModal();
            }}
        }});

        // Toggle impact card (legacy, keeping for compatibility)
        function toggleImpactCard(card) {{
            const content = card.querySelector('.impact-content');
            const icon = card.querySelector('.expand-toggle');
            
            if (content.classList.contains('expanded')) {{
                content.classList.remove('expanded');
                icon.classList.remove('expanded');
            }} else {{
                content.classList.add('expanded');
                icon.classList.add('expanded');
            }}
        }}
        
        // Render treemap (UNCHANGED from original)
        function renderTreemap(data) {{
            const container = d3.select('#treemap');
            container.selectAll('*').remove();
            
            if (!data || data.length === 0) {{
                container.append('div')
                    .style('display', 'flex')
                    .style('align-items', 'center')
                    .style('justify-content', 'center')
                    .style('height', '100%')
                    .style('color', '#a0aec0')
                    .text('No data available');
                return;
            }}
            
            const width = container.node().offsetWidth;
            const height = 650;
            
            const treemap = d3.treemap()
                .size([width - 4, height - 4])
                .padding(2);
            
            const root = d3.hierarchy({{ children: data }})
                .sum(d => d.abs_impact)
                .sort((a, b) => b.value - a.value);
            
            treemap(root);
            
            const svg = container
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            const nodes = svg.selectAll('.node')
                .data(root.leaves())
                .enter().append('g')
                .attr('class', 'node')
                .attr('transform', d => `translate(${{d.x0}}, ${{d.y0}})`);
            
            // Simple clickable cards with fade animation
            nodes.append('rect')
                .attr('width', d => d.x1 - d.x0)
                .attr('height', d => d.y1 - d.y0)
                .style('fill', d => d.data.impact >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)')
                .style('stroke', '#fff')
                .style('stroke-width', 2)
                .style('cursor', 'pointer')
                .on('click', function(event, d) {{
                    // Show detailed modal
                    showDetailModal(d.data);
                }})
                .on('mouseover', function(event, d) {{
                    // Highlight effect
                    d3.select(this)
                        .transition()
                        .duration(200)
                        .style('stroke-width', 4)
                        .style('stroke', '#667eea')
                        .style('filter', 'brightness(1.2)');
                    
                    tooltip.transition()
                        .duration(200)
                        .style('opacity', 0.9);
                    tooltip.html(`
                        <strong>${{d.data.factor}}</strong><br/>
                        <span class="${{d.data.impact >= 0 ? 'return-rate' : 'negative-rate'}}">
                            Return Rate: ${{(d.data.impact * 100).toFixed(2)}}%
                        </span><br/>
                        <em>Click for detailed view</em>
                    `)
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 28) + 'px');
                }})
                .on('mouseout', function(d) {{
                    d3.select(this)
                        .transition()
                        .duration(200)
                        .style('stroke-width', 2)
                        .style('stroke', '#fff')
                        .style('filter', 'brightness(1)');
                    
                    tooltip.transition()
                        .duration(500)
                        .style('opacity', 0);
                }});
            
            // Add factor names with strict boundary control
            nodes.each(function(d) {{
                const rectWidth = d.x1 - d.x0;
                const rectHeight = d.y1 - d.y0;
                
                // Only add text if rectangle is large enough
                if (rectWidth < 60 || rectHeight < 30) {{
                    return; // Skip very small rectangles
                }}
                
                const text = d3.select(this).append('text')
                    .attr('x', 6)
                    .attr('y', 12)
                    .attr('text-anchor', 'start')
                    .style('fill', '#ffffff')
                    .style('font-size', '10px')
                    .style('font-weight', '900')
                    .style('text-shadow', '2px 2px 4px rgba(0,0,0,0.8)')
                    .style('overflow', 'hidden')
                    .style('white-space', 'nowrap');
                
                const words = d.data.factor.split(' ');
                const availableWidth = rectWidth - 12; // 6px margin on each side
                const lineHeight = 11;
                const maxLines = Math.floor((rectHeight - 12) / lineHeight); // 6px margin top/bottom
                
                let line = '';
                let lineNumber = 0;
                
                words.forEach(function(word) {{
                    const testLine = line + word + ' ';
                    const testWidth = testLine.length * 5.5; // Conservative character width estimate
                    
                    if (testWidth > availableWidth && lineNumber < maxLines - 1) {{
                        if (line.trim()) {{
                            text.append('tspan')
                                .attr('x', 6)
                                .attr('dy', lineNumber === 0 ? 0 : lineHeight)
                                .text(line.trim());
                            lineNumber++;
                        }}
                        line = word + ' ';
                    }} else {{
                        line = testLine;
                    }}
                }});
                
                // Add the last line if there's space
                if (line.trim() && lineNumber < maxLines) {{
                    text.append('tspan')
                        .attr('x', 6)
                        .attr('dy', lineNumber === 0 ? 0 : lineHeight)
                        .text(line.trim());
                }}
                
                // Add ellipsis if text was truncated
                if (words.length > 0 && lineNumber >= maxLines && line.trim()) {{
                    text.append('tspan')
                        .attr('x', 6)
                        .attr('dy', lineNumber === 0 ? 0 : lineHeight)
                        .text('...');
                }}
            }});
            
            // Add impact rates
            nodes.append('text')
                .attr('x', d => (d.x1 - d.x0) / 2)
                .attr('y', d => (d.y1 - d.y0) / 2)
                .attr('text-anchor', 'middle')
                .style('fill', '#ffffff')
                .style('font-size', '18px')
                .style('font-weight', '900')
                .style('text-shadow', '3px 3px 6px rgba(0,0,0,0.8)')
                .text(d => {{
                    const rate = (d.data.impact * 100).toFixed(1);
                    return `${{rate > 0 ? '+' : ''}}${{rate}}%`;
                }});
        }}
        
        function switchTab(tab) {{
            document.querySelectorAll('.tab-button').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');
            
            if (tab === 'macro') {{
                currentData = macroData;
            }} else if (tab === 'micro') {{
                currentData = microData;
            }}
            renderTreemap(currentData);
        }}
        
        // Modal functions  
        function showDetailModal(data) {{
            console.log('📊 Modal clicked for factor:', data.factor);
            
            const modal = document.getElementById('detailModal');
            const content = document.getElementById('modalContent');
            
            // Try exact match first
            let factorDates = factorTimeData[data.factor] || [];
            let allMatchedDates = [];
            
            if (factorDates.length === 0) {{
                // Smart keyword matching - extract key terms and find ALL matching factors
                const searchTerms = data.factor.toLowerCase()
                    .replace(/[0-9]+%/g, '')  // Remove percentages
                    .split(' ')
                    .filter(word => word.length > 3 && !['from', 'with', 'that', 'this'].includes(word));
                
                console.log('🔍 Search terms:', searchTerms);
                
                const factorKeys = Object.keys(factorTimeData);
                const matchingKeys = factorKeys.filter(key => {{
                    const keyLower = key.toLowerCase();
                    // Match if at least 2 search terms are found in the key
                    const matchCount = searchTerms.filter(term => keyLower.includes(term)).length;
                    return matchCount >= Math.min(2, searchTerms.length);
                }});
                
                console.log('✅ Matching keys found:', matchingKeys);
                
                // Collect ALL dates from ALL matching factors
                matchingKeys.forEach(key => {{
                    const dates = factorTimeData[key];
                    if (dates && dates.length > 0) {{
                        dates.forEach(dateInfo => {{
                            allMatchedDates.push({{
                                ...dateInfo,
                                source_factor: key
                            }});
                        }});
                    }}
                }});
                
                factorDates = allMatchedDates;
            }}
            
            console.log('📅 Final factor dates:', factorDates);
            
            let datesHtml = '';
            if (factorDates.length > 0) {{
                datesHtml = factorDates.map(interval => `
                    <div style="background: rgba(255,255,255,0.1); padding: 10px; margin: 5px 0; border-radius: 8px;">
                        ${{interval.source_factor ? `<div style="color: #667eea; font-size: 11px; margin-bottom: 5px;">🔗 ${{interval.source_factor}}</div>` : ''}}
                        <strong>Period:</strong> ${{interval.start_date}} to ${{interval.end_date}}<br/>
                        <strong>Duration:</strong> ${{interval.duration_days}} days<br/>
                        <strong>Scope:</strong> ${{interval.scope}}
                    </div>
                `).join('');
            }} else {{
                datesHtml = '<p style="color: #a0aec0;">No date information available for this factor.</p>';
                console.log('❌ No dates found for factor:', data.factor);
            }}
            
            content.innerHTML = `
                <button class="modal-close" onclick="closeModal()">&times;</button>
                <h3 style="color: #667eea; margin-bottom: 20px;">Factor Dates: ${{data.factor}}</h3>
                <div style="text-align: left; max-height: 400px; overflow-y: auto;">
                    ${{datesHtml}}
                </div>
            `;
            
            modal.classList.add('show');
            console.log('Modal should be showing now');
        }}
        
        function closeModal() {{
            document.getElementById('detailModal').classList.remove('show');
        }}
        
        // Close modal when clicking outside
        window.onclick = function(event) {{
            const modal = document.getElementById('detailModal');
            if (event.target === modal) {{
                closeModal();
            }}
        }}
        
        // Initialize
        if (macroData && macroData.length > 0) {{
            renderTreemap(macroData);
        }}
    </script>
</body>
</html>"""
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_filepath = f.name
    
    print(f"✅ Report generated: {temp_filepath}")
    print(f"📊 Opening in browser...")
    
    # Open in browser
    webbrowser.open(f"file://{temp_filepath}")
    
    print(f"✅ Report displayed!")
    print(f"💡 Structure: Impact Chains → Quantitative Analysis")
    
    return temp_filepath

