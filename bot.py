import ccxt
import time
import math
import logging
from datetime import datetime
import os

# === CONFIGURATION ===
RISK_PER_TRADE = 0.01
LEVERAGE = 5
TIMEFRAME = '15m'
SYMBOL = 'BTC/USDT'
SLEEP_INTERVAL = 60 * 15  # 15 minutes

# Initialize logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === CONNECT TO BINANCE ===
exchange = ccxt.binance({
    'apiKey': os.environ.get('BINANCE_API_KEY'),
    'secret': os.environ.get('BINANCE_API_SECRET'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future',
        'adjustForTimeDifference': True,
    }
})
exchange.set_leverage(LEVERAGE, SYMBOL)

balance = 200  # starting simulated balance
trade_count = 0

def fetch_ohlcv():
    return exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=50)

def calculate_ema(prices, period):
    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_atr(candles, period=14):
    trs = []
    for i in range(1, len(candles)):
        high = candles[i][2]
        low = candles[i][3]
        prev_close = candles[i - 1][4]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        trs.append(tr)
    return sum(trs[-period:]) / period

def get_trade_signal(candles):
    closes = [c[4] for c in candles]
    ema_21 = calculate_ema(closes, 21)
    ema_50 = calculate_ema(closes, 50)
    current_price = closes[-1]
    atr = calculate_atr(candles)

    if current_price > ema_21 and current_price > ema_50:
        return 'long', current_price, atr
    elif current_price < ema_21 and current_price < ema_50:
        return 'short', current_price, atr
    else:
        return None, current_price, atr

def calculate_position_size(balance, entry_price, sl_price):
    risk_amount = balance * RISK_PER_TRADE
    stop_loss_distance = abs(entry_price - sl_price)
    if stop_loss_distance == 0:
        return 0
    position_size = risk_amount / stop_loss_distance
    return position_size

def simulate_trade(direction, entry_price, atr):
    global balance, trade_count

    trail_stop_pct = 1.0  # 1% trailing
    tp_multiplier = 1.5   # Take profit = 1.5x ATR

    if direction == 'long':
        sl = entry_price - atr
        tp = entry_price + (atr * tp_multiplier)
    else:
        sl = entry_price + atr
        tp = entry_price - (atr * tp_multiplier)

    size = calculate_position_size(balance, entry_price, sl)
    if size <= 0:
        logging.info("❌ Trade rejected: Position size too small.")
        return

    price_movement = tp if direction == 'long' else tp
    profit = abs(price_movement - entry_price) * size
    if direction == 'short':
        profit = -profit if price_movement > entry_price else profit

    balance += profit
    trade_count += 1

    logging.info(f"📈 Trade #{trade_count}: {direction.upper()} | Entry: {entry_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")
    logging.info(f"💰 Size: {size:.6f} | Profit: ${profit:.2f} | New Balance: ${balance:.2f}")

# === MAIN LOOP ===
logging.info("🚀 Phase 2 BTC margin scalping bot started - live style loop")

while True:
    try:
        candles = fetch_ohlcv()
        signal, entry_price, atr = get_trade_signal(candles)

        if not signal:
            logging.info(f"🤷 No setup confirmed | Price: {entry_price:.2f}")
        else:
            logging.info(f"✅ Trade setup confirmed ({signal.upper()}) | Entry Price: {entry_price:.2f}")
            simulate_trade(signal, entry_price, atr)

    except Exception as e:
        logging.error(f"❌ Error: {str(e)}")

    logging.info("⏳ Waiting 15 min for next signal...\n")
    time.sleep(SLEEP_INTERVAL)
