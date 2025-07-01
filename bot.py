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
WAIT_TIME_SECONDS = 15 * 60  # 15 minutes
EMA_SHORT = 21
EMA_LONG = 50
STOCHRSI_PERIOD = 14
ATR_PERIOD = 14

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
    stochrsi = StochRSIIndicator(df['close'], window=STOCHRSI_PERIOD)
    df['stochrsi_k'] = stochrsi.stochrsi_k()
    df['stochrsi_d'] = stochrsi.stochrsi_d()
    df['supertrend'] = (df['close'] > df['ema_21']) & (df['close'] > df['ema_50'])
    return df

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

def get_trade_signal(df):
    latest = df.iloc[-1]
    previous = df.iloc[-2]

    uptrend = latest['supertrend']
    downtrend = not latest['supertrend']

    long_signal = (
        uptrend and
        latest['close'] > latest['ema_21'] > latest['ema_50'] and
        latest['stochrsi_k'] > latest['stochrsi_d'] and
        previous['stochrsi_k'] <= previous['stochrsi_d']
    )

    short_signal = (
        downtrend and
        latest['close'] < latest['ema_21'] < latest['ema_50'] and
        latest['stochrsi_k'] < latest['stochrsi_d'] and
        previous['stochrsi_k'] >= previous['stochrsi_d']
    )

    if long_signal:
        return "LONG"
    elif short_signal:
        return "SHORT"
    else:
        return None

def simulate_trade(entry_price, atr, direction):
    global balance, trade_count, loss_streak

    sl_distance = atr
    tp_distance = atr * RR_RATIO
    risk_amount = RISK_PER_TRADE * balance
    size = round(risk_amount / sl_distance, 6)

    if direction == "LONG":
        tp = entry_price + tp_distance
        sl = entry_price - sl_distance
    else:
        tp = entry_price - tp_distance
        sl = entry_price + sl_distance

    # Simulated outcome (replace later with real price checks if needed)
    win = random.choice([True, False])

    if win:
        profit = round(size * tp_distance, 2)
        balance += profit
        loss_streak = 0
    else:
        loss = round(size * sl_distance, 2)
        balance -= loss
        loss_streak += 1
        profit = -loss

    trade_count += 1

    logging.info(f"\n📉 Trade #{trade_count}: {direction} | Entry: {entry_price:.2f} | SL: {sl:.2f} | TP: {tp:.2f}")
    logging.info(f"💰 Size: {size} | Profit: ${profit:.2f} | New Balance: ${balance:.2f}")
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
            direction = get_trade_signal(df)

            if not direction:
                logging.info("⚠️ No clear trend. Waiting 15 mins...\n")
                time.sleep(WAIT_TIME_SECONDS)
                continue

            entry_price = df.iloc[-1]['close']
            atr = df.iloc[-1]['atr']
            simulate_trade(entry_price, atr, direction)

        except Exception as e:
            logging.error(f"❌ Error: {e}")
        
        time.sleep(WAIT_TIME_SECONDS)

if __name__ == "__main__":
    main()
