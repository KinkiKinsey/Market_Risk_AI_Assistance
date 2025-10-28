"""
Get Price Data from Yahoo Finance

Simple module to fetch historical price and volume data for any ticker.

Usage:
    from get_price import get_yahoo_data
    
    df = get_yahoo_data("CLZ25.NYM")
    df = get_yahoo_data("AAPL", 90)
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta


def get_yahoo_data(ticker: str, days: int = 365) -> pd.DataFrame:
    """
    Get historical price data from Yahoo Finance
    
    Input:
        ticker: Yahoo Finance ticker
                Examples: 'CLZ25.NYM' (Crude Oil Dec 2025)
                         'GC=F' (Gold Futures)
                         'AAPL' (Apple Stock)
                         'BTC-USD' (Bitcoin)
        days: Number of days (default: 365)
    
    Output:
        DataFrame with columns: ['date', 'close', 'volume']
        Date is a regular column (not index)
    """
    
    try:
        print(f"📊 Fetching {days} days of data for {ticker}...")
        
        end_date = datetime.now() + timedelta(days=1)  # Tomorrow to ensure we get today's data
        start_date = end_date - timedelta(days=days)
        
        df = yf.download(
            ticker, 
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            progress=False
        )
        
        if df.empty:
            print(f"❌ No data available for {ticker}")
            return pd.DataFrame(columns=['date', 'close', 'volume'])
        
        # Clean column names
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.columns = [col.lower() for col in df.columns]
        
        # Reset index to make date a column
        df = df.reset_index()
        df.columns = ['date' if col.lower() in ['date', 'index'] else col for col in df.columns]
        
        # Select ONLY date, close, volume (no index)
        df = df[['date', 'close', 'volume']].copy()
        
        print(f"✅ Retrieved {len(df)} days")
        print(f"   Range: {df['date'].min().date()} → {df['date'].max().date()}")
        print(f"   Latest: ${df['close'].iloc[-1]:.2f}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame(columns=['date', 'close', 'volume'])


def get_yahoo_data_comprehensive(ticker: str, days: int = 365) -> pd.DataFrame:
    """
    Get comprehensive historical price data from Yahoo Finance (OHLCV)
    
    Input:
        ticker: Yahoo Finance ticker
                Examples: 'CLZ25.NYM' (Crude Oil Dec 2025)
                         'GC=F' (Gold Futures)
                         'AAPL' (Apple Stock)
                         'BTC-USD' (Bitcoin)
        days: Number of days (default: 365)
    
    Output:
        DataFrame with columns: ['date', 'open', 'high', 'low', 'close', 'volume']
        Date is a regular column (not index)
    """
    
    try:
        print(f"📊 Fetching {days} days of comprehensive data for {ticker}...")
        
        end_date = datetime.now() + timedelta(days=1)  # Tomorrow to ensure we get today's data
        start_date = end_date - timedelta(days=days)
        
        df = yf.download(
            ticker, 
            start=start_date.strftime('%Y-%m-%d'),
            end=end_date.strftime('%Y-%m-%d'),
            progress=False
        )
        
        if df.empty:
            print(f"❌ No data available for {ticker}")
            return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        
        # Clean column names
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.columns = [col.lower() for col in df.columns]
        
        # Reset index to make date a column
        df = df.reset_index()
        df.columns = ['date' if col.lower() in ['date', 'index'] else col for col in df.columns]
        
        # Select OHLCV columns
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']].copy()
        
        print(f"✅ Retrieved {len(df)} days")
        print(f"   Range: {df['date'].min().date()} → {df['date'].max().date()}")
        print(f"   Latest Close: ${df['close'].iloc[-1]:.2f}")
        print(f"   Latest High: ${df['high'].iloc[-1]:.2f}")
        print(f"   Latest Low: ${df['low'].iloc[-1]:.2f}")
        
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return pd.DataFrame(columns=['date', 'open', 'high', 'low', 'close', 'volume'])


def get_zigga_price() -> dict:
    """
    Get current Zigga token price from DEX Screener API
    
    Output:
        Dictionary with price information including:
        - price_usd: Current price in USD
        - price_change_24h: 24h price change percentage
        - volume_24h: 24h trading volume
        - market_cap: Market capitalization
    """
    
    try:
        print("🪙 Fetching Zigga token price...")
        
        # DEX Screener API endpoint for Zigga/SOL pair
        url = "https://api.dexscreener.com/latest/dex/pairs/solana/j25t3a5hsvecw71dpid5oi9kvzkjm5mujyrbsfpawpt1"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        
        if not data.get('pairs') or len(data['pairs']) == 0:
            print("❌ No Zigga price data available")
            return {}
        
        pair_data = data['pairs'][0]
        
        price_info = {
            'price_usd': float(pair_data.get('priceUsd', 0)),
            'price_change_24h': float(pair_data.get('priceChange', {}).get('h24', 0)),
            'volume_24h': float(pair_data.get('volume', {}).get('h24', 0)),
            'market_cap': float(pair_data.get('marketCap', 0)),
            'liquidity_usd': float(pair_data.get('liquidity', {}).get('usd', 0)),
            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        print(f"✅ Zigga Price: ${price_info['price_usd']:.8f}")
        print(f"   24h Change: {price_info['price_change_24h']:.2f}%")
        print(f"   24h Volume: ${price_info['volume_24h']:,.2f}")
        print(f"   Market Cap: ${price_info['market_cap']:,.2f}")
        
        return price_info
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error: {e}")
        return {}
    except Exception as e:
        print(f"❌ Error fetching Zigga price: {e}")
        return {}


# Example usage when run directly
if __name__ == "__main__":
    # Test the functions
    print("Testing get_yahoo_data()...")
    print("="*70)
    
    # Test 1: Crude Oil Futures (Simple)
    crude = get_yahoo_data("CLZ25.NYM", 30)
    print("\nCrude Oil - Simple (Last 5 days):")
    print(crude.tail())
    
    # Test 2: Crude Oil Futures (Comprehensive)
    print("\n" + "="*70)
    print("Testing get_yahoo_data_comprehensive()...")
    print("="*70)
    crude_comp = get_yahoo_data_comprehensive("CLZ25.NYM", 30)
    print("\nCrude Oil - Comprehensive (Last 5 days):")
    print(crude_comp.tail())
    
    # Test 3: Gold Futures
    print("\n" + "="*70)
    gold = get_yahoo_data("GC=F", 30)
    print("\nGold (Last 5 days):")
    print(gold.tail())
    
    # Test 4: Stock
    print("\n" + "="*70)
    aapl = get_yahoo_data("AAPL", 30)
    print("\nApple Stock (Last 5 days):")
    print(aapl.tail())
    
    # Test 5: Zigga Token
    print("\n" + "="*70)
    zigga_price = get_zigga_price()
    if zigga_price:
        print("\nZigga Token Price Info:")
        for key, value in zigga_price.items():
            print(f"   {key}: {value}")

