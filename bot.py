import time
import datetime
import random

TRAILING_STOP_LOSS_PCT = 0.005  # 0.5% trailing stop
CHECK_INTERVAL_SECONDS = 5  # shorter delay for demo purposes

def fetch_mock_price():
    base_price = 107000
    variation = random.uniform(-150, 150)
    return base_price + variation

def generate_mock_candles(entry_price):
    return [
        {'high': entry_price * 1.002, 'low': entry_price * 0.998, 'close': entry_price * 1.001},
        {'high': entry_price * 1.004, 'low': entry_price * 0.999, 'close': entry_price * 1.003},
        {'high': entry_price * 1.006, 'low': entry_price * 1.000, 'close': entry_price * 1.005},
        {'high': entry_price * 1.003, 'low': entry_price * 0.996, 'close': entry_price * 0.997},
    ]

def simulate_trailing_stop_long(entry_price, candles):
    peak_price = entry_price
    for i, candle in enumerate(candles):
        high = candle['high']
        low = candle['low']
        if high > peak_price:
            peak_price = high
        stop_price = peak_price * (1 - TRAILING_STOP_LOSS_PCT)
        if low <= stop_price:
            print(f"🔻 Trailing Stop Hit (LONG) | Exit Price: {stop_price:.2f} | Peak: {peak_price:.2f} | Candle {i+1}")
            return stop_price
    print(f"🏁 Target Reached (LONG) | Exit Price: {candles[-1]['close']:.2f}")
    return candles[-1]['close']

def simulate_trailing_stop_short(entry_price, candles):
    trough_price = entry_price
    for i, candle in enumerate(candles):
        low = candle['low']
        high = candle['high']
        if low < trough_price:
            trough_price = low
        stop_price = trough_price * (1 + TRAILING_STOP_LOSS_PCT)
        if high >= stop_price:
            print(f"🔻 Trailing Stop Hit (SHORT) | Exit Price: {stop_price:.2f} | Trough: {trough_price:.2f} | Candle {i+1}")
            return stop_price
    print(f"🏁 Target Reached (SHORT) | Exit Price: {candles[-1]['close']:.2f}")
    return candles[-1]['close']

def main():
    print("🚀 BTC Margin Scalping Bot Started (Live Loop)")
    direction = "long"  # Change to "short" for short trades

    while True:
        current_price = fetch_mock_price()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n🧠 {now} | Checking for trade setup | Price: {current_price:.2f}")

        # Mock condition: always take the trade
        print(f"✅ Trade setup confirmed ({direction.upper()}) | Entry Price: {current_price:.2f}")
        candles = generate_mock_candles(current_price)

        if direction == "long":
            exit_price = simulate_trailing_stop_long(current_price, candles)
        else:
            exit_price = simulate_trailing_stop_short(current_price, candles)

        profit = (exit_price - current_price) if direction == "long" else (current_price - exit_price)
        print(f"💰 Simulated {direction.upper()} Trade Profit: {profit:.2f} | Entry: {current_price:.2f} → Exit: {exit_price:.2f}")

        print("⏳ Sleeping until next trade check...\n")
        time.sleep(CHECK_INTERVAL_SECONDS)

main()
