"""
React Treemap Generator for Q&Q.AI
Generates interactive treemap visualizations with risk analysis integration
"""

import webbrowser
import tempfile
import os
import json
import threading
import time


def generate_and_display_react_treemap(macro_df, micro_df, sector_df=None, Factor_Risk_Reward_dataset=None, risk_share_index=None, factor_time_df=None, language="English", ticker=""):
    """
    Generate React treemap with red/green colors, increased transparency, and integrated risk analysis
    
    Args:
        macro_df: DataFrame with macro factors and impacts
        micro_df: DataFrame with micro factors and impacts
        sector_df: Optional DataFrame with sector factors and impacts
        Factor_Risk_Reward_dataset: Optional risk-reward analysis data
        risk_share_index: Optional risk share distribution data
        factor_time_df: Optional DataFrame with factor time intervals for card flip functionality
        language: Language for UI ("English" or "Chinese")
        ticker: Stock ticker symbol to display in title
    
    Returns:
        str: HTML content of the generated treemap
    """
    
    # Prepare multilingual content
    titles = {
        "English": {
            "main_title": "Impact Analysis",
            "qai_title": "Q&Q.AI",
            "description": "Quantitative & Qualitative AI Investment Analysis System",
            "macro_factors": "Macro Factors",
            "micro_factors": "Micro Factors",
            "sector_factors": "Sector Factors",
            "positive_return": "Positive Return",
            "negative_return": "Negative Return",
            "risk_analysis": "Risk-Reward Analysis",
            "max_return": "Max Return",
            "min_return": "Min Return",
            "range": "Range",
            "sub_factors": "Sub-Factors:",
            "risk_summary": "Risk Environment Summary"
        },
        "Chinese": {
            "main_title": "影响分析",
            "qai_title": "Q&Q.AI",
            "description": "量化与定性AI投资分析系统",
            "macro_factors": "宏观因素",
            "micro_factors": "微观因素",
            "sector_factors": "行业因素",
            "positive_return": "正向收益",
            "negative_return": "负向收益",
            "risk_analysis": "风险收益分析",
            "max_return": "最大收益",
            "min_return": "最小收益",
            "range": "收益区间",
            "sub_factors": "子因素:",
            "risk_summary": "风险环境概览"
        }
    }
    
    t = titles.get(language, titles["English"])
    
    # Add ticker to title if provided
    title_with_ticker = f"{ticker} - {t['main_title']}" if ticker else t['main_title']
    
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
    
    # Prepare sector data if provided
    sector_data = []
    if sector_df is not None:
        for _, row in sector_df.iterrows():
            sector_data.append({
                'factor': row['factor'],
                'impact': float(row['final_impact']),
                'abs_impact': abs(float(row['final_impact']))
            })
    
    macro_data.sort(key=lambda x: x['abs_impact'], reverse=True)
    micro_data.sort(key=lambda x: x['abs_impact'], reverse=True)
    sector_data.sort(key=lambda x: x['abs_impact'], reverse=True)
    
    macro_json = json.dumps(macro_data, ensure_ascii=False)
    micro_json = json.dumps(micro_data, ensure_ascii=False)
    sector_json = json.dumps(sector_data, ensure_ascii=False)
    
    # Prepare Factor_Risk_Reward data
    risk_data_json = "[]"
    if Factor_Risk_Reward_dataset is not None:
        risk_data = Factor_Risk_Reward_dataset.to_dict('records') if hasattr(Factor_Risk_Reward_dataset, 'to_dict') else Factor_Risk_Reward_dataset
        risk_data_json = json.dumps(risk_data, ensure_ascii=False)
    
    # Prepare risk share data
    risk_share_json = "{}"
    if risk_share_index is not None:
        risk_share_json = json.dumps(risk_share_index, ensure_ascii=False)
    
    # Prepare factor time data
    factor_time_json = json.dumps(factor_time_data, ensure_ascii=False)
    
    # Create HTML with multilingual support and risk share integration
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Q&Q.AI - """ + title_with_ticker + """</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Courier New', 'Monaco', 'Menlo', monospace;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a2e 50%, #16213e 100%);
            color: #ffffff;
            min-height: 100vh;
            position: relative;
            overflow-x: hidden;
        }

        .main-container {
            position: relative;
            z-index: 2;
            max-width: 1400px;
            margin: 0 auto;
            padding: 40px 20px;
        }

        .logo-section {
            text-align: center;
            margin-bottom: 40px;
            padding: 40px 20px;
            background: transparent;
        }

        .logo-svg {
            width: 500px;
            height: 200px;
            filter: drop-shadow(0 0 40px rgba(102, 126, 234, 0.8));
            animation: pulse-glow 4s ease-in-out infinite;
        }

        @keyframes pulse-glow {
            0%, 100% { filter: drop-shadow(0 0 40px rgba(102, 126, 234, 0.8)); }
            50% { filter: drop-shadow(0 0 60px rgba(118, 75, 162, 1)); }
        }

        .logo-text {
            font-size: 48px;
            font-weight: 200;
            color: #ffffff;
            letter-spacing: 12px;
            margin-top: 30px;
            text-shadow: 0 0 30px rgba(102, 126, 234, 0.8);
        }

        .logo-description {
            font-size: 20px;
            font-weight: 100;
            color: #a0aec0;
            letter-spacing: 4px;
            margin-top: 15px;
            opacity: 0.9;
        }
        
        .ticker-bar {
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 20px;
            padding: 20px 40px;
            margin-bottom: 40px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .ticker-symbol {
            font-size: 2em;
            font-weight: 600;
            color: #667eea;
            text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
        }
        
        .tab-container {
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
        }
        
        .tab-button {
            padding: 12px 24px;
            border: none;
            background: transparent;
            color: #a0aec0;
            cursor: pointer;
            border-radius: 8px;
            font-weight: 600;
            font-size: 14px;
            transition: all 0.3s ease;
        }
        
        .tab-button.active {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
        }
        
        .tab-button:hover:not(.active) {
            background: rgba(255, 255, 255, 0.1);
            color: #ffffff;
        }
        
        .treemap-container {
            width: 100%;
            height: 650px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            position: relative;
            background: rgba(255, 255, 255, 0.02);
            backdrop-filter: blur(20px);
            overflow: hidden;
        }
        
        .legend {
            display: flex;
            justify-content: center;
            margin-top: 25px;
            gap: 40px;
        }
        
        .legend-item {
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
        }
        
        .legend-color {
            width: 16px;
            height: 16px;
            border-radius: 4px;
        }
        
        .legend-color.positive {
            background: linear-gradient(135deg, #10b981, #059669);
        }
        
        .legend-color.negative {
            background: linear-gradient(135deg, #ef4444, #dc2626);
        }
        
        .treemap-tooltip {
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
        }
        
        .treemap-tooltip strong {
            color: #fbbf24;
            font-weight: 600;
        }
        
        .return-rate {
            color: #10b981;
            font-weight: 600;
        }
        
        .negative-rate {
            color: #ef4444;
            font-weight: 600;
        }
        
        /* Risk Summary Section */
        .risk-summary {
            margin-top: 50px;
            margin-bottom: 40px;
            padding: 30px;
            background: rgba(102, 126, 234, 0.05);
            border-radius: 16px;
            border: 1px solid rgba(102, 126, 234, 0.2);
            text-align: center;
        }
        
        .risk-summary-title {
            font-size: 24px;
            font-weight: 700;
            color: #667eea;
            margin-bottom: 20px;
            text-shadow: 0 0 10px rgba(102, 126, 234, 0.5);
        }
        
        .risk-summary-content {
            display: flex;
            justify-content: space-around;
            align-items: center;
            gap: 30px;
        }
        
        .risk-share-item {
            flex: 1;
            padding: 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
        }
        
        .risk-share-item:hover {
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.08);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .risk-share-label {
            font-size: 14px;
            color: #a0aec0;
            margin-bottom: 10px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .risk-share-value {
            font-size: 28px;
            font-weight: 700;
            color: #667eea;
            text-shadow: 0 0 15px rgba(102, 126, 234, 0.6);
        }
        
        .risk-environment-text {
            font-size: 16px;
            color: #ffffff;
            margin-top: 20px;
            font-style: italic;
            opacity: 0.8;
        }
        
        /* Risk Analysis Section */
        .risk-section {
            margin-top: 60px;
            padding-top: 40px;
            border-top: 2px solid rgba(255, 255, 255, 0.1);
        }
        
        .risk-title {
            font-size: 32px;
            font-weight: 700;
            text-align: center;
            margin-bottom: 40px;
            color: #ffffff;
            text-shadow: 0 0 20px rgba(102, 126, 234, 0.5);
        }
        
        .risk-category-section {
            margin-bottom: 30px;
            background: rgba(255, 255, 255, 0.02);
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            overflow: hidden;
        }
        
        .risk-category-header {
            background: rgba(102, 126, 234, 0.1);
            padding: 20px 30px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .risk-category-header:hover {
            background: rgba(102, 126, 234, 0.2);
        }
        
        .risk-category-title {
            font-size: 20px;
            font-weight: 600;
            color: #667eea;
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .risk-category-count {
            background: rgba(102, 126, 234, 0.3);
            color: #ffffff;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
        }
        
        .expand-icon {
            font-size: 18px;
            color: #667eea;
            transition: transform 0.3s ease;
        }
        
        .expand-icon.expanded {
            transform: rotate(180deg);
        }
        
        .risk-category-content {
            padding: 0 30px;
            max-height: 0;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .risk-category-content.expanded {
            max-height: 2000px;
            padding: 30px;
        }
        
        .factor-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .factor-card:hover {
            background: rgba(255, 255, 255, 0.08);
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3);
        }
        
        .factor-card.expanded {
            background: rgba(102, 126, 234, 0.1);
            border-color: rgba(102, 126, 234, 0.3);
        }
        
        .factor-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        
        .factor-name {
            font-size: 16px;
            font-weight: 600;
            color: #ffffff;
            flex: 1;
        }
        
        .expand-factor-icon {
            font-size: 14px;
            color: #667eea;
            transition: transform 0.3s ease;
            margin-left: 15px;
        }
        
        .expand-factor-icon.expanded {
            transform: rotate(90deg);
        }
        
        .factor-metrics {
            display: flex;
            justify-content: space-between;
            gap: 20px;
            margin-bottom: 15px;
        }
        
        .metric {
            flex: 1;
            text-align: center;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            padding: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        
        .metric-label {
            font-size: 11px;
            color: #a0aec0;
            margin-bottom: 8px;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .metric-value {
            font-size: 16px;
            font-weight: 700;
            color: #ffffff;
        }
        
        .positive-value {
            color: #10b981;
            text-shadow: 0 0 10px rgba(16, 185, 129, 0.5);
        }
        
        .negative-value {
            color: #ef4444;
            text-shadow: 0 0 10px rgba(239, 68, 68, 0.5);
        }
        
        .sub-factors-container {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid rgba(255, 255, 255, 0.1);
            max-height: 0;
            overflow: hidden;
            transition: all 0.3s ease;
        }
        
        .sub-factors-container.expanded {
            max-height: 500px;
        }
        
        .sub-factors-title {
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 10px;
            color: #a0aec0;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .sub-factors-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        
        .sub-factor-tag {
            background: rgba(102, 126, 234, 0.2);
            color: #667eea;
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 10px;
            font-weight: 500;
            border: 0.1px solid rgba(102, 126, 234, 0.3);
        }
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
        """ + (f"""
        <!-- Ticker info bar -->
        <div class="ticker-bar">
            <div class="ticker-symbol">{ticker}</div>
            <div>Impact Analysis</div>
        </div>
        """ if ticker else "") + """
        
        <div class="tab-container">
            <button class="tab-button active" onclick="switchTab('macro')">""" + t['macro_factors'] + """</button>
            <button class="tab-button" onclick="switchTab('micro')">""" + t['micro_factors'] + """</button>""" + ("""<button class="tab-button" onclick="switchTab('sector')">""" + t['sector_factors'] + """</button>""" if sector_df is not None else "") + """
        </div>
        
        <div id="treemap" class="treemap-container"></div>
        
        <div class="legend">
            <div class="legend-item">
                <div class="legend-color positive"></div>
                <span>""" + t['positive_return'] + """</span>
            </div>
            <div class="legend-item">
                <div class="legend-color negative"></div>
                <span>""" + t['negative_return'] + """</span>
            </div>
        </div>
        
        <!-- Risk Summary Section -->
        <div class="risk-summary" id="riskSummarySection" style="display: none;">
            <div class="risk-summary-title">""" + t['risk_summary'] + """</div>
            <div class="risk-summary-content" id="riskSummaryContent">
                <!-- Risk share data will be populated by JavaScript -->
            </div>
            <div class="risk-environment-text" id="riskEnvironmentText">
                <!-- Risk environment description will be populated by JavaScript -->
            </div>
        </div>
        
        <div class="risk-section">
            <h2 class="risk-title">""" + t['risk_analysis'] + """</h2>
            
            <div id="riskCategoryContainer">
                <!-- Risk category sections will be populated by JavaScript -->
            </div>
        </div>
    </div>

    <script>
        const macroData = """ + macro_json + """;
        const microData = """ + micro_json + """;
        const sectorData = """ + sector_json + """;
        const Factor_Risk_Reward = """ + risk_data_json + """;
        const RiskShareIndex = """ + risk_share_json + """;
        const FactorTimeData = """ + factor_time_json + """;
        
        // Language texts
        const texts = """ + json.dumps(t, ensure_ascii=False) + """;
        
        let currentData = macroData;
        
        // Create tooltip
        const tooltip = d3.select("body").append("div")
            .attr("class", "treemap-tooltip")
            .style("opacity", 0);
        
        // Function to wrap text into multiple lines
        function wrapText(text, width, fontSize) {
            const words = text.split(' ');
            const lines = [];
            let currentLine = words[0] || '';
            
            for (let i = 1; i < words.length; i++) {
                const word = words[i];
                const testLine = currentLine + ' ' + word;
                const testWidth = testLine.length * fontSize * 0.6; // Approximate character width
                
                if (testWidth < width) {
                    currentLine = testLine;
                } else {
                    lines.push(currentLine);
                    currentLine = word;
                }
            }
            if (currentLine) {
                lines.push(currentLine);
            }
            return lines;
        }
        
        function renderTreemap(data) {
            const container = d3.select('#treemap');
            container.selectAll('*').remove();
            
            const width = container.node().offsetWidth;
            const height = 650;
            
            // Create treemap layout
            const treemap = d3.treemap()
                .size([width - 4, height - 4])
                .padding(2);
            
            // Prepare hierarchy
            const root = d3.hierarchy({ children: data })
                .sum(d => d.abs_impact)
                .sort((a, b) => b.value - a.value);
            
            // Generate treemap
            treemap(root);
            
            // Create SVG container
            const svg = container
                .append('svg')
                .attr('width', width)
                .attr('height', height);
            
            // Create nodes
            const nodes = svg.selectAll('.node')
                .data(root.leaves())
                .enter().append('g')
                .attr('class', 'node')
                .attr('transform', d => `translate(${d.x0}, ${d.y0})`);
            
            // Add rectangles with RED/GREEN colors and INCREASED TRANSPARENCY
            nodes.append('rect')
                .attr('width', d => d.x1 - d.x0)
                .attr('height', d => d.y1 - d.y0)
                .attr('class', d => d.data.impact >= 0 ? 'positive' : 'negative')
                .style('fill', d => d.data.impact >= 0 ? 'rgba(16, 185, 129, 0.7)' : 'rgba(239, 68, 68, 0.7)')  // 70% opacity
                .style('stroke', '#fff')
                .style('stroke-width', 2)
                .style('cursor', 'pointer')
                .on('click', function(event, d) {
                    toggleFactorCard(d.data.factor);
                })
                .on('mouseover', function(event, d) {
                    tooltip.transition()
                        .duration(200)
                        .style('opacity', 0.9);
                    tooltip.html(`
                        <strong>${d.data.factor}</strong><br/>
                        <span class="${d.data.impact >= 0 ? 'return-rate' : 'negative-rate'}">
                            Return Rate: ${(d.data.impact * 100).toFixed(2)}%
                        </span><br/>
                        <small>Click to view time intervals</small>
                    `)
                        .style('left', (event.pageX + 10) + 'px')
                        .style('top', (event.pageY - 28) + 'px');
                })
                .on('mouseout', function(d) {
                    tooltip.transition()
                        .duration(500)
                        .style('opacity', 0);
                });
            
            // Calculate relative font sizes based on data range
            const impacts = data.map(d => d.abs_impact);
            const maxImpact = Math.max(...impacts);
            const minImpact = Math.min(...impacts);
            const impactRange = maxImpact - minImpact;
            
            // Add event names in TOP LEFT with BETTER VISIBILITY
            nodes.each(function(d) {
                const node = d3.select(this);
                const rectWidth = d.x1 - d.x0 - 12;
                const rectHeight = d.y1 - d.y0;
                const normalizedImpact = impactRange > 0 ? (d.data.abs_impact - minImpact) / impactRange : 0;
                
                // Bigger font size for better visibility
                const eventFontSize = 12 + (normalizedImpact * 10); // Range from 12px to 22px
                
                // Wrap text for event names
                const lines = wrapText(d.data.factor, rectWidth, eventFontSize);
                const lineHeight = eventFontSize * 1.2;
                
                // Position event names in TOP LEFT with better contrast
                lines.forEach((line, i) => {
                    node.append('text')
                        .attr('x', 8)  // Left margin
                        .attr('y', 20 + (i * lineHeight))  // Top margin - Fixed the variable name
                        .attr('text-anchor', 'start')
                        .attr('dominant-baseline', 'middle')
                        .style('fill', '#ffffff')  // White text for good contrast
                        .style('font-size', eventFontSize + 'px')
                        .style('font-weight', '900')  // Extra bold
                        .style('text-shadow', '2px 2px 4px rgba(0,0,0,0.8)')  // Black shadow
                        .text(line);
                });
            });
            
            // Add BIG IMPACT RATES in CENTER with better visibility
            nodes.append('text')
                .attr('x', d => (d.x1 - d.x0) / 2)
                .attr('y', d => (d.y1 - d.y0) / 2)
                .attr('text-anchor', 'middle')
                .attr('dominant-baseline', 'middle')
                .style('fill', '#ffffff')  // White text for good contrast
                .style('font-size', d => {
                    const normalizedImpact = impactRange > 0 ? (d.data.abs_impact - minImpact) / impactRange : 0;
                    const fontSize = 18 + (normalizedImpact * 18); // Range from 18px to 36px
                    return fontSize + 'px';
                })
                .style('font-weight', '900')  // Extra bold
                .style('text-shadow', '3px 3px 6px rgba(0,0,0,0.8)')  // Black shadow
                .text(d => {
                    const rate = (d.data.impact * 100).toFixed(1);
                    return `${rate > 0 ? '+' : ''}${rate}%`;
                });
        }
        
        function switchTab(tab) {
            // Update button states
            document.querySelectorAll('.tab-button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Switch data and render
            if (tab === 'macro') {
                currentData = macroData;
            } else if (tab === 'micro') {
                currentData = microData;
            } else if (tab === 'sector') {
                currentData = sectorData;
            }
            renderTreemap(currentData);
        }
        
        // Risk Share Summary Functions
        function createRiskSummary() {
            if (!RiskShareIndex || Object.keys(RiskShareIndex).length === 0) {
                document.getElementById('riskSummarySection').style.display = 'none';
                return;
            }
            
            const riskSummarySection = document.getElementById('riskSummarySection');
            const riskSummaryContent = document.getElementById('riskSummaryContent');
            const riskEnvironmentText = document.getElementById('riskEnvironmentText');
            
            riskSummarySection.style.display = 'block';
            
            // Clear existing content
            riskSummaryContent.innerHTML = '';
            
            // Create risk share items
            const macroShare = RiskShareIndex.macro_risk_share || 0;
            const microShare = RiskShareIndex.micro_risk_share || 0;
            const riskEnvironment = RiskShareIndex.risk_environment || '';
            
            const macroItem = riskSummaryContent.appendChild(document.createElement('div'));
            macroItem.className = 'risk-share-item';
            macroItem.innerHTML = `
                <div class="risk-share-label">Macro Risk</div>
                <div class="risk-share-value">${macroShare.toFixed(1)}%</div>
            `;
            
            const microItem = riskSummaryContent.appendChild(document.createElement('div'));
            microItem.className = 'risk-share-item';
            microItem.innerHTML = `
                <div class="risk-share-label">Micro Risk</div>
                <div class="risk-share-value">${microShare.toFixed(1)}%</div>
            `;
            
            if (riskEnvironment) {
                riskEnvironmentText.textContent = riskEnvironment;
            }
        }
        
        // Risk Analysis Functions - Collapsible Sections
        function createRiskSections() {
            if (!Factor_Risk_Reward || Factor_Risk_Reward.length === 0) {
                document.getElementById('riskCategoryContainer').innerHTML = '<div style="text-align: center; color: #a0aec0; font-size: 18px; padding: 40px;">No risk data available</div>';
                return;
            }
            
            // Group risk data by category
            const riskByCategory = {};
            Factor_Risk_Reward.forEach(item => {
                const category = item.category.toLowerCase();
                if (!riskByCategory[category]) {
                    riskByCategory[category] = [];
                }
                riskByCategory[category].push(item);
            });
            
            const container = d3.select('#riskCategoryContainer');
            container.selectAll('*').remove();
            
            // Create collapsible sections for each category
            const categories = ['macro', 'micro', 'sector'];
            
            categories.forEach(category => {
                if (!riskByCategory[category]) return;
                
                const categoryData = riskByCategory[category].sort((a, b) => b.max_compound_return - a.max_compound_return);
                
                const section = container.append('div')
                    .attr('class', 'risk-category-section');
                
                const header = section.append('div')
                    .attr('class', 'risk-category-header')
                    .on('click', function() {
                        toggleCategorySection(this);
                    });
                
                header.append('div')
                    .attr('class', 'risk-category-title')
                    .html(`
                        <span>${texts[category.toLowerCase() + '_factors'] || category.charAt(0).toUpperCase() + category.slice(1) + ' Factors'}</span>
                        <span class="risk-category-count">${categoryData.length}</span>
                    `);
                
                header.append('div')
                    .attr('class', 'expand-icon')
                    .text('▼');
                
                const content = section.append('div')
                    .attr('class', 'risk-category-content');
                
                // Create factor cards
                categoryData.forEach(factor => {
                    const card = content.append('div')
                        .attr('class', 'factor-card');
                    
                    card.node().addEventListener('click', function(event) {
                        event.stopPropagation();
                        toggleFactorExpansion(this);
                    });
                    
                    card.append('div')
                        .attr('class', 'factor-header')
                        .html(`
                            <div class="factor-name">${factor.factor_name || 'N/A'}</div>
                            <div class="expand-factor-icon">▶</div>
                        `);
                    
                    const metricsDiv = card.append('div')
                        .attr('class', 'factor-metrics');
                    
                    metricsDiv.html(`
                        <div class="metric">
                            <div class="metric-label">${texts.max_return}</div>
                            <div class="metric-value ${factor.max_compound_return > 0 ? 'positive-value' : 'negative-value'}">${((factor.max_compound_return || 0) * 100).toFixed(2)}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">${texts.min_return}</div>
                            <div class="metric-value ${factor.min_compound_return > 0 ? 'positive-value' : 'negative-value'}">${((factor.min_compound_return || 0) * 100).toFixed(2)}%</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">${texts.range}</div>
                            <div class="metric-value">${((factor.return_range || 0) * 100).toFixed(2)}%</div>
                        </div>
                    `);
                    
                    const subFactorsContainer = card.append('div')
                        .attr('class', 'sub-factors-container');
                    
                    subFactorsContainer.append('div')
                        .attr('class', 'sub-factors-title')
                        .text(texts.sub_factors);
                    
                    const list = subFactorsContainer.append('div')
                        .attr('class', 'sub-factors-list');
                    
                    if (factor.sub_factors && typeof factor.sub_factors === 'string') {
                        factor.sub_factors.split(' | ').forEach(subFactor => {
                            if (subFactor && subFactor.trim()) {
                                list.append('div')
                                    .attr('class', 'sub-factor-tag')
                                    .text(subFactor.trim());
                            }
                        });
                    }
                });
            });
        }
        
        function toggleCategorySection(header) {
            const content = header.parentNode.querySelector('.risk-category-content');
            const icon = header.querySelector('.expand-icon');
            
            if (!content || !icon) return;
            
            if (content.classList.contains('expanded')) {
                content.classList.remove('expanded');
                icon.classList.remove('expanded');
                icon.textContent = '▼';
            } else {
                content.classList.add('expanded');
                icon.classList.add('expanded');
                icon.textContent = '▲';
            }
        }
        
        function toggleFactorExpansion(factorCard) {
            const container = factorCard.querySelector('.sub-factors-container');
            const icon = factorCard.querySelector('.expand-factor-icon');
            
            if (!container || !icon) return;
            
            if (container.classList.contains('expanded')) {
                container.classList.remove('expanded');
                icon.classList.remove('expanded');
                icon.textContent = '▶';
                factorCard.classList.remove('expanded');
            } else {
                container.classList.add('expanded');
                icon.classList.add('expanded');
                icon.textContent = '▼';
                factorCard.classList.add('expanded');
            }
        }
        
        // Factor Card Flip Functionality
        function toggleFactorCard(factorName) {
            // Check if factor has time data
            if (!FactorTimeData[factorName] || FactorTimeData[factorName].length === 0) {
                alert(`No time interval data available for factor: ${factorName}`);
                return;
            }
            
            // Create or update factor card modal
            let modal = document.getElementById('factorCardModal');
            if (!modal) {
                modal = createFactorCardModal();
            }
            
            // Populate modal with factor time data
            populateFactorCard(factorName, FactorTimeData[factorName]);
            
            // Show modal
            modal.style.display = 'block';
        }
        
        function createFactorCardModal() {
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
            modal.onclick = (event) => {
                if (event.target === modal) {
                    modal.style.display = 'none';
                }
            };
            
            document.body.appendChild(modal);
            return modal;
        }
        
        function populateFactorCard(factorName, timeIntervals) {
            const title = document.getElementById('factorCardTitle');
            const content = document.getElementById('factorCardContent');
            
            title.textContent = factorName;
            
            // Group intervals by scope
            const macroIntervals = timeIntervals.filter(interval => interval.scope === 'macro');
            const microIntervals = timeIntervals.filter(interval => interval.scope === 'micro');
            
            let html = '';
            
            if (macroIntervals.length > 0) {
                html += '<div style="margin-bottom: 20px;">';
                html += '<h3 style="color: #10b981; margin: 0 0 10px 0; font-size: 18px;">📊 Macro Time Intervals</h3>';
                macroIntervals.forEach(interval => {
                    html += createIntervalCard(interval);
                });
                html += '</div>';
            }
            
            if (microIntervals.length > 0) {
                html += '<div>';
                html += '<h3 style="color: #3b82f6; margin: 0 0 10px 0; font-size: 18px;">🏢 Micro Time Intervals</h3>';
                microIntervals.forEach(interval => {
                    html += createIntervalCard(interval);
                });
                html += '</div>';
            }
            
            content.innerHTML = html;
        }
        
        function createIntervalCard(interval) {
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
                            ${interval.time_interval}
                        </span>
                        <span style="
                            background: ${interval.scope === 'macro' ? '#10b981' : '#3b82f6'};
                            color: white;
                            padding: 4px 8px;
                            border-radius: 12px;
                            font-size: 12px;
                            font-weight: 500;
                        ">
                            ${interval.scope.toUpperCase()}
                        </span>
                    </div>
                    <div style="color: #a0aec0; font-size: 14px;">
                        <div>📅 Start: ${startDate}</div>
                        <div>📅 End: ${endDate}</div>
                        <div>⏱️ Duration: ${duration} days</div>
                    </div>
                </div>
            `;
        }
        
        // Initialize everything
        renderTreemap(macroData);
        createRiskSummary();
        createRiskSections();
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
    
    print(f"Q&Q.AI treemap with Risk Analysis opened in browser! Language: {language}")
    if ticker:
        print(f"📊 Ticker: {ticker}")
    print("✅ Portfolio overview removed")
    print("✅ Multilingual support added")
    print("✅ Risk share summary integrated")
    
    # Clean up temp file after a delay
    def cleanup():
        time.sleep(2)
        try:
            os.unlink(temp_file)
        except:
            pass
    
    threading.Thread(target=cleanup, daemon=True).start()
    
    return html_content


# Example usage function
def example_usage():
    """
    Example of how to use the treemap generator
    """
    import pandas as pd
    
    # Sample data - replace with your actual data
    macro_df = pd.DataFrame({
        'factor': ['Interest Rates', 'Inflation', 'GDP Growth', 'Unemployment'],
        'final_impact': [0.05, -0.03, 0.08, -0.02]
    })
    
    micro_df = pd.DataFrame({
        'factor': ['Company Earnings', 'Market Sentiment', 'Technical Analysis', 'News Impact'],
        'final_impact': [0.12, -0.05, 0.07, -0.08]
    })
    
    # Sample sector data
    sector_df = pd.DataFrame({
        'factor': ['Technology Trends', 'Industry Competition', 'Regulatory Changes'],
        'final_impact': [0.08, -0.04, 0.06]
    })
    
    # Sample risk data
    risk_data = [
        {
            'category': 'macro',
            'factor_name': 'Interest Rates',
            'max_compound_return': 0.15,
            'min_compound_return': -0.10,
            'return_range': 0.25,
            'sub_factors': 'Fed Policy | Bond Yields | Credit Spreads'
        }
    ]
    
    risk_share = {
        'macro_risk_share': 60.5,
        'micro_risk_share': 39.5,
        'risk_environment': 'Moderate risk environment with balanced macro and micro factors'
    }
    
    # Generate treemap
    html_content = generate_and_display_react_treemap(
        macro_df=macro_df,
        micro_df=micro_df,
        sector_df=sector_df,
        Factor_Risk_Reward_dataset=risk_data,
        risk_share_index=risk_share,
        language="English",
        ticker="AAPL"
    )
    
    return html_content


if __name__ == "__main__":
    # Run example
    example_usage()
