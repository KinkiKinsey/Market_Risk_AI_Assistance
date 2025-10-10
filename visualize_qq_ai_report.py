# Q&Q.AI Complete Integrated Report with Full Treemap Features
# All-in-one React-style visualization with expandable sections
import webbrowser
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional
import json
import pandas as pd

def visualize_qq_ai_report(
    ticker: str,
    final_results: List[Dict[str, Any]],
    internet_search_result: Any,
    conclusion_result: Dict[str, Any],
    language: str = "English",
    # Treemap parameters
    macro_df: Optional[pd.DataFrame] = None,
    micro_df: Optional[pd.DataFrame] = None,
    risk_reward_data: Optional[Any] = None,
    risk_share_index: Optional[Dict] = None,
    factor_time_df: Optional[pd.DataFrame] = None
):
    """
    Generate Complete Q&Q.AI Report with Full Treemap Integration
    ALL features in ONE page with React-style expandable sections
    """
    
    # Process final_results to get chain data
    chain_data = []
    
    for i, result_item in enumerate(final_results):
        if result_item.get('status') == 'success':
            result_data = result_item.get('result', {})
            chain_info = result_data.get('chain_of_thought', {})
            nested_chain = chain_info.get('chain_of_thought', {})
            events = nested_chain.get('events', [])
            starting_event = events[0] if events else "Unknown starting event"
            
            chain_data.append({
                'index': i + 1,
                'query_key': result_item.get('query_key', f'Query {i+1}'),
                'direction': nested_chain.get('final_direction', 'Unknown'),
                'chain': nested_chain.get('impact_chain', 'Unknown'),
                'mermaid_code': chain_info.get('mermaid_code', ''),
                'starting_event': starting_event
            })
    
    print(f"✅ Extracted {len(chain_data)} chains from final_results")
    
    # Get data from internet_search_result
    sell_side_data = getattr(internet_search_result, 'sell_side_summary', [])
    buy_side_data = getattr(internet_search_result, 'buy_side_summary', [])
    business_logic_data = getattr(internet_search_result, 'business_logic', "No business logic available")
    
    # Get conclusion results
    catalyst = conclusion_result.get('Catalyst', 'Not available')
    short_term_impact = conclusion_result.get('short_term_impact', 'Not available')
    long_term_outlook = conclusion_result.get('long_term_outlook', 'Not available')
    
    # Prepare treemap data
    has_treemap = macro_df is not None and micro_df is not None
    
    macro_data_json = "[]"
    micro_data_json = "[]"
    risk_data_json = "[]"
    risk_share_json = "{}"
    factor_time_json = "{}"
    
    if has_treemap:
        print("✅ Preparing complete treemap data with all features...")
        
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
                    'start_date': row['start_date'],
                    'end_date': row['end_date'],
                    'time_interval': row['time_interval'],
                    'duration_days': int(row.get('duration_days', 0)),
                    'scope': row.get('scope', 'unknown')
                })
        
        # Convert to JSON
        macro_data_json = json.dumps(macro_data, ensure_ascii=False)
        micro_data_json = json.dumps(micro_data, ensure_ascii=False)
        
        # Handle risk_reward_data (could be DataFrame or dict)
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
        print(f"   - Risk data entries: {len(risk_data) if risk_reward_data is not None else 0}")
    
    # Convert lists to HTML paragraphs
    def list_to_paragraphs(items):
        if isinstance(items, list):
            return "".join([f"<p>{item}</p>\n" for item in items])
        else:
            return f"<p>{items}</p>\n"
    
    sell_side_html = list_to_paragraphs(sell_side_data)
    buy_side_html = list_to_paragraphs(buy_side_data)
    
    # Generate chain cards HTML with COLLAPSIBLE functionality
    chain_cards_html = ""
    for chain in chain_data:
        direction_class = "unknown"
        if "Short Term Up" in chain['direction']:
            direction_class = "short-term-up"
        elif "Short Term Down" in chain['direction']:
            direction_class = "short-term-down"
        elif "Long Term Up" in chain['direction']:
            direction_class = "long-term-up"
        elif "Long Term Down" in chain['direction']:
            direction_class = "long-term-down"
        
        chain_cards_html += f"""
            <div class="chain-card" onclick="toggleChainCard(this)">
                <div class="chain-header">
                    <div class="chain-title-wrapper">
                        <div class="chain-number">{chain['index']}</div>
                        <div class="chain-title">{chain['starting_event']}</div>
                    </div>
                    <div style="display: flex; align-items: center; gap: 15px;">
                        <span class="direction-badge {direction_class}">{chain['direction']}</span>
                        <span class="expand-icon">▼</span>
                    </div>
                </div>
                <div class="chain-content-collapsible">
                    <div class="chain-content">{chain['chain']}</div>
                    <div class="mermaid-wrapper">
                        <div class="mermaid">{chain['mermaid_code']}</div>
                    </div>
                </div>
            </div>
        """
    
    # Generate dates
    analysis_date = datetime.now().strftime("%Y-%m-%d")
    report_date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    chain_count = len(chain_data)
    
    # Language texts
    is_chinese = language.lower() == 'chinese'
    
    if is_chinese:
        texts = {
            "color_legend_title": "影响链方向说明",
            "long_term_up": "长期上涨",
            "long_term_down": "长期下跌",
            "short_term_up": "短期上涨",
            "short_term_down": "短期下跌",
            "impact_chains_title": "定性AI",
            "sell_buy_title": "买卖分析总结",
            "sell_side_title": "卖出分析",
            "buy_side_title": "买入分析",
            "business_logic_title": "商业逻辑总结",
            "quantitative_title": "定量AI",
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
            "conclusion_title": "结论",
            "key_catalysts": "关键催化剂",
            "short_term_impact": "短期影响",
            "long_term_outlook": "长期展望",
            "logo_description": "定量与定性AI投资分析系统"
        }
    else:
        texts = {
            "color_legend_title": "Impact Chain Direction Legend",
            "long_term_up": "Long Term Up",
            "long_term_down": "Long Term Down",
            "short_term_up": "Short Term Up",
            "short_term_down": "Short Term Down",
            "impact_chains_title": "Qualitative AI",
            "sell_buy_title": "Sell & Buy Analysis Summary",
            "sell_side_title": "Sell Side Analysis",
            "buy_side_title": "Buy Side Analysis",
            "business_logic_title": "Business Logic Summary",
            "quantitative_title": "Quantitative AI",
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
            "conclusion_title": "Conclusion",
            "key_catalysts": "Key Catalysts",
            "short_term_impact": "Short Term Impact",
            "long_term_outlook": "Long Term Outlook",
            "logo_description": "Quantitative & Qualitative AI Investment Analysis System"
        }
    
    texts_json = json.dumps(texts, ensure_ascii=False)
    
    # Color legend HTML
    color_legend_html = f"""
        <div class="color-legend">
            <h3 class="legend-title">{texts['color_legend_title']}</h3>
            <div class="legend-grid">
                <div class="legend-item">
                    <div class="legend-color long-term-up"></div>
                    <span class="legend-text">{texts['long_term_up']}</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color long-term-down"></div>
                    <span class="legend-text">{texts['long_term_down']}</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color short-term-up"></div>
                    <span class="legend-text">{texts['short_term_up']}</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color short-term-down"></div>
                    <span class="legend-text">{texts['short_term_down']}</span>
                </div>
            </div>
        </div>
    """
    
    # Section title with ring
    def get_section_title_with_ring(title_text, is_quantitative=True):
        ring_class = "ring-quantitative" if is_quantitative else "ring-qualitative"
        ring_glow_class = "ring-glow-quantitative" if is_quantitative else "ring-glow-qualitative"
        
        return f"""
            <div class="section-title-with-ring">
                <div class="single-ring {ring_class}">
                    <div class="ring-glow {ring_glow_class}"></div>
                </div>
                <div class="section-title-text">{title_text}</div>
            </div>
        """
    
    impact_chains_title_html = get_section_title_with_ring(texts['impact_chains_title'], is_quantitative=False)
    quantitative_title_html = get_section_title_with_ring(texts['quantitative_title'], is_quantitative=True)
    
    # Generate complete HTML (I'll write it in parts due to size)
    # Part 1: HTML head and styles will be in next message due to length
    
    print("✅ Generating complete integrated HTML report...")
    print("📊 Features included:")
    print("   - Collapsible impact chains")
    print("   - Interactive treemap with click handlers")
    print("   - Risk summary cards")
    print("   - Expandable risk analysis")
    print("   - Factor time interval modals")
    print("   - All animations and transitions")
    
    # Due to length, I'll create a complete integrated HTML file
    # Importing the full treemap CSS and JS
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q&Q.AI - Complete Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
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

        /* Single Ring Design */
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

        .ring-glow {{
            position: absolute;
            top: -2px;
            left: -2px;
            right: -2px;
            bottom: -2px;
            border-radius: 50%;
            opacity: 0.3;
            animation: ring-glow 3s ease-in-out infinite;
        }}

        .ring-glow-quantitative {{
            border: 1px solid #667eea;
            box-shadow: 0 0 20px rgba(102, 126, 234, 0.4);
        }}

        .ring-glow-qualitative {{
            border: 1px solid #764ba2;
            box-shadow: 0 0 20px rgba(118, 75, 162, 0.4);
        }}

        @keyframes ring-glow {{
            0%, 100% {{ opacity: 0.3; }}
            50% {{ opacity: 0.6; }}
        }}

        /* Section Titles */
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

        .section-title-text {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }}

        .section-title {{
            font-size: 2em;
            font-weight: 300;
            letter-spacing: 3px;
            margin-bottom: 30px;
            padding-bottom: 15px;
            border-bottom: 2px solid rgba(102, 126, 234, 0.3);
            text-transform: uppercase;
        }}

        /* Color Legend */
        .color-legend {{
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 40px;
        }}

        .legend-title {{
            font-size: 1.5em;
            font-weight: 400;
            margin-bottom: 20px;
            color: #667eea;
            text-align: center;
        }}

        .legend-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 15px;
            padding: 15px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
        }}

        .legend-color {{
            width: 30px;
            height: 30px;
            border-radius: 50%;
            flex-shrink: 0;
        }}

        .legend-color.long-term-up {{
            background: linear-gradient(135deg, #3498db, #5dade2);
        }}

        .legend-color.long-term-down {{
            background: linear-gradient(135deg, #e67e22, #f39c12);
        }}

        .legend-color.short-term-up {{
            background: linear-gradient(135deg, #27ae60, #2ecc71);
        }}

        .legend-color.short-term-down {{
            background: linear-gradient(135deg, #e74c3c, #c0392b);
        }}

        .legend-color.positive {{
            background: linear-gradient(135deg, #10b981, #059669);
        }}

        .legend-color.negative {{
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }}

        .legend-text {{
            font-weight: 500;
            font-size: 1.1em;
        }}

        /* COLLAPSIBLE Chain Cards */
        .chain-card {{
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px 30px;
            margin-bottom: 20px;
            transition: all 0.3s ease;
            cursor: pointer;
        }}

        .chain-card:hover {{
            background: rgba(255, 255, 255, 0.05);
            transform: translateY(-2px);
        }}

        .chain-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .chain-title-wrapper {{
            display: flex;
            align-items: center;
            gap: 15px;
        }}

        .chain-number {{
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

        .chain-title {{
            font-size: 1.1em;
            font-weight: 400;
            color: #ffffff;
            line-height: 1.4;
        }}

        .direction-badge {{
            padding: 8px 20px;
            border-radius: 30px;
            font-weight: 500;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 1px;
            white-space: nowrap;
        }}

        .direction-badge.short-term-up {{
            background: rgba(39, 174, 96, 0.2);
            color: #27ae60;
            border: 1px solid #27ae60;
        }}

        .direction-badge.short-term-down {{
            background: rgba(231, 76, 60, 0.2);
            color: #e74c3c;
            border: 1px solid #e74c3c;
        }}

        .direction-badge.long-term-up {{
            background: rgba(52, 152, 219, 0.2);
            color: #3498db;
            border: 1px solid #3498db;
        }}

        .direction-badge.long-term-down {{
            background: rgba(230, 126, 34, 0.2);
            color: #e67e22;
            border: 1px solid #e67e22;
        }}

        .expand-icon {{
            font-size: 18px;
            color: #667eea;
            transition: transform 0.3s ease;
        }}

        .expand-icon.expanded {{
            transform: rotate(180deg);
        }}

        .chain-content-collapsible {{
            max-height: 0;
            overflow: hidden;
            transition: max-height 0.5s ease;
        }}

        .chain-content-collapsible.expanded {{
            max-height: 3000px;
            padding-top: 20px;
        }}

        .chain-content {{
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            font-size: 0.95em;
            line-height: 1.6;
            color: #cbd5e0;
        }}

        .mermaid-wrapper {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 20px;
            overflow-x: auto;
        }}

        /* Sell/Buy Cards */
        .summary-card {{
            background: rgba(255, 255, 255, 0.03);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 30px;
        }}

        .summary-content {{
            font-size: 1.1em;
            line-height: 1.8;
            color: #cbd5e0;
        }}

        .summary-content p {{
            margin-bottom: 15px;
        }}

        .sell-buy-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-bottom: 30px;
        }}

        .sell-side-card {{
            background: rgba(231, 76, 60, 0.05);
            border: 1px solid rgba(231, 76, 60, 0.2);
            border-radius: 20px;
            padding: 30px;
        }}

        .buy-side-card {{
            background: rgba(39, 174, 96, 0.05);
            border: 1px solid rgba(39, 174, 96, 0.2);
            border-radius: 20px;
            padding: 30px;
        }}

        .side-title {{
            font-size: 1.3em;
            font-weight: 600;
            margin-bottom: 20px;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 2px;
        }}

        .sell-side-title {{
            color: #e74c3c;
        }}

        .buy-side-title {{
            color: #27ae60;
        }}

        .side-content {{
            font-size: 1em;
            line-height: 1.7;
            color: #cbd5e0;
        }}

        .side-content p {{
            margin-bottom: 12px;
        }}

        /* TREEMAP STYLES */
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

        /* Risk Summary Section */
        .risk-summary {{
            margin-top: 50px;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(102, 126, 234, 0.05);
            border-radius: 16px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            text-align: center;
        }}
        
        .risk-summary-title {{
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 20px;
            text-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
        }}
        
        .risk-summary-content {{
            display: flex;
            justify-content: space-around;
            align-items: center;
            gap: 30px;
        }}
        
        .risk-share-item {{
            flex: 1;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }}
        
        .risk-share-item:hover {{
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }}
        
        .risk-share-label {{
            font-size: 14px;
            color: #a0aec0;
            margin-bottom: 10px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .risk-share-value {{
            font-size: 28px;
            font-weight: 700;
            color: #667eea;
            text-shadow: 0 0 15px rgba(102, 126, 234, 0.6);
        }}
        
        .risk-environment-text {{
            font-size: 16px;
            color: #ffffff;
            margin-top: 20px;
            font-style: italic;
            opacity: 0.8;
        }}

        /* Risk Analysis Section */
        .risk-section {{
            margin-top: 60px;
            padding-top: 40px;
            border-top: 2px solid rgba(255, 255, 255, 0.1);
        }}
        
        .risk-title {{
            font-size: 32px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 40px;
            color: #ffffff;
            text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
        }}
        
        .risk-category-section {{
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            overflow: hidden;
        }}
        
        .risk-category-header {{
            background: rgba(102, 126, 234, 0.1);
            padding: 20px 30px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .risk-category-header:hover {{
            background: rgba(102, 126, 234, 0.2);
        }}
        
        .risk-category-title {{
            font-size: 20px;
            font-weight: 600;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        
        .risk-category-count {{
            background: rgba(102, 126, 234, 0.3);
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }}
        
        .risk-category-content {{
            padding: 0 30px;
            max-height: 0;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        
        .risk-category-content.expanded {{
            max-height: 2000px;
            padding: 30px;
        }}
        
        .factor-card {{
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .factor-card:hover {{
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }}
        
        .factor-card.expanded {{
            background: rgba(102, 126, 234, 0.1);
            border-color: rgba(102, 126, 234, 0.3);
        }}
        
        .factor-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }}
        
        .factor-name {{
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
            flex: 1;
        }}
        
        .expand-factor-icon {{
            font-size: 14px;
            color: #667eea;
            transition: transform 0.3s ease;
            margin-left: 15px;
        }}
        
        .expand-factor-icon.expanded {{
            transform: rotate(90deg);
        }}
        
        .factor-metrics {{
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 15px;
        }}
        
        .metric {{
            flex: 1;
            text-align: center;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        
        .metric-label {{
            font-size: 11px;
            color: #a0aec0;
            margin-bottom: 8px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .metric-value {{
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }}
        
        .positive-value {{
            color: #10b981;
            text-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
        }}
        
        .negative-value {{
            color: #ef4444;
            text-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
        }}
        
        .sub-factors-container {{
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            max-height: 0;
            overflow: hidden;
            transition: all 0.3s ease;
        }}
        
        .sub-factors-container.expanded {{
            max-height: 500px;
        }}
        
        .sub-factors-title {{
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .sub-factors-list {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        
        .sub-factor-tag {{
            background: rgba(102, 126, 234, 0.2);
            color: #667eea;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 10px;
            font-weight: 500;
            border: 1px solid rgba(102, 126, 234, 0.3);
        }}

        /* Conclusion Cards */
        .conclusion-card {{
            background: rgba(102, 126, 234, 0.1);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 20px;
            padding: 30px;
            margin-bottom: 20px;
        }}

        .conclusion-title {{
            font-size: 1.3em;
            margin-bottom: 15px;
            color: #667eea;
            font-weight: 500;
        }}

        .conclusion-text {{
            line-height: 1.7;
            color: #cbd5e0;
        }}

        .footer {{
            text-align: center;
            padding: 40px 20px;
            margin-top: 80px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            color: #a0aec0;
            font-size: 0.9em;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .sell-buy-container {{
                grid-template-columns: 1fr;
            }}
            .risk-summary-content {{
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

        <!-- Color Legend -->
        {color_legend_html}

        <!-- Qualitative AI Section -->
        <div class="section">
            {impact_chains_title_html}
            {chain_cards_html}
        </div>

        <!-- Sell/Buy Analysis -->
        <div class="section">
            <h2 class="section-title">{texts['sell_buy_title']}</h2>
            <div class="sell-buy-container">
                <div class="sell-side-card">
                    <h3 class="side-title sell-side-title">{texts['sell_side_title']}</h3>
                    <div class="side-content">{sell_side_html}</div>
                </div>
                <div class="buy-side-card">
                    <h3 class="side-title buy-side-title">{texts['buy_side_title']}</h3>
                    <div class="side-content">{buy_side_html}</div>
                </div>
            </div>
        </div>

        <!-- Business Logic -->
        <div class="section">
            <h2 class="section-title">{texts['business_logic_title']}</h2>
            <div class="summary-card">
                <div class="summary-content"><p>{business_logic_data}</p></div>
            </div>
        </div>

        <!-- Quantitative AI Section with FULL TREEMAP -->
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
            
            <!-- Risk Summary -->
            <div class="risk-summary" id="riskSummarySection" style="display: none;">
                <div class="risk-summary-title">{texts['risk_summary']}</div>
                <div class="risk-summary-content" id="riskSummaryContent"></div>
                <div class="risk-environment-text" id="riskEnvironmentText"></div>
            </div>
            
            <!-- Risk Analysis -->
            <div class="risk-section">
                <h2 class="risk-title">{texts['risk_analysis']}</h2>
                <div id="riskCategoryContainer"></div>
            </div>
        </div>

        <!-- Conclusion -->
        <div class="section">
            <h2 class="section-title">{texts['conclusion_title']}</h2>
            <div class="conclusion-card">
                <h3 class="conclusion-title">{texts['key_catalysts']}</h3>
                <div class="conclusion-text">{catalyst}</div>
            </div>
            <div class="conclusion-card">
                <h3 class="conclusion-title">{texts['short_term_impact']}</h3>
                <div class="conclusion-text">{short_term_impact}</div>
            </div>
            <div class="conclusion-card">
                <h3 class="conclusion-title">{texts['long_term_outlook']}</h3>
                <div class="conclusion-text">{long_term_outlook}</div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            <p>Generated by Q&Q.AI - Quantitative & Qualitative AI Investment Analysis System</p>
            <p>Report generated on: {report_date_time}</p>
            <p>© 2025 Q&Q.AI - Bridging Data Intelligence</p>
        </div>
    </div>

    <script>
        // Initialize Mermaid
        mermaid.initialize({{
            startOnLoad: true,
            theme: 'dark',
            themeVariables: {{
                primaryColor: '#667eea',
                primaryTextColor: '#fff',
                primaryBorderColor: '#764ba2',
                lineColor: '#667eea',
                secondaryColor: '#764ba2',
                fontFamily: 'Segoe UI',
                fontSize: '14px'
            }},
            flowchart: {{
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }}
        }});

        // Data
        const macroData = {macro_data_json};
        const microData = {micro_data_json};
        const Factor_Risk_Reward = {risk_data_json};
        const RiskShareIndex = {risk_share_json};
        const FactorTimeData = {factor_time_json};
        const texts = {texts_json};
        
        let currentData = macroData;
        
        // Create tooltip
        const tooltip = d3.select("body").append("div")
            .attr("class", "treemap-tooltip")
            .style("opacity", 0);

        // Toggle chain card
        function toggleChainCard(card) {{
            const content = card.querySelector('.chain-content-collapsible');
            const icon = card.querySelector('.expand-icon');
            
            if (content.classList.contains('expanded')) {{
                content.classList.remove('expanded');
                icon.classList.remove('expanded');
            }} else {{
                content.classList.add('expanded');
                icon.classList.add('expanded');
            }}
        }}
        
        // Wrap text
        function wrapText(text, width, fontSize) {{
            const words = text.split(' ');
            const lines = [];
            let currentLine = words[0] || '';
            
            for (let i = 1; i < words.length; i++) {{
                const word = words[i];
                const testLine = currentLine + ' ' + word;
                const testWidth = testLine.length * fontSize * 0.6;
                
                if (testWidth < width) {{
                    currentLine = testLine;
                }} else {{
                    lines.push(currentLine);
                    currentLine = word;
                }}
            }}
            if (currentLine) lines.push(currentLine);
            return lines;
        }}
        
        // Render treemap
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
            
            nodes.append('rect')
                .attr('width', d => d.x1 - d.x0)
                .attr('height', d => d.y1 - d.y0)
                .style('fill', d => d.data.impact >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)')
                .style('stroke', '#fff')
                .style('stroke-width', 2)
                .style('cursor', 'pointer')
                .on('click', function(event, d) {{
                    toggleFactorCard(d.data.factor);
                }})
                .on('mouseover', function(event, d) {{
                    tooltip.transition()
                        .duration(200)
                        .style('opacity', 0.9);
                    tooltip.html(`
                        <strong>${{d.data.factor}}</strong><br/>
                        <span class="${{d.data.impact >= 0 ? 'return-rate' : 'negative-rate'}}">
                            Return Rate: ${{(d.data.impact * 100).toFixed(2)}}%
                        </span><br/>
                        <small>Click to view time intervals</small>
                    `)
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 28) + 'px');
                }})
                .on('mouseout', function(d) {{
                    tooltip.transition()
                        .duration(500)
                        .style('opacity', 0);
                }});
            
            const impacts = data.map(d => d.abs_impact);
            const maxImpact = Math.max(...impacts);
            const minImpact = Math.min(...impacts);
            const impactRange = maxImpact - minImpact;
            
            // Add factor names with wrapping
            nodes.each(function(d) {{
                const node = d3.select(this);
                const rectWidth = d.x1 - d.x0 - 12;
                const normalizedImpact = impactRange > 0 ? (d.data.abs_impact - minImpact) / impactRange : 0;
                const eventFontSize = 12 + (normalizedImpact * 10);
                const lines = wrapText(d.data.factor, rectWidth, eventFontSize);
                const lineHeight = eventFontSize * 1.2;
                
                lines.forEach((line, i) => {{
                    node.append('text')
                        .attr('x', 8)
                        .attr('y', 20 + (i * lineHeight))
                        .attr('text-anchor', 'start')
                        .style('fill', '#ffffff')
                        .style('font-size', eventFontSize + 'px')
                        .style('font-weight', '900')
                        .style('text-shadow', '2px 2px 4px rgba(0,0,0,0.8)')
                        .text(line);
                }});
            }});
            
            // Add impact rates
            nodes.append('text')
                .attr('x', d => (d.x1 - d.x0) / 2)
                .attr('y', d => (d.y1 - d.y0) / 2)
                .attr('text-anchor', 'middle')
                .style('fill', '#ffffff')
                .style('font-size', d => {{
                    const normalizedImpact = impactRange > 0 ? (d.data.abs_impact - minImpact) / impactRange : 0;
                    return (18 + normalizedImpact * 18) + 'px';
                }})
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
        
        // Risk Share Summary
        function createRiskSummary() {{
            if (!RiskShareIndex || Object.keys(RiskShareIndex).length === 0) {{
                document.getElementById('riskSummarySection').style.display = 'none';
                return;
            }}
            
            const riskSummarySection = document.getElementById('riskSummarySection');
            const riskSummaryContent = document.getElementById('riskSummaryContent');
            const riskEnvironmentText = document.getElementById('riskEnvironmentText');
            
            riskSummarySection.style.display = 'block';
            riskSummaryContent.innerHTML = '';
            
            const macroShare = RiskShareIndex.macro_risk_share || 0;
            const microShare = RiskShareIndex.micro_risk_share || 0;
            const riskEnvironment = RiskShareIndex.risk_environment || '';
            
            const macroItem = document.createElement('div');
            macroItem.className = 'risk-share-item';
            macroItem.innerHTML = `
                <div class="risk-share-label">Macro Risk</div>
                <div class="risk-share-value">${{macroShare.toFixed(1)}}%</div>
            `;
            riskSummaryContent.appendChild(macroItem);
            
            const microItem = document.createElement('div');
            microItem.className = 'risk-share-item';
            microItem.innerHTML = `
                <div class="risk-share-label">Micro Risk</div>
                <div class="risk-share-value">${{microShare.toFixed(1)}}%</div>
            `;
            riskSummaryContent.appendChild(microItem);
            
            if (riskEnvironment) {{
                riskEnvironmentText.textContent = riskEnvironment;
            }}
        }}
        
        // Risk Analysis Sections
        function createRiskSections() {{
            if (!Factor_Risk_Reward || Factor_Risk_Reward.length === 0) {{
                document.getElementById('riskCategoryContainer').innerHTML = '<div style="text-align: center; color: #a0aec0; font-size: 18px; padding: 40px;">No risk data available</div>';
                return;
            }}
            
            const riskByCategory = {{}};
            Factor_Risk_Reward.forEach(item => {{
                const category = item.category.toLowerCase();
                if (!riskByCategory[category]) {{
                    riskByCategory[category] = [];
                }}
                riskByCategory[category].push(item);
            }});
            
            const container = d3.select('#riskCategoryContainer');
            container.selectAll('*').remove();
            
            const categories = ['macro', 'micro'];
            
            categories.forEach(category => {{
                if (!riskByCategory[category]) return;
                
                const categoryData = riskByCategory[category].sort((a, b) => b.max_compound_return - a.max_compound_return);
                
                const section = container.append('div')
                    .attr('class', 'risk-category-section');
                
                const header = section.append('div')
                    .attr('class', 'risk-category-header')
                    .on('click', function() {{
                        toggleCategorySection(this);
                    }});
                
                header.append('div')
                    .attr('class', 'risk-category-title')
                    .html(`
                        <span>${{texts[category + '_factors'] || category.charAt(0).toUpperCase() + category.slice(1) + ' Factors'}}</span>
                        <span class="risk-category-count">${{categoryData.length}}</span>
                    `);
                
                header.append('div')
                    .attr('class', 'expand-icon')
                    .text('▼');
                
                const content = section.append('div')
                    .attr('class', 'risk-category-content');
                
                categoryData.forEach(factor => {{
                    const card = content.append('div')
                        .attr('class', 'factor-card');
                    
                    card.node().addEventListener('click', function(event) {{
                        event.stopPropagation();
                        toggleFactorExpansion(this);
                    }});
                    
                    card.append('div')
                        .attr('class', 'factor-header')
                        .html(`
                            <div class="factor-name">${{factor.factor_name || 'N/A'}}</div>
                            <div class="expand-factor-icon">▶</div>
                        `);
                    
                    const metricsDiv = card.append('div')
                        .attr('class', 'factor-metrics');
                    
                    metricsDiv.html(`
                        <div class="metric">
                            <div class="metric-label">${{texts.max_return}}</div>
                            <div class="metric-value ${{factor.max_compound_return > 0 ? 'positive-value' : 'negative-value'}}">${{((factor.max_compound_return || 0) * 100).toFixed(2)}}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">${{texts.min_return}}</div>
                            <div class="metric-value ${{factor.min_compound_return > 0 ? 'positive-value' : 'negative-value'}}">${{((factor.min_compound_return || 0) * 100).toFixed(2)}}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">${{texts.range}}</div>
                            <div class="metric-value">${{((factor.return_range || 0) * 100).toFixed(2)}}%</div>
                        </div>
                    `);
                    
                    const subFactorsContainer = card.append('div')
                        .attr('class', 'sub-factors-container');
                    
                    subFactorsContainer.append('div')
                        .attr('class', 'sub-factors-title')
                        .text(texts.sub_factors);
                    
                    const list = subFactorsContainer.append('div')
                        .attr('class', 'sub-factors-list');
                    
                    if (factor.sub_factors && typeof factor.sub_factors === 'string') {{
                        factor.sub_factors.split(' | ').forEach(subFactor => {{
                            if (subFactor && subFactor.trim()) {{
                                list.append('div')
                                    .attr('class', 'sub-factor-tag')
                                    .text(subFactor.trim());
                            }}
                        }});
                    }}
                }});
            }});
        }}
        
        function toggleCategorySection(header) {{
            const content = header.parentNode.querySelector('.risk-category-content');
            const icon = header.querySelector('.expand-icon');
            
            if (content.classList.contains('expanded')) {{
                content.classList.remove('expanded');
                icon.classList.remove('expanded');
                icon.textContent = '▼';
            }} else {{
                content.classList.add('expanded');
                icon.classList.add('expanded');
                icon.textContent = '▲';
            }}
        }}
        
        function toggleFactorExpansion(factorCard) {{
            const container = factorCard.querySelector('.sub-factors-container');
            const icon = factorCard.querySelector('.expand-factor-icon');
            
            if (container.classList.contains('expanded')) {{
                container.classList.remove('expanded');
                icon.classList.remove('expanded');
                icon.textContent = '▶';
                factorCard.classList.remove('expanded');
            }} else {{
                container.classList.add('expanded');
                icon.classList.add('expanded');
                icon.textContent = '▼';
                factorCard.classList.add('expanded');
            }}
        }}
        
        function toggleFactorCard(factorName) {{
            if (!FactorTimeData[factorName] || FactorTimeData[factorName].length === 0) {{
                alert(`No time interval data available for factor: ${{factorName}}`);
                return;
            }}
            alert(`Time intervals for ${{factorName}}:\\n` + JSON.stringify(FactorTimeData[factorName], null, 2));
        }}
        
        // Initialize
        if (macroData && macroData.length > 0) {{
            renderTreemap(macroData);
        }}
        createRiskSummary();
        createRiskSections();
    </script>
</body>
</html>"""
    
    # Create temporary HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(html_content)
        temp_filepath = f.name
    
    print(f"✅ Complete integrated report generated")
    print(f"📊 Opening in browser...")
    
    # Open in browser
    webbrowser.open(f"file://{temp_filepath}")
    
    print(f"✅ All-in-one React-style report displayed!")
    print(f"💡 Features: Collapsible chains, interactive treemap, expandable risk analysis")
    
    return temp_filepath
