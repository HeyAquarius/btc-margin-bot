import time
import datetime
import logging
from binance.client import Client
import pandas as pd
import ta

# Setup
api_key = "YOUR_API_KEY"
api_secret = "YOUR_API_SECRET"
client = Client(api_key, api_secret)
symbol = "BTCUSDT"
quantity = 0.05  # Just for simulation logs
sleep_interval = 60 * 15  # 15-minute intervals

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Simulation results
total_trades = 0
wins = 0
losses = 0
simulated_pnl = 0

def fetch_ohlcv(symbol, interval, limit=100):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df['close'] = df['close'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    return df

def calculate_indicators(df):
    df['EMA21'] = ta.trend.ema_indicator(df['close'], window=21)
    df['EMA50'] = ta.trend.ema_indicator(df['close'], window=50)
    df['SuperTrend'] = ta.trend.stc(df['close'], fillna=True)
    return df

def micro_confirmation(df_5m):
    df_5m['EMA9'] = ta.trend.ema_indicator(df_5m['close'], window=9)
    return df_5m['close'].iloc[-1] > df_5m['EMA9'].iloc[-1]

def should_trade(df_1h, df_15m, df_5m):
    price_15m = df_15m['close'].iloc[-1]
    ema21_15m = df_15m['EMA21'].iloc[-1]

    ema21_1h = df_1h['EMA21'].iloc[-1]
    ema50_1h = df_1h['EMA50'].iloc[-1]
    trend_up = df_1h['SuperTrend'].iloc[-1] > 0 and price_15m > ema21_1h and ema21_1h > ema50_1h

    micro_ok = micro_confirmation(df_5m)

    if not trend_up:
        return False, "📉 1H trend filter failed"
    if price_15m < ema21_15m:
        return False, "❌ Price below EMA-21 on 15M"
    if not micro_ok:
        return False, "🕵️‍♂️ 5M micro-confirmation failed"
    return True, "✅ All trade conditions met"

def simulate_trade(entry_price):
    global total_trades, wins, losses, simulated_pnl
    target = entry_price * 1.015
    stop = entry_price * 0.9925
    simulated_high = entry_price * 1.017
    simulated_low = entry_price * 0.991  # just for logic

    logging.info(f"📊 Simulating trade: Entry={entry_price:.2f} | Target={target:.2f} | Stop={stop:.2f}")

    if simulated_high >= target:
        pnl = (target - entry_price) * quantity
        wins += 1
        result = f"✅ Hit target | PnL +${pnl:.2f}"
    elif simulated_low <= stop:
        pnl = (stop - entry_price) * quantity
        losses += 1
        result = f"🛑 Hit stop | PnL ${pnl:.2f}"
    else:
        pnl = 0
        result = "⏸ No clear outcome"

    total_trades += 1
    simulated_pnl += pnl
    logging.info(f"📈 Result: {result} | Total PnL: ${simulated_pnl:.2f}")

def run_bot():
    while True:
        try:
            logging.info("🔄 Fetching data...")
            df_15m = calculate_indicators(fetch_ohlcv(symbol, '15m'))
            df_1h = calculate_indicators(fetch_ohlcv(symbol, '1h'))
            df_5m = calculate_indicators(fetch_ohlcv(symbol, '5m'))

            last_price = df_15m['close'].iloc[-1]
            allowed, reason = should_trade(df_1h, df_15m, df_5m)

            if allowed:
                logging.info(f"🚀 Trade triggered at {last_price:.2f}")
                simulate_trade(last_price)
            else:
                logging.info(f"❌ Trade rejected: {reason} | Price: {last_price:.2f}")

        except Exception as e:
            logging.error(f"❗️Error: {e}")

        time.sleep(sleep_interval)

if __name__ == "__main__":
    logging.info("🤖 Starting Phase 2 BTC margin scalping bot simulation...")
    run_bot()
