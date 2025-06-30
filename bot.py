import math
import time
import logging
from datetime import datetime
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException

# ─── CONFIGURATION ─────────────────────────────────────────────────────────────
API_KEY = 'your_api_key_here'
API_SECRET = 'your_api_secret_here'
SYMBOL = "BTCUSDT"
LEVERAGE = 5
STARTING_BALANCE = 200
RISK_PER_TRADE = 0.01  # 1% risk per trade
MAX_TRADES_PER_DAY = 100
RESET_HOUR_UTC = 0  # Reset trade count at 00:00 UTC daily

# ─── INITIALIZATION ────────────────────────────────────────────────────────────
client = Client(API_KEY, API_SECRET)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
account_balance = STARTING_BALANCE
trade_count = 0

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

def get_klines(symbol, interval, limit=100):
    try:
        return client.get_klines(symbol=symbol, interval=interval, limit=limit)
    except BinanceAPIException as e:
        logging.error(f"Kline fetch failed: {e}")
        return []

def calculate_atr(candles, period=14):
    trs = []
    for i in range(1, len(candles)):
        high = float(candles[i][2])
        low = float(candles[i][3])
        close_prev = float(candles[i - 1][4])
        tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
        trs.append(tr)
    return sum(trs[-period:]) / period if len(trs) >= period else 0

def get_trend(candles):
    if len(candles) < 50:
        return None, None
    close = float(candles[-1][4])
    ema_21 = sum(float(candles[i][4]) for i in range(-21, 0)) / 21
    ema_50 = sum(float(candles[i][4]) for i in range(-50, 0)) / 50
    if close > ema_21 and close > ema_50:
        return "long", close
    elif close < ema_21 and close < ema_50:
        return "short", close
    return None, close

def calculate_position_size(balance, stop_loss_dist, risk_percent):
    risk_amount = balance * risk_percent
    if stop_loss_dist == 0:
        return 0
    size = risk_amount / stop_loss_dist
    return round(size, 6)

def simulate_trade(entry_price, stop_loss, direction, size):
    stop_dist = abs(entry_price - stop_loss)
    if direction == "long":
        tp = entry_price + (2 * stop_dist)
        pnl = (tp - entry_price) * size
    else:
        tp = entry_price - (2 * stop_dist)
        pnl = (entry_price - tp) * size
    return tp, round(pnl, 2)

def reset_daily_trades():
    global trade_count
    if datetime.utcnow().hour == RESET_HOUR_UTC and trade_count != 0:
        trade_count = 0
        logging.info("🔁 Trade count reset for new day.")

# ─── MAIN LOOP ─────────────────────────────────────────────────────────────────

def run_bot():
    global trade_count, account_balance
    logging.info("🚀 Bot started.")
    while True:
        reset_daily_trades()
        if trade_count >= MAX_TRADES_PER_DAY:
            logging.info("📛 Trade limit reached. Sleeping until next day.")
            time.sleep(900)
            continue

        candles = get_klines(SYMBOL, Client.KLINE_INTERVAL_15MINUTE)
        if not candles:
            time.sleep(60)
            continue

        direction, entry_price = get_trend(candles)
        if not direction:
            logging.info("⚠️ No clear trend. Waiting 15 mins...")
            time.sleep(900)
            continue

        atr = calculate_atr(candles)
        if atr == 0:
            logging.info("⚠️ ATR is zero. Skipping.")
            time.sleep(900)
            continue

        # Define stop-loss as recent price ± ATR
        stop_loss = entry_price - atr if direction == "long" else entry_price + atr
        stop_dist = abs(entry_price - stop_loss)
        size = calculate_position_size(account_balance, stop_dist, RISK_PER_TRADE)
        tp, profit = simulate_trade(entry_price, stop_loss, direction, size)

        account_balance += profit
        trade_count += 1

        # ✅ LOGGING (clean, multi-line-safe)
        logging.info("📈 Trade #{}: {} | Entry: {:.2f} | SL: {:.2f} | TP: {:.2f}".format(
            trade_count, direction.upper(), entry_price, stop_loss, tp))
        logging.info("💰 Size: {} | Profit: ${:.2f} | New Balance: ${:.2f}".format(
            size, profit, account_balance))
        logging.info("⏳ Waiting 15 min for next signal...\n")

        time.sleep(900)

# ─── START BOT ─────────────────────────────────────────────────────────────────
run_bot()
