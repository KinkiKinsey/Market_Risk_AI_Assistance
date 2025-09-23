"""Utilities for reading stock trend data from the Redis `Stock_Trend_INFOS` collection."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

import redis

try:  # Prefer shared configuration if available
    from shared_clients import STOCK_TREND_REDIS_CONFIG as _DEFAULT_REDIS_CONFIG
except ImportError:
    _DEFAULT_REDIS_CONFIG: Dict[str, Any] = {}

DEFAULT_COLLECTION = "Stock_Trend_INFOS"


@dataclass
class RedisConnectionSettings:
    """Container for Redis connection parameters."""

    host: str
    port: int
    username: str = "default"
    password: Optional[str] = None
    decode_responses: bool = True

    @classmethod
    def from_env(cls, prefix: str = "STOCK_TREND_REDIS") -> "RedisConnectionSettings":
        """Build settings from environment variables or shared defaults."""

        env_host = os.getenv(f"{prefix}_HOST")
        env_port = os.getenv(f"{prefix}_PORT")
        env_username = os.getenv(f"{prefix}_USERNAME")
        env_password = os.getenv(f"{prefix}_PASSWORD")

        if env_host and env_port:
            return cls(
                host=env_host,
                port=int(env_port),
                username=env_username or "default",
                password=env_password,
            )

        if _DEFAULT_REDIS_CONFIG:
            return cls(
                host=_DEFAULT_REDIS_CONFIG.get("host", "localhost"),
                port=int(_DEFAULT_REDIS_CONFIG.get("port", 6379)),
                username=_DEFAULT_REDIS_CONFIG.get("username", "default"),
                password=_DEFAULT_REDIS_CONFIG.get("password"),
            )

        raise ValueError(
            "Redis configuration missing. Set STOCK_TREND_REDIS_* environment variables"
            " or update shared_clients.STOCK_TREND_REDIS_CONFIG."
        )


class StockTrendInfosClient:
    """Lightweight helper that fetches Stock Trend INFOS documents from Redis."""

    def __init__(
        self,
        settings: Optional[RedisConnectionSettings] = None,
        *,
        collection_name: str = DEFAULT_COLLECTION,
    ) -> None:
        self.settings = settings or RedisConnectionSettings.from_env()
        self.collection_name = collection_name
        self._client = redis.Redis(
            host=self.settings.host,
            port=self.settings.port,
            username=self.settings.username,
            password=self.settings.password,
            decode_responses=self.settings.decode_responses,
        )

    def _build_key(self, ticker: str) -> str:
        return f"{self.collection_name}:{ticker.upper()}_trends"

    def get_document(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Return the stored Stock Trend payload for the requested ticker."""

        redis_key = self._build_key(ticker)
        payload = self._client.get(redis_key)
        if not payload:
            return None
        return json.loads(payload)

    def list_tickers(self) -> Dict[str, str]:
        """Return a mapping of Redis keys to ticker symbols present in the collection."""

        tickers: Dict[str, str] = {}
        pattern = f"{self.collection_name}:*_trends"
        for redis_key in self._client.scan_iter(match=pattern):
            symbol = redis_key.split(":")[-1].replace("_trends", "")
            tickers[redis_key] = symbol
        return tickers

    def close(self) -> None:
        """Release the underlying Redis connection."""

        try:
            self._client.close()
        except AttributeError:
            # redis-py <5.0 does not expose close()
            pass


def fetch_stock_trend_infos(ticker: str, *, collection_name: str = DEFAULT_COLLECTION) -> Optional[Dict[str, Any]]:
    """Convenience wrapper for one-off scripts."""

    client = StockTrendInfosClient(collection_name=collection_name)
    try:
        return client.get_document(ticker)
    finally:
        client.close()


if __name__ == "__main__":
    import argparse
    import pprint

    parser = argparse.ArgumentParser(description="Fetch a Stock_Trend_INFOS entry for a ticker.")
    parser.add_argument("ticker", help="Ticker symbol to query, for example AAPL")
    parser.add_argument(
        "--collection",
        default=DEFAULT_COLLECTION,
        help="Redis collection/namespace to read from (defaults to Stock_Trend_INFOS)",
    )
    args = parser.parse_args()

    document = fetch_stock_trend_infos(args.ticker, collection_name=args.collection)
    if document is None:
        print(f"⚠️ No document found for ticker {args.ticker!r} in {args.collection}.")
    else:
        pprint.pprint(document)
