import time
import math
import logging
from datetime import datetime
from strategy import get_trade_signal
from binance_data import get_latest_price, get_historical_data

# === CONFIG ===
CAPITAL = 2500  # USD
RISK_PER_TRADE = 0.01  # 1%
LEVERAGE = 5
SYMBOL = 'BTC/USDT'
INTERVAL = '15m'

# === LOGGING ===
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger()

def calculate_position_size(entry_price, stop_loss_price):
    risk_amount = CAPITAL * RISK_PER_TRADE
    stop_loss_distance = abs(entry_price - stop_loss_price)

    if stop_loss_distance == 0:
        log.warning("Stop loss distance is 0. Cannot calculate position size.")
        return 0

    position_size = risk_amount / stop_loss_distance
    position_size = round(position_size, 4)  # ✅ allow fractional quantities

    log.info(f"🧮 Position sizing: Risk ${risk_amount:.2f} | Stop Δ {stop_loss_distance:.2f} | Size = {position_size:.4f} BTC")

    return position_size

def simulate_trade(entry_price, stop_loss_price, take_profit_price, direction):
    position_size = calculate_position_size(entry_price, stop_loss_price)

    if position_size <= 0:
        log.warning("❌ Trade skipped: position size too small or zero.")
        return

    trade_value = position_size * entry_price
    log.info(f"🟢 Simulated {direction.upper()} Trade | Entry: {entry_price:.2f} | Size: {position_size:.4f} BTC | Value: ${trade_value:.2f}")

    # Simulate profit/loss logic here...
    # For now, just pretend trade reached TP
    exit_price = take_profit_price
    pnl = (exit_price - entry_price) * position_size if direction == 'long' else (entry_price - exit_price) * position_size

    log.info(f"💰 Exit {direction.upper()} | Exit Price: {exit_price:.2f} | PnL: ${pnl:.2f}")

def run_bot():
    log.info("🚀 BTC Margin Scalping Bot Starting...")

    while True:
        log.info("🧠 Checking for trade setup...")

        candles = get_historical_data(SYMBOL, INTERVAL, limit=100)
        current_price = get_latest_price(SYMBOL)
        signal = get_trade_signal(candles)

        if signal:
            direction = signal['direction']
            entry_price = current_price
            stop_loss_price = signal['stop_loss']
            take_profit_price = signal['take_profit']

            simulate_trade(entry_price, stop_loss_price, take_profit_price, direction)
        else:
            log.info("⚪ No valid trade setup found.")

        log.info("⏳ Sleeping 15 minutes...\n")
        time.sleep(900)

if __name__ == "__main__":
    run_bot()
