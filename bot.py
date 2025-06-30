import time
import logging
from binance.client import Client
from binance.enums import *
from datetime import datetime, timedelta
import numpy as np
import os

# === CONFIG ===
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(API_KEY, API_SECRET)

SYMBOL = "BTCUSDT"
INTERVAL = Client.KLINE_INTERVAL_15MINUTE
START_TIME = int((datetime.utcnow() - timedelta(days=7)).timestamp() * 1000)

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
log = lambda msg: print(msg, flush=True) or logging.info(msg)

# === EMA CALCULATION ===
def calculate_ema(prices, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a = np.convolve(prices, weights, mode='full')[:len(prices)]
    return a[-1]

# === MAIN SIMULATION LOOP ===
def run_simulation():
    log("📊 Fetching historical data for 7-day simulation...")
    candles = client.get_klines(symbol=SYMBOL, interval=INTERVAL, startTime=START_TIME, limit=1000)
    closes = [float(c[4]) for c in candles]
    timestamps = [int(c[0]) for c in candles]

    trade_count = 0
    rejected_count = 0

    for i in range(50, len(closes)):
        current_price = closes[i]
        time_str = datetime.utcfromtimestamp(timestamps[i] / 1000).strftime('%Y-%m-%d %H:%M:%S')

        ema21 = np.mean(closes[i - 21:i])
        ema50 = np.mean(closes[i - 50:i])

        if current_price > ema21 and current_price > ema50:
            log(f"✅ Simulated BUY trade at {time_str} — Price: {current_price:.2f}")
            trade_count += 1
        else:
            reason = []
            if current_price <= ema21:
                reason.append("price below EMA-21")
            if current_price <= ema50:
                reason.append("price below EMA-50")
            log(f"❌ Trade Rejected at {time_str} — Reason: {', '.join(reason)}")
            rejected_count += 1

    log("📈 Simulation Complete")
    log(f"📌 Total Trades Simulated: {trade_count}")
    log(f"📌 Total Trades Rejected: {rejected_count}")

# === ENTRY POINT ===
if __name__ == "__main__":
    log("🤖 Starting 7-day BTCUSDT Trade Simulation...")
    run_simulation()
