import ccxt, time, json, os, csv, threading
from decimal import Decimal, getcontext, ROUND_DOWN
from datetime import datetime
import pandas as pd
import ta
import requests

TELEGRAM_TOKEN = '8072613829:AAESNMnZdvNyycZd4DfRV-kHRE4JTFcQl7U'
TELEGRAM_CHAT_ID = 455597450

def send_telegram(msg):
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage'
        data = {'chat_id': TELEGRAM_CHAT_ID, 'text': msg}
        requests.post(url, data=data)
    except Exception as e:
        print(f"[TELEGRAM ERROR] Failed to send alert: {e}")

getcontext().prec = 12
getcontext().rounding = ROUND_DOWN

# ── CONFIG ─────────────────────────────────────────────────────────
SYMBOL          = 'BTC/USDT'
TIMEFRAME       = '15m'
RISK_PER_TRADE  = Decimal('0.01')
MAX_DRAWDOWN    = Decimal('0.10')
MAX_LOSS_STREAK = 3
FEE_RATE        = Decimal('0.0004')
MIN_ATR         = Decimal('0.5')
LEVERAGE_LIMIT  = Decimal('5')
CHECK_INTERVAL  = 5

STATE_FILE      = 'bot_state.json'
TRADE_LOG_FILE  = 'trade_log.csv'
lock            = threading.Lock()

# ── EXCHANGE ───────────────────────────────────────────────────────
exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
market   = exchange.load_markets()[SYMBOL]

try:
    exchange.set_leverage(int(LEVERAGE_LIMIT), SYMBOL)
except Exception as e:
    print(f"[WARN] set_leverage failed ({e}). Continuing in paper mode.")

lot_step = None
for f in market['info']['filters']:
    if f['filterType'] == 'LOT_SIZE':
        lot_step = Decimal(f['stepSize'])
        break
if lot_step is None:
    raise ValueError("LOT_SIZE stepSize not found.")

min_qty = Decimal(market['limits']['amount']['min'])

# ── STATE ──────────────────────────────────────────────────────────
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            d = json.load(f)
            d['balance']         = Decimal(d['balance'])
            d['initial_balance'] = Decimal(d['initial_balance'])
            return d
    return {'balance': Decimal('1000'), 'initial_balance': Decimal('1000'),
            'loss_streak': 0, 'open_trade': None}

def save_state(st):
    with lock:
        dump = {**st, 'balance': str(st['balance']), 'initial_balance': str(st['initial_balance'])}
        with open(STATE_FILE, 'w') as f:
            json.dump(dump, f, indent=2)

def log_trade(row):
    header = not os.path.exists(TRADE_LOG_FILE)
    with open(TRADE_LOG_FILE, 'a', newline='') as f:
        w = csv.writer(f)
        if header:
            w.writerow(['entry_time','exit_time','side','size','entry','exit','pnl','balance'])
        w.writerow(row)

# ── UTIL ───────────────────────────────────────────────────────────
def round_lot(qty: Decimal) -> Decimal:
    return (qty / lot_step).to_integral_value(ROUND_DOWN) * lot_step

def fetch_df():
    candles = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=150)
    df = pd.DataFrame(candles, columns=['ts','open','high','low','close','vol'])
    df['ema21'] = ta.trend.ema_indicator(df['close'], 21)
    df['ema50'] = ta.trend.ema_indicator(df['close'], 50)
    df['atr']   = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
    df['stoch'] = ta.momentum.stochrsi(df['close'])  # returns 0-1
    df.dropna(inplace=True)
    if df.empty:
        return None
    return df

def get_signal(df):
    last = df.iloc[-1]
    close = last['close']
    ema21 = last['ema21']
    ema50 = last['ema50']
    stoch = last['stoch']

    print(f"[DEBUG] close: {close:.2f}, ema21: {ema21:.2f}, ema50: {ema50:.2f}, stoch: {stoch:.2f}")

    if close > ema21 > ema50 and stoch < 0.2:
        print("[DEBUG] Signal = LONG (trend up + stoch low)")
        return 'LONG'
    if close < ema21 < ema50 and stoch > 0.8:
        print("[DEBUG] Signal = SHORT (trend down + stoch high)")
        return 'SHORT'

    print("[DEBUG] No signal met.")
    return None

def calc_size(balance, price, stop):
    if stop <= 0:
        return Decimal('0')
    risk = balance * RISK_PER_TRADE
    if risk <= 0:
        return Decimal('0')
        
    qty = round_lot(risk / stop)
    
    # Compare AFTER rounding
    if qty < min_qty:
        return Decimal('0')
    if qty * price > balance * LEVERAGE_LIMIT:
        return Decimal('0')
    return qty

# ── MONITOR ────────────────────────────────────────────────────────
def monitor(state_path, qty, entry, side):
    tp = entry * (Decimal('1.02') if side == 'LONG' else Decimal('0.98'))
    sl = entry * (Decimal('0.99') if side == 'LONG' else Decimal('1.01'))
    retries = 0

    while True:
        try:
            price = Decimal(str(exchange.fetch_ticker(SYMBOL)['last']))
            retries = 0                    # reset on success
        except Exception as e:
            retries += 1
            send_telegram(f"❌ Error fetching price: {e}")
            if retries > 5:                # give up after 5 consecutive failures
                print(f"[WARN] Monitor abort: {e}")
                break
            time.sleep(CHECK_INTERVAL)
            continue

        with lock:
            st = load_state()
            if st['loss_streak'] >= MAX_LOSS_STREAK or \
               st['balance'] < st['initial_balance'] * (1 - MAX_DRAWDOWN):
                st['open_trade'] = None
                save_state(st)
                print("[RISK] Trade aborted by live risk-control.")
                return

        if (side == 'LONG' and price >= tp) or (side == 'SHORT' and price <= tp):
            exit_p = tp; break
        if (side == 'LONG' and price <= sl) or (side == 'SHORT' and price >= sl):
            exit_p = sl; break
        time.sleep(CHECK_INTERVAL)

    gross = (exit_p - entry) * qty if side == 'LONG' else (entry - exit_p) * qty
    fees  = FEE_RATE * qty * (entry + exit_p)
    pnl   = gross - fees

    with lock:
        st = load_state()
        st['balance']        += pnl
        st['initial_balance'] = max(st['initial_balance'], st['balance'])
        st['loss_streak']     = 0 if pnl > 0 else st['loss_streak'] + 1
        st['open_trade']      = None
        save_state(st)
        bal_after = st['balance']

    log_trade([datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
               side, str(qty), str(entry), str(exit_p), str(pnl), str(bal_after)])
    print(f"[CLOSE] {side} | PnL {pnl:.2f} | Bal {bal_after:.2f}")
    send_telegram(
    f"✅ Trade Closed\nSide: {side}\nEntry: {entry:.2f}\nExit: {exit_p:.2f}\nPnL: {pnl:.2f}\nBalance: {bal_after:.2f}"
)

# ── MAIN LOOP ──────────────────────────────────────────────────────
def run():
    while True:
        with lock:
            st = load_state()
            open_pos   = st['open_trade']
            balance    = st['balance']
            initial    = st['initial_balance']
            streak     = st['loss_streak']

        if open_pos:
            time.sleep(CHECK_INTERVAL)   # monitor thread is running
            continue

        if streak >= MAX_LOSS_STREAK or balance < initial * (1 - MAX_DRAWDOWN):
            time.sleep(CHECK_INTERVAL)
            continue

        df = fetch_df()
        if df is None:
            time.sleep(CHECK_INTERVAL)
            continue

        sig = get_signal(df)
        if not sig:
            time.sleep(CHECK_INTERVAL)
            continue

        price = Decimal(str(df['close'].iloc[-1]))
        atr   = Decimal(str(df['atr'].iloc[-1]))
        print(f"[DEBUG] ATR: {atr:.2f}")
        if atr < MIN_ATR:
            print(f"[INFO] Skipping trade: ATR {atr:.2f} < MIN_ATR {MIN_ATR}")
            time.sleep(CHECK_INTERVAL)
            continue

        qty = calc_size(balance, price, atr)
        print(f"[DEBUG] Calculated size: {qty}")
        if qty == 0:
            print("[INFO] Skipping trade: Position size too small or invalid.")
            time.sleep(CHECK_INTERVAL)
            continue

        with lock:
            st = load_state()
            st['open_trade'] = {'qty': str(qty), 'entry': str(price), 'side': sig}
            save_state(st)
        print(f"[OPEN ] {sig} | Qty {qty} | Price {price}")
        send_telegram(f"📈 Trade Opened\nSide: {sig}\nQty: {qty}\nPrice: {price:.2f}")

        threading.Thread(target=monitor,
                         args=(STATE_FILE, qty, price, sig),
                         daemon=True).start()

        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    send_telegram("🚀 Bot started successfully.")
    run()
