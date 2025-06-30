import logging
import time
import datetime
from binance.client import Client

# Initialize Binance Client
API_KEY = 'your_api_key'
API_SECRET = 'your_api_secret'
client = Client(API_KEY, API_SECRET)

# Constants
RISK_PER_TRADE = 0.01  # 1% of balance
RESET_HOUR_UTC = 0     # Midnight UTC
TRADE_INTERVAL = 15 * 60  # 15 minutes

# State
balance = 200.00  # Starting balance for simulation
trade_count = 0
loss_streak = 0

def get_signal():
    # Dummy signal generator for testing
    from random import choice
    return choice(["long", "short", "none"])

def simulate_trade(entry_price, sl_price, direction):
    global balance, trade_count, loss_streak
    trade_count += 1

    # Calculate size based on risk
    stop_distance = abs(entry_price - sl_price)
    size = (balance * RISK_PER_TRADE) / stop_distance

    # Calculate TP based on 2:1 reward:risk
    if direction == "long":
        tp = entry_price + 2 * (entry_price - sl_price)
        pnl = (tp - entry_price) * size
    else:
        tp = entry_price - 2 * (sl_price - entry_price)
        pnl = (entry_price - tp) * size

    # Simulate a win for testing
    result = "win"
    balance += pnl

    if result == "win":
        loss_streak = 0
    else:
        loss_streak += 1

    logging.info(f"\n📉 Trade #{trade_count}: {direction.upper()} | Entry: {entry_price:.2f} | SL: {sl_price:.2f} | TP: {tp:.2f}")
    logging.info(f"💰 Size: {size:.6f} | Profit: ${pnl:.2f} | New Balance: ${balance:.2f}")
    logging.info(f"📉 Loss Streak: {loss_streak}")
    logging.info("⏳ Waiting 15 min for next signal...\n")

def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

    while True:
        now_utc = datetime.datetime.utcnow()

        if now_utc.hour == RESET_HOUR_UTC and trade_count != 0:
            trade_count = 0
            logging.info("🔄 Resetting daily trade count.")

        signal = get_signal()

        if signal == "none":
            logging.warning("⚠️ No clear trend. Waiting 15 mins...\n")
        else:
            # Simulate prices (for demo)
            current_price = 107000.00
            sl = current_price - 200 if signal == "long" else current_price + 200
            simulate_trade(current_price, sl, signal)

        time.sleep(TRADE_INTERVAL)

if __name__ == "__main__":
    main()
