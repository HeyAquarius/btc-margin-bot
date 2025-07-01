import datetime
import time
import logging
import random

# Constants
RESET_HOUR_UTC = 0
MAX_LOSS_STREAK = 3
MAX_DRAWDOWN_PERCENT = 10
WAIT_TIME_SECONDS = 15 * 60  # 15 minutes

# Trading State
trade_count = 0
balance = 200.0
loss_streak = 0
initial_balance = balance

# Logger setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

def clear_trading_history():
    global trade_count, balance, loss_streak, initial_balance
    trade_count = 0
    balance = 200.0
    loss_streak = 0
    initial_balance = balance
    logging.info("🔄 Daily reset triggered. Trade history cleared.")

def should_reset():
    now_utc = datetime.datetime.now(datetime.UTC)
    return now_utc.hour == RESET_HOUR_UTC and trade_count != 0

def trend_is_clear():
    # Placeholder for actual trend detection logic
    return random.choice([True, False])

def get_trade_direction():
    return random.choice(["LONG", "SHORT"])

def calculate_trade(entry_price, direction):
    tp = entry_price * (1.02 if direction == "LONG" else 0.98)
    sl = entry_price * (0.98 if direction == "LONG" else 1.02)
    return round(tp, 2), round(sl, 2)

def execute_trade(entry_price, tp, sl, direction):
    global trade_count, balance, loss_streak

    trade_count += 1
    size = round(balance * 0.00005 + trade_count * 0.00002, 6)
    profit = round(size * entry_price * 0.02, 2)  # Assume 2% win per trade
    balance += profit
    loss_streak = 0  # Reset loss streak on win

    logging.info(f"\n📉 Trade #{trade_count}: {direction} | Entry: {entry_price} | SL: {sl} | TP: {tp}")
    logging.info(f"💰 Size: {size} | Profit: ${profit} | New Balance: ${round(balance, 2)}")
    logging.info(f"📉 Loss Streak: {loss_streak}")
    logging.info("⏳ Waiting 15 min for next signal...\n")

def risk_check():
    if loss_streak >= MAX_LOSS_STREAK:
        logging.warning("🛑 Max loss streak reached. Skipping trade.")
        return False
    if balance < initial_balance * (1 - MAX_DRAWDOWN_PERCENT / 100):
        logging.warning("🛑 Max drawdown reached. Skipping trade.")
        return False
    return True

def main():
    global trade_count, balance, loss_streak

    while True:
        now_utc = datetime.datetime.now(datetime.UTC)

        # Daily Reset
        if should_reset():
            clear_trading_history()

        # Wait if no clear trend
        if not trend_is_clear():
            logging.info("⚠️ No clear trend. Waiting 15 mins...\n")
            time.sleep(WAIT_TIME_SECONDS)
            continue

        if not risk_check():
            time.sleep(WAIT_TIME_SECONDS)
            continue

        # Simulate trade
        entry_price = 107000.00  # Placeholder fixed price
        direction = get_trade_direction()
        tp, sl = calculate_trade(entry_price, direction)
        execute_trade(entry_price, tp, sl, direction)

        time.sleep(WAIT_TIME_SECONDS)

if __name__ == "__main__":
    main()
