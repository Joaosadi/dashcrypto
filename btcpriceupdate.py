from datetime import datetime, timezone
import sqlite3
import pandas as pd
import requests

DATABASE = "crypto_historical_data.db"

def get_latest_db_timestamp():
    """Fetch the max timestamp (in seconds) stored in SQLite to align with Coinbase."""
    with sqlite3.connect(DATABASE) as conn:
        result = pd.read_sql("SELECT MAX(time_close) FROM btc_price", conn)

    raw_val = result.iloc[0, 0]

    # Handle empty database
    if pd.isna(raw_val) or raw_val is None:
        return None

    # Handle string ISO format or existing integer timestamps
    if isinstance(raw_val, str):
        # Convert string to UTC datetime
        dt = pd.to_datetime(raw_val, utc=True)
        return int(dt.timestamp())
    elif isinstance(raw_val, (int, float)):
        # If stored as milliseconds in DB, convert to seconds
        return int(raw_val // 1000) if raw_val > 1e11 else int(raw_val)

    return None


def fetch_btc_daily_coinbase(start_time_sec=None):
    """Fetch daily BTC candles from Coinbase starting from the latest DB timestamp."""
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"

    # Granularity 86400 = 1 Day
    params = {"granularity": 86400}

    # Pass ISO 8601 start date if we already have records in DB
    if start_time_sec:
        start_iso = datetime.fromtimestamp(start_time_sec, tz=timezone.utc).isoformat()
        params["start"] = start_iso

    headers = {"User-Agent": "CryptoDashboard/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not data:
            return pd.DataFrame()

        # Coinbase returns: [time, low, high, open, close, volume]
        cols = ["time_close", "low", "high", "open", "close", "volume"]
        df = pd.DataFrame(data, columns=cols)

        # Convert Unix epoch (seconds) to UTC ISO string format for SQLite
        df["time_close"] = pd.to_datetime(
            df["time_close"], unit="s", utc=True
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

        # Sort ascending by timestamp
        df = df.sort_values("time_close").reset_index(drop=True)

        # Filter out the existing max record if it returned in the API response
        if start_time_sec:
            last_date_str = datetime.fromtimestamp(
                start_time_sec, tz=timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
            df = df[df["time_close"] > last_date_str].reset_index(drop=True)

        return df

    except Exception as e:
        print(f"Failed to fetch data from Coinbase: {e}")
        return pd.DataFrame()


# --- USAGE / EXECUTION FLOW ---
def sync_latest_btc_data():
    latest_sec = get_latest_db_timestamp()
    new_data = fetch_btc_daily_coinbase(start_time_sec=latest_sec).drop("volume", axis = 1)

    if not new_data.empty:
        with sqlite3.connect(DATABASE) as conn:
            new_data.to_sql(
                "btc_price", conn, if_exists="append", index=False
            )
        print(f"Successfully appended {len(new_data)} new candle(s).")
    else:
        print("Database is already up to date.")

if __name__ == "__main__":
    sync_latest_btc_data()