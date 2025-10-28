# Financial Data Sources

This module provides data retrieval functions for financial analysis.

## Modules

### `get_price.py`
Retrieves Yahoo Finance data for commodities and futures contracts.

### `wti_news.py`
Fetches WTI crude oil news from Financial Modeling Prep API and stores in Redis.

## Redis Configuration

The module uses Redis for caching news data. Redis is configured via environment variables:

- `RINGSHELL_REDIS_HOST` - Redis hostname (default: `localhost`, in Docker: `redis`)
- `RINGSHELL_REDIS_PORT` - Redis port (default: `6379`)
- `RINGSHELL_REDIS_USERNAME` - Optional Redis username
- `RINGSHELL_REDIS_PASSWORD` - Optional Redis password

## Docker Setup

Redis is now included in the Docker Compose stack:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

The backend service automatically connects to Redis using the hostname `redis` within the Docker network.

## Usage

```python
from src.financial.data_sources import get_wti_news, get_yahoo_data

# Get WTI news from the last 730 days
news = get_wti_news(days_back=730)

# Get price data for WTI futures
df = get_yahoo_data("CLZ25.NYM")
```

## Environment Variables Required

Create a `.env` file in the project root with:

```env
# Financial Data API
RINGSHELL_FMP_API_KEY=your_fmp_api_key

# Redis (automatically set in Docker)
RINGSHELL_REDIS_HOST=redis
RINGSHELL_REDIS_PORT=6379
RINGSHELL_REDIS_USERNAME=
RINGSHELL_REDIS_PASSWORD=
```

## Redis Data Structure

WTI news is stored in Redis with the following keys:
- `Crude_Oil:NEWS:WTI:new` - Latest fetched news data
- `Crude_Oil:NEWS:WTI:old` - Previous version for deduplication

Each entry contains:
```json
{
  "news": [...],
  "last_update": "2025-10-22 10:30:00",
  "total_count": 500,
  "wti_count": 200,
  "general_count": 300,
  "sources": {
    "wti_stock": 200,
    "general_filtered": 300
  }
}
```

