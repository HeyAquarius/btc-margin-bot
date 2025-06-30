import time
import logging
import datetime as dt
import pandas as pd
import requests

# === SETUP ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Constants
SYMBOL = "BTCUSDT"
INTERVAL_15M = "15m"
INTERVAL_1H = "1h"
LIMIT = 100
API_URL = "https://api.binance.com/api/v3/klines"

# === FETCHING DATA ===
def fetch_klines(symbol, interval, limit=100):
    url = f"{API_URL}?symbol={symbol}&interval={interval}&limit={limit}"
    response = requests.get(url)
    data = response.json()
    df = pd.DataFrame(data, columns=[
        'time','open','high','low','close','volume',
        'close_time','quote_asset_volume','num_trades',
        'taker_buy_base_vol','taker_buy_quote_vol','ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    return df

# === STRATEGY CONDITIONS ===
def calculate_ema(df, period):
    return df['close'].ewm(span=period).mean()

def is_uptrend(df_1h):
    ema_21 = calculate_ema(df_1h, 21)
    ema_50 = calculate_ema(df_1h, 50)
    uptrend = df_1h['close'].iloc[-1] > ema_21.iloc[-1] and df_1h['close'].iloc[-1] > ema_50.iloc[-1]
    return uptrend

def is_downtrend(df_1h):
    ema_21 = calculate_ema(df_1h, 21)
    ema_50 = calculate_ema(df_1h, 50)
    downtrend = df_1h['close'].iloc[-1] < ema_21.iloc[-1] and df_1h['close'].iloc[-1] < ema_50.iloc[-1]
    return downtrend

# === SIMULATE TRADE ===
def simulate_trade():
    logging.info("🧠 Checking for trade setup...")

    # Fetch latest data
    df_15m = fetch_klines(SYMBOL, INTERVAL_15M, LIMIT)
    df_1h = fetch_klines(SYMBOL, INTERVAL_1H, LIMIT)

    current_price = df_15m['close'].iloc[-1]

    if is_uptrend(df_1h):
        logging.info(f"✅ Uptrend detected — Simulating LONG trade | Price: {current_price}")
    elif is_downtrend(df_1h):
        logging.info(f"✅ Downtrend detected — Simulating SHORT trade | Price: {current_price}")
    else:
        logging.info(f"❌ Trade rejected — ❗ 1H trend filter failed | Price: {current_price}")

# === MAIN LOOP ===
if __name__ == "__main__":
    logging.info("🚀 Phase 2 BTC margin scalping bot started — live style loop")
    while True:
        try:
            simulate_trade()
        except Exception as e:
            logging.error(f"⚠️ Error during trade simulation: {e}")

        logging.info("⏳ Sleeping 15 minutes until next candle close...\n")
        time.sleep(15 * 60)  # Sleep for 15 minutes
