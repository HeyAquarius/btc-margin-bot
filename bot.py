import time
import logging
import math
from datetime import datetime
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = Client(API_KEY, API_SECRET)

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# === CONFIG ===
symbol = "BTCUSDT"
quantity = 0.001  # Simulated amount
leverage = 5
interval = "15m"

# === Trade tracking ===
open_trade = None

# === Define trade signal logic here ===
def get_trade_signal(df_1h, df_15m):
    """
    Simulates a trend-based strategy:
    - LONG: If 1h close > 1h EMA and 15m shows bullish candle
    - SHORT: If 1h close < 1h EMA and 15m shows bearish candle
    Returns: "LONG", "SHORT", or None
    """

    try:
        price_1h = float(df_1h[-1]["close"])
        price_15m = float(df_15m[-1]["close"])
        ema = sum([float(candle["close"]) for candle in df_1h[-5:]]) / 5

        if price_1h > ema and float(df_15m[-1]["close"]) > float(df_15m[-2]["close"]):
            return "LONG"
        elif price_1h < ema and float(df_15m[-1]["close"]) < float(df_15m[-2]["close"]):
            return "SHORT"
        else:
            return None
    except Exception as e:
        logging.warning(f"Error in get_trade_signal(): {e}")
        return None

# === Helper to fetch candles ===
def get_klines(symbol, interval, limit=100):
    data = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    return [{"time": x[0], "open": x[1], "high": x[2], "low": x[3], "close": x[4]} for x in data]

# === Main loop ===
logging.info("🚀 Phase 2 BTC margin scalping bot started – live style loop")

while True:
    try:
        df_15m = get_klines(symbol, "15m", 50)
        df_1h = get_klines(symbol, "1h", 50)
        current_price = float(df_15m[-1]["close"])

        logging.info("🧠 Checking for trade setup | Price: %.2f", current_price)

        signal = get_trade_signal(df_1h, df_15m)

        if signal:
            entry_price = current_price
            peak_price = entry_price
            trailing_stop_pct = 0.004  # 0.4%
            trailing_triggered = False

            logging.info("✅ Trade setup confirmed (%s) | Entry Price: %.2f", signal, entry_price)

            for candle in range(1, 4):  # Simulate 3 candles ahead
                time.sleep(1)  # Simulated delay

                next_candle = get_klines(symbol, "15m", 1)[-1]
                new_price = float(next_candle["close"])

                if signal == "LONG":
                    peak_price = max(peak_price, new_price)
                    stop_price = peak_price * (1 - trailing_stop_pct)
                    if new_price <= stop_price:
                        logging.info("🔻 Trailing Stop Hit (LONG) | Exit Price: %.2f | Peak: %.2f | Candle %d", new_price, peak_price, candle)
                        break
                elif signal == "SHORT":
                    peak_price = min(peak_price, new_price)
                    stop_price = peak_price * (1 + trailing_stop_pct)
                    if new_price >= stop_price:
                        logging.info("🔺 Trailing Stop Hit (SHORT) | Exit Price: %.2f | Trough: %.2f | Candle %d", new_price, peak_price, candle)
                        break

            profit = round((new_price - entry_price) * quantity * leverage, 2)
            if signal == "SHORT":
                profit *= -1

            logging.info("💰 Simulated %s Trade Profit: %.2f | Entry: %.2f → Exit: %.2f", signal, profit, entry_price, new_price)

        else:
            logging.info("❌ Trade rejected: 📉 No valid signal at this time")

        logging.info("⏳ Sleeping 15 minutes until next candle close...\n")
        time.sleep(60 * 15)

    except Exception as e:
        logging.warning("⚠️ Error in main loop: %s", str(e))
        time.sleep(60)
