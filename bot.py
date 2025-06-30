import math
import time
import logging
from datetime import datetime, timedelta
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
RESET_HOUR_UTC = 0
FAILSAFE_TRIGGER_LOSS_STREAK = 3

# ─── INITIALIZATION ────────────────────────────────────────────────────────────
client = Client(API_KEY, API_SECRET)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

account_balance = STARTING_BALANCE
trade_count = 0
loss_streak = 0
failsafe_until = None

# ─── HELPER FUNCTIONS ──────────────────────────────────────────────────────────

def retry(func, max_attempts=3, delay=5):
    for attempt in range(max_attempts):
        try:
            return func()
        except BinanceAPIException as e:
            logging.warning(f"Attempt {attempt+1} failed: {e}")
            time.sleep(delay)
    logging.error("Max retries exceeded.")
    return None

def get_klines(symbol, interval, limit=100):
    return retry(lambda: client.get_klines(symbol=symbol, interval=interval, limit=limit)) or []

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
    if direction == "long":
        tp = entry_price + (entry_price - stop_loss)
        result = "win" if tp > entry_price else "loss"
        pnl = (tp - entry_price) * size
    else:
        tp = entry_price - (stop_loss - entry_price)
        result = "win" if tp < entry_price else "loss"
        pnl = (entry_price - tp) * size
    return tp, round(pnl, 2), result

def reset_daily_trades():
    global trade_count
    if datetime.utcnow().hour == RESET_HOUR_UTC and trade_count != 0:
        trade_count = 0
        logging.info("🔁 Trade count reset for new day.")

# ─── MAIN LOOP ─────────────────────────────────────────────────────────────────

def run_bot():
    global trade_count, account_balance, loss_streak, failsafe_until

    logging.info("🚀 Bot started.")
    while True:
        now = datetime.utcnow()
        reset_daily_trades()

        # ─── Failsafe check ─────────────────────────────
        if failsafe_until and now < failsafe_until:
            mins = int((failsafe_until - now).total_seconds() / 60)
            logging.warning(f"🚨 Failsafe triggered. Sleeping for {mins} min.")
            time.sleep(300)
            continue

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
            logging.info("⚠️ No clear trend. Waiting...")
            time.sleep(900)
            continue

        atr = calculate_atr(candles)
        if atr == 0:
            logging.info("⚠️ ATR is zero. Skipping.")
            time.sleep(900)
            continue

        stop_loss = entry_price - atr if direction == "long" else entry_price + atr
        stop_dist = abs(entry_price - stop_loss)
        size = calculate_position_size(account_balance, stop_dist, RISK_PER_TRADE)
        tp, profit, result = simulate_trade(entry_price, stop_loss, direction, size)

        if result == "win":
            loss_streak = 0
        else:
            loss_streak += 1
            if loss_streak >= FAILSAFE_TRIGGER_LOSS_STREAK:
                failsafe_until = now + timedelta(hours=24)
                logging.warning("🚫 3-loss streak detected. Pausing for 24h.")

        account_balance += profit
        trade_count += 1

        logging.info(f"📈 Trade #{trade_count}: {direction.upper()} | Entry: {entry_price:.2f} | SL: {stop_loss:.2f} | TP: {tp:.2f}")
        logging.info(f"💰 Size: {size} | Profit: ${profit:.2f} | New Balance: ${account_balance:.2f}")
        logging.info(f"📉 Loss Streak: {loss_streak}")
        logging.info("⏳ Waiting 15 min for next signal...\n")

        time.sleep(900)

# ─── START BOT ─────────────────────────────────────────────────────────────────
run_bot()
