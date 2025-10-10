# Quant Impact Modular Agent

A complete modular quant impact analysis system that integrates the Dynamic Alpha pipeline from `Dynamic_Alpha.ipynb`. This system provides a simple interface to get 6 datasets for any ticker with automatic warm-up pool integration.

## 🎯 Key Features

- **One-Function Access**: Get all 6 datasets with a single function call
- **Automatic Warm-up Pool**: Pre-updates Market Expectation and Sector Analyst modules
- **Complete Pipeline Integration**: Implements the exact Dynamic Alpha pipeline
- **Database Caching**: Stores results for fast future access
- **Multi-language Support**: Generate factors in any language
- **Async Ready**: Built for async/await patterns

## 📊 Output: 6 Datasets + Metadata

When you call the agent, you get exactly 7 items:

1. **Risk Share Index**: Macro vs Micro risk percentages
2. **Macro Volatility DataFrame**: Macro factors with HIGH/LOW volatility classification
3. **Micro Volatility DataFrame**: Micro factors with HIGH/LOW volatility classification
4. **Risk-Reward Ratio DataFrame**: Sharpe-style risk-reward metrics
5. **Macro Total Impact DataFrame**: Compound impact calculations for macro factors
6. **Micro Total Impact DataFrame**: Compound impact calculations for micro factors
7. **Metadata**: Update dates, status, and analysis parameters

## 🚀 Quick Start

### Basic Usage

```python
import asyncio
from Quant_Impact_Agent import get_quant_impact_data

async def main():
    # Get all 6 datasets for TSLA
    datasets = await get_quant_impact_data("TSLA", language="English")
    
    # Unpack the results
    risk_share_index, macro_volatility_df, micro_volatility_df, risk_reward_df, macro_total_impact_df, micro_total_impact_df, meta_info = datasets
    
    print(f"Risk Environment: {risk_share_index}")
    print(f"Macro Factors: {len(macro_volatility_df)}")
    print(f"Micro Factors: {len(micro_volatility_df)}")

asyncio.run(main())
```

### Advanced Usage

```python
import asyncio
from Quant_Impact_Agent import QuantImpactAgent

async def main():
    # Initialize agent
    agent = QuantImpactAgent(user_id="my_analysis")
    
    try:
        # Get data for multiple tickers
        tickers = ["TSLA", "AAPL", "MSFT"]
        
        for ticker in tickers:
            datasets = await agent.get_quant_impact_data(ticker, language="Chinese")
            risk_share_index, macro_volatility_df, micro_volatility_df, risk_reward_df, macro_total_impact_df, micro_total_impact_df, meta_info = datasets
            
            print(f"{ticker}: {meta_info['status']}")
        
        # List all available tickers
        available = await agent.list_available_tickers()
        print(f"Available tickers: {available}")
        
    finally:
        await agent.close()

asyncio.run(main())
```

## 📋 Complete API Reference

### `get_quant_impact_data(ticker, language="English", force_update=False)`

**Convenience function** - Get all 6 datasets with one call.

**Parameters:**
- `ticker` (str): Stock ticker symbol (e.g., 'TSLA')
- `language` (str): Language for factor generation (default: 'English')
- `force_update` (bool): Force update even if data exists (default: False)

**Returns:**
- Tuple of 7 items: (risk_share_index, macro_volatility_df, micro_volatility_df, risk_reward_df, macro_total_impact_df, micro_total_impact_df, meta_info)

### `QuantImpactAgent` Class

#### `__init__(user_id="default_user")`
Initialize the agent with a user ID for database storage.

#### `get_quant_impact_data(ticker, language="English", force_update=False)`
Get 6 datasets for a ticker (same as convenience function).

#### `list_available_tickers()`
List all tickers with available quant impact data.

#### `get_metadata(ticker)`
Get metadata for a specific ticker.

#### `delete_data(ticker)`
Delete quant impact data for a ticker.

#### `health_check()`
Perform health check on Redis connection.

#### `close()`
Close Redis connection.

## 🔄 Pipeline Process

When you request data for a ticker, the agent:

1. **Checks Database**: Looks for existing data first
2. **Warm-up Pool**: Updates Market Expectation and Sector Analyst modules
3. **Sector Analysis**: Gets sector index using Sector Analyst Agent
4. **Beta Calculation**: Performs orthogonal sector analysis
5. **Factor Generation**: Uses LLM to generate macro + micro factors
6. **Date Mapping**: Maps factors to specific date ranges
7. **Beta Filtering**: Calculates real market/micro impact using beta
8. **Risk Analysis**: Generates the 6 datasets using risk analysis
9. **Database Storage**: Stores results for future access

## 📊 Dataset Details

### 1. Risk Share Index
```python
{
    "macro_risk_share": 65.2,
    "micro_risk_share": 34.8,
    "risk_environment": "Current risk environment is 34.8% company-driven, 65.2% macro-driven."
}
```

### 2. Macro Volatility DataFrame
```python
    scope  factor           volatility_level
0   macro  美联储降息           HIGH
1   macro  中美贸易战升级        HIGH
2   macro  经济衰退担忧          LOW
```

### 3. Micro Volatility DataFrame
```python
    scope  factor           volatility_level
0   micro  业绩超预期           HIGH
1   micro  产品召回事件         HIGH
2   micro  管理层法律调查       LOW
```

### 4. Risk-Reward Ratio DataFrame
```python
    scope  factor           risk_reward_ratio
0   macro  美联储降息           2.45
1   micro  业绩超预期           1.89
2   macro  中美贸易战升级       1.23
```

### 5. Macro Total Impact DataFrame
```python
    factor           final_impact
0   美联储降息          0.0456
1   中美贸易战升级       0.0234
2   经济衰退担忧         0.0123
```

### 6. Micro Total Impact DataFrame
```python
    factor           final_impact
0   业绩超预期          0.0678
1   产品召回事件        0.0345
2   管理层法律调查      0.0098
```

### 7. Metadata
```python
{
    "ticker": "TSLA",
    "sector_index": "XLY",
    "market_beta": 1.2777,
    "risk_free_rate": 0.025,
    "data_period": "2024-01-01 to 2024-12-31",
    "update_date": "2024-12-19T10:30:00",
    "status": "success",
    "data_source": "database"
}
```

## 🔧 Configuration

### Redis Configuration
The system uses Redis for caching. Default configuration:
```python
REDIS_HOST = "redis-16376.crce197.us-east-2-1.ec2.redns.redis-cloud.com"
REDIS_PORT = 16376
REDIS_USERNAME = "default"
REDIS_PASSWORD = "rl8242B4UItBhFzgHW5APEqZnkYoaEZv"
COLLECTION_NAME = "Quant_Impact_INFOS"
```

### FMP API Configuration
Uses Financial Modeling Prep API for stock price data:
```python
FMP_API_KEY = "9dfbbfa29d93f4793f246e8fb5ca5e74"
```

## 🎯 Use Cases

### 1. Risk Assessment
```python
datasets = await get_quant_impact_data("TSLA")
risk_share_index, macro_volatility_df, micro_volatility_df, risk_reward_df, macro_total_impact_df, micro_total_impact_df, meta_info = datasets

# Check if stock is macro or micro driven
if risk_share_index['macro_risk_share'] > 60:
    print("Stock is primarily macro-driven")
else:
    print("Stock is primarily company-driven")
```

### 2. Factor Analysis
```python
# Find high volatility factors
high_vol_macro = macro_volatility_df[macro_volatility_df['volatility_level'] == 'HIGH']
high_vol_micro = micro_volatility_df[micro_volatility_df['volatility_level'] == 'HIGH']

print(f"High volatility macro factors: {len(high_vol_macro)}")
print(f"High volatility micro factors: {len(high_vol_micro)}")
```

### 3. Impact Ranking
```python
# Get top impact factors
top_macro_impact = macro_total_impact_df.iloc[0]
top_micro_impact = micro_total_impact_df.iloc[0]

print(f"Top macro impact: {top_macro_impact['factor']} ({top_macro_impact['final_impact']:.4f})")
print(f"Top micro impact: {top_micro_impact['factor']} ({top_micro_impact['final_impact']:.4f})")
```

### 4. Portfolio Analysis
```python
tickers = ["TSLA", "AAPL", "MSFT", "GOOGL"]
portfolio_analysis = {}

for ticker in tickers:
    datasets = await get_quant_impact_data(ticker)
    risk_share_index, macro_volatility_df, micro_volatility_df, risk_reward_df, macro_total_impact_df, micro_total_impact_df, meta_info = datasets
    
    portfolio_analysis[ticker] = {
        "macro_risk": risk_share_index['macro_risk_share'],
        "micro_risk": risk_share_index['micro_risk_share'],
        "high_vol_factors": len(macro_volatility_df[macro_volatility_df['volatility_level'] == 'HIGH']) + 
                           len(micro_volatility_df[micro_volatility_df['volatility_level'] == 'HIGH'])
    }

print("Portfolio Risk Analysis:")
for ticker, analysis in portfolio_analysis.items():
    print(f"{ticker}: {analysis['macro_risk']:.1f}% macro, {analysis['high_vol_factors']} high-vol factors")
```

## 🔄 Update Logic

The system includes built-in update logic:

- **Monthly Updates**: Factors impact will be updated every month
- **Force Updates**: Use `force_update=True` to bypass cache
- **Automatic Caching**: Results are cached for 30 days
- **Warm-up Pool**: Only updates Market Expectation and Sector Analyst modules

## 🛠️ Dependencies

- `redis`: Redis database connection
- `pandas`: DataFrame operations
- `numpy`: Numerical calculations
- `scipy`: Statistical analysis
- `requests`: API calls
- `langchain`: LLM integration
- `shared_clients`: Shared LLM and Redis clients

## 🚨 Error Handling

The system gracefully handles errors:

```python
try:
    datasets = await get_quant_impact_data("INVALID_TICKER")
except Exception as e:
    print(f"Error: {e}")
    # Returns empty datasets with error information
```

## 🔮 Future Extensions

- Support for other database connections (PostgreSQL, MongoDB)
- Real-time factor monitoring
- Batch processing capabilities
- Advanced visualization options
- Custom factor generation
- Historical factor tracking

## 📝 Examples

See `example_usage_modular.py` for comprehensive usage examples including:
- Basic usage
- Agent class usage
- Force updates
- Data analysis
- Portfolio analysis

## 🤝 Integration

This modular system integrates seamlessly with other Fintegrate AI modules:

- **Market Expectation Agent**: For stock trend data
- **Sector Analyst Agent**: For sector analysis
- **LLM Call Agent**: For factor generation
- **Shared Clients**: For database and LLM access

The system is designed to be a drop-in replacement for the Dynamic Alpha notebook with a much simpler interface.
