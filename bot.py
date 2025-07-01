import ccxt
import pandas as pd
import time
import datetime
import logging
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from ta.momentum import StochRSIIndicator

# Constants
RESET_HOUR_UTC = 0
MAX_LOSS_STREAK = 3
MAX_DRAWDOWN_PERCENT = 10
RISK_PER_TRADE = 0.015  # 1.5%
RR_RATIO = 2
WAIT_TIME_SECONDS = 15 * 60
EMA_SHORT = 21
EMA_LONG = 50
STOCHRSI_PERIOD = 14
ATR_PERIOD = 14
TRADE_MONITOR_DURATION = 60 * 60  # 1 hour max monitoring for TP/SL hit

# Trading State
balance = 200.0
initial_balance = balance
trade_count = 0
loss_streak = 0

# Logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# Binance Setup
exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

def fetch_ohlcv(symbol="BTC/USDT", timeframe='15m', limit=150):
    data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

def add_indicators(df):
    df['ema_21'] = EMAIndicator(df['close'], window=EMA_SHORT).ema_indicator()
    df['ema_50'] = EMAIndicator(df['close'], window=EMA_LONG).ema_indicator()
    df['atr'] = AverageTrueRange(df['high'], df['low'], df['close'], window=ATR_PERIOD).average_true_range()
    stoch = StochRSIIndicator(df['close'], window=STOCHRSI_PERIOD)
    df['stochrsi_k'] = stoch.stochrsi_k()
    df['stochrsi_d'] = stoch.stochrsi_d()
    df['supertrend'] = (df['close'] > df['ema_21']) & (df['close'] > df['ema_50'])
    return df

def get_trade_signal(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    long_signal = (
        latest['supertrend']
        and latest['close'] > latest['ema_21'] > latest['ema_50']
        and latest['stochrsi_k'] > latest['stochrsi_d']
        and previous['stochrsi_k'] <= previous['stochrsi_d']
    )

    short_signal = (
        not latest['supertrend']
        and latest['close'] < latest['ema_21'] < latest['ema_50']
        and latest['stochrsi_k'] < latest['stochrsi_d']
        and previous['stochrsi_k'] >= previous['stochrsi_d']
    )

    if long_signal:
        return "LONG"
    elif short_signal:
        return "SHORT"
    return None

def should_reset():
    now_utc = datetime.datetime.now(datetime.UTC)
    return now_utc.hour == RESET_HOUR_UTC and trade_count != 0

def clear_trading_history():
    global balance, trade_count, loss_streak, initial_balance
    balance = 200.0
    initial_balance = balance
    trade_count = 0
    loss_streak = 0
    logging.info("🔄 Daily reset triggered. Trade history cleared.")

def risk_check():
    if loss_streak >= MAX_LOSS_STREAK:
        logging.warning("🛑 Max loss streak reached. Skipping trade.")
        return False
    if balance < initial_balance * (1 - MAX_DRAWDOWN_PERCENT / 100):
        logging.warning("🛑 Max drawdown reached. Skipping trade.")
        return False
    return True

def monitor_trade(symbol, entry, tp, sl, size, direction):
    global balance, trade_count, loss_streak

    start_time = time.time()
    outcome = None

    while time.time() - start_time < TRADE_MONITOR_DURATION:
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']

        if direction == "LONG":
            if price >= tp:
                outcome = "TP"
                break
            elif price <= sl:
                outcome = "SL"
                break
        else:  # SHORT
            if price <= tp:
                outcome = "TP"
                break
            elif price >= sl:
                outcome = "SL"
                break

        time.sleep(5)

    if outcome == "TP":
        profit = round(size * abs(tp - entry), 2)
        balance += profit
        loss_streak = 0
    elif outcome == "SL":
        loss = round(size * abs(sl - entry), 2)
        balance -= loss
        loss_streak += 1
        profit = -loss
    else:
        profit = 0  # No outcome
        logging.info("⏳ Trade expired without TP or SL being hit.")

    trade_count += 1

    logging.info(f"\n📉 Trade #{trade_count}: {direction} | Entry: {entry:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")
    logging.info(f"💰 Size: {size:.6f} | Profit: ${profit:.2f} | New Balance: ${balance:.2f}")
    logging.info(f"📉 Loss Streak: {loss_streak}")
    logging.info("⏳ Waiting 15 min for next signal...\n")

def main():
    global trade_count, loss_streak

    while True:
        try:
            if should_reset():
                clear_trading_history()

            if not risk_check():
                time.sleep(WAIT_TIME_SECONDS)
                continue

            df = fetch_ohlcv()
            df = add_indicators(df)
            signal = get_trade_signal(df)

            if not signal:
                logging.info("⚠️ No valid signal. Waiting 15 mins...\n")
                time.sleep(WAIT_TIME_SECONDS)
                continue

            entry = df.iloc[-1]['close']
            atr = df.iloc[-1]['atr']
            sl_distance = atr
            tp_distance = atr * RR_RATIO
            risk_dollars = RISK_PER_TRADE * balance
            size = round(risk_dollars / sl_distance, 6)

            if signal == "LONG":
                sl = entry - sl_distance
                tp = entry + tp_distance
            else:
                sl = entry + sl_distance
                tp = entry - tp_distance

            monitor_trade("BTC/USDT", entry, tp, sl, size, signal)

        except Exception as e:
            logging.error(f"❌ Error: {e}")

        time.sleep(WAIT_TIME_SECONDS)

if __name__ == "__main__":
    main()
