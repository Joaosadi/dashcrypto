from datetime import datetime, timezone
import sqlite3
import pandas as pd
import requests

BINANCE_KLINES_URL = "https://api.binance.us/api/v3/klines"
DATABASE = "crypto_historical_data.db"

def get_latest_db_timestamp():
    """Fetch the max timestamp (in milliseconds) currently stored in the DB."""
    with sqlite3.connect(DATABASE) as conn:
        result = pd.read_sql("SELECT MAX(time_close) FROM btc_price", conn)
    result = result.max().values[0]
    dt = datetime.fromisoformat(result)
    ms = int(dt.timestamp() * 1000)
    return ms


def fetch_binance_klines(symbol="BTCUSDT", interval="1d", start_time=None):
    """Fetch candlestick data directly from Binance public REST API."""
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": 1000,  # Max allowed per request
    }
    if start_time:
        # +1 ms so we don't duplicate the last existing candle
        params["startTime"] = start_time + 1

    response = requests.get(BINANCE_KLINES_URL, params=params)
    response.raise_for_status()
    data = response.json()

    if not data:
        return pd.DataFrame()

    # Parse Binance KLine Array Structure
    cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "close_time",
        "quote_asset_volume",
        "number_of_trades",
        "taker_buy_base_asset_volume",
        "taker_buy_quote_asset_volume",
        "ignore",
    ]

    df = pd.DataFrame(data, columns=cols)

    # Clean & Format Columns
    df["symbol"] = symbol
    df = df[["timestamp", "symbol", "open", "high", "low", "close", "volume"]]
    numeric_cols = ["open", "high", "low", "close", "volume"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)

    return df

def update_btc_database(db_path=DATABASE):
    """Main function to perform delta update."""
    with sqlite3.connect(db_path) as conn:
        last_ts = get_latest_db_timestamp()
        new_candles = fetch_binance_klines(
            symbol="BTCUSDT", interval="1d", start_time=last_ts
        )

        if new_candles.empty:
            return pd.DataFrame()

        # Insert new rows into database
        new_candles = new_candles.rename(columns={"timestamp": "time_close"})
        new_candles['time_close'] = pd.to_datetime(new_candles['time_close'], unit='ms', utc=True)
        new_candles = new_candles[["time_close", "close", "high", "low", "open"]]
        new_candles.to_sql("btc_price", conn, if_exists="append", index=False)
    
    return new_candles

if __name__ == "__main__":
    print("Starting automated Binance sync...")
    df = update_btc_database("crypto.db")
    print(df)