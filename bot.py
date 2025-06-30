
import os
import time
import pandas as pd
from dotenv import load_dotenv
from binance.client import Client
from binance.exceptions import BinanceAPIException
from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import StochRSIIndicator
from ta.volatility import AverageTrueRange


# Load environment variables
load_dotenv()
API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")

client = Client(API_KEY, API_SECRET)
print("🔑 Binance client initialized")

symbol = "BTCUSDT"
interval_15m = Client.KLINE_INTERVAL_15MINUTE
interval_1h = Client.KLINE_INTERVAL_1HOUR

def get_klines(symbol, interval, limit=100):
    try:
        raw = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        df = pd.DataFrame(raw, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        df = df[['open', 'high', 'low', 'close', 'volume']].astype(float)
        return df
    except BinanceAPIException as e:
        print("Binance API error:", e)
        return None
    except Exception as e:
        print("❌ Error fetching klines:", e)
        return None

def compute_indicators(df_15m, df_1h):
    try:
        stoch = StochRSIIndicator(df_15m['close'], window=14)
        df_15m['stoch_rsi_k'] = stoch.stochrsi_k()
        df_15m['stoch_rsi_d'] = stoch.stochrsi_d()
        df_15m['atr_15m'] = AverageTrueRange(df_15m['high'], df_15m['low'], df_15m['close']).average_true_range()

        ema_21 = EMAIndicator(df_1h['close'], window=21)
        ema_50 = EMAIndicator(df_1h['close'], window=50)
        adx = ADXIndicator(df_1h['high'], df_1h['low'], df_1h['close'], window=14)
        atr_1h = AverageTrueRange(df_1h['high'], df_1h['low'], df_1h['close']).average_true_range()

        df_1h['ema21'] = ema_21.ema_indicator()
        df_1h['ema50'] = ema_50.ema_indicator()
        df_1h['adx'] = adx.adx()
        df_1h['atr_1h'] = atr_1h

        return df_15m, df_1h
    except Exception as e:
        print("❌ Error computing indicators:", e)
        return df_15m, df_1h

def check_trade_signal(df_15m, df_1h):
    try:
        latest_15m = df_15m.iloc[-1]
        latest_1h = df_1h.iloc[-1]

        trend_up = latest_1h['close'] > latest_1h['ema21'] and latest_1h['close'] > latest_1h['ema50']
        trend_down = latest_1h['close'] < latest_1h['ema21'] and latest_1h['close'] < latest_1h['ema50']
        strong_trend = latest_1h['adx'] > 20 and (latest_1h['atr_1h'] / latest_1h['close']) > 0.006
        stoch_trigger = latest_15m['stoch_rsi_k'] < 20 and latest_15m['stoch_rsi_d'] < 20

        print(f"Trend Up: {trend_up}, Trend Down: {trend_down}, Strong Trend: {strong_trend}, Stoch Trigger: {stoch_trigger}")

        if trend_up and strong_trend and stoch_trigger:
            print("📈 Long signal detected.")
            return "long"
        elif trend_down and strong_trend and stoch_trigger:
            print("📉 Short signal detected.")
            return "short"
        else:
            print("🟡 No signal at this time.")
            return None
    except Exception as e:
        print("❌ Error checking trade signal:", e)
        return None

def main_loop():
    print("🚀 Bot started. Entering main loop.")
    while True:
        try:
            print("📊 Checking for trade signals...")
            df_15m = get_klines(symbol, interval_15m)
            df_1h = get_klines(symbol, interval_1h)

            if df_15m is not None and df_1h is not None:
                df_15m, df_1h = compute_indicators(df_15m, df_1h)
                check_trade_signal(df_15m, df_1h)
            else:
                print("⚠️ Could not fetch candle data.")
        except Exception as e:
            print("❌ Unexpected error in main loop:", e)

        time.sleep(300)

if __name__ == "__main__":
    print("🚀 About to enter main_loop()")
    main_loop()
