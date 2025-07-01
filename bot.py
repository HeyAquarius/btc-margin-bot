import ccxt, time, json, os, csv
from decimal import Decimal, getcontext, ROUND_DOWN
from datetime import datetime
import pandas as pd
import ta

getcontext().prec = 12
getcontext().rounding = ROUND_DOWN

# ── CONFIG ─────────────────────────────────────────────────────────
SYMBOL           = 'BTC/USDT'
TIMEFRAME        = '15m'
RISK_PER_TRADE   = Decimal('0.01')
MAX_DRAWDOWN     = Decimal('0.10')
MAX_LOSS_STREAK  = 3
FEE_RATE         = Decimal('0.0004')
MIN_ATR          = Decimal('0.5')
LEVERAGE_LIMIT   = Decimal('5')
CHECK_INTERVAL   = 5

STATE_FILE       = 'bot_state.json'
TRADE_LOG_FILE   = 'trade_log.csv'

# ── EXCHANGE ───────────────────────────────────────────────────────
exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
markets  = exchange.load_markets()
info     = markets[SYMBOL]

# Get step size from filters (Binance-specific)
filters = info.get('info', {}).get('filters', [])
lot_step = None

for f in filters:
    if f['filterType'] == 'LOT_SIZE':
        lot_step = Decimal(f['stepSize'])
        break

if lot_step is None:
    raise ValueError("LOT_SIZE step not found in market info")
min_qty  = Decimal(str(info['limits']['amount']['min']))    # e.g. 0.000001

# ── STATE ──────────────────────────────────────────────────────────
def load_state():
    return {
        'balance': Decimal('1000'),
        'initial_balance': Decimal('1000'),
        'loss_streak': 0,
        'open_trade': None
    }

def save_state(st):
    dump = {**st,
            'balance': str(st['balance']),
            'initial_balance': str(st['initial_balance'])}
    with open(STATE_FILE, 'w') as f:
        json.dump(dump, f, indent=2)

def log_trade(row):
    header = not os.path.exists(TRADE_LOG_FILE)
    with open(TRADE_LOG_FILE, 'a', newline='') as f:
        w = csv.writer(f)
        if header:
            w.writerow(['entry_time','exit_time','side','size','entry','exit','pnl','balance'])
        w.writerow(row)

# ── HELPERS ────────────────────────────────────────────────────────
def round_lot(qty: Decimal) -> Decimal:
    return (qty / lot_step).to_integral_value(ROUND_DOWN) * lot_step

def fetch_df():
    candles = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, limit=150)
    df = pd.DataFrame(candles, columns=['ts','open','high','low','close','vol'])
    df['ema21'] = ta.trend.ema_indicator(df['close'], 21)
    df['ema50'] = ta.trend.ema_indicator(df['close'], 50)
    df['atr']   = ta.volatility.average_true_range(df['high'], df['low'], df['close'])
    df['stoch'] = ta.momentum.stochrsi(df['close'])
    df.dropna(inplace=True)
    if df.empty or df['atr'].iloc[-1] == 0:
        return None
    return df

def get_signal(df):
    last = df.iloc[-1]
    if last['close'] > last['ema21'] > last['ema50'] and last['stoch'] < 0.2:
        return 'LONG'
    if last['close'] < last['ema21'] < last['ema50'] and last['stoch'] > 0.8:
        return 'SHORT'
    return None

def size_for_trade(balance, price, stop):
    risk = balance * RISK_PER_TRADE
    fee_estimate = Decimal('2') * FEE_RATE * price
    usable = risk - fee_estimate
    if usable <= 0 or stop == 0:
        return Decimal('0')
    qty = round_lot(usable / stop)
    if qty < min_qty or qty * price > balance * LEVERAGE_LIMIT:
        return Decimal('0')
    return qty

# ── MONITOR ────────────────────────────────────────────────────────
def monitor(st, qty, entry, side):
    tp_factor = Decimal('1.02')
    sl_factor = Decimal('0.99')
    tp = entry * tp_factor if side == 'LONG' else entry * (2 - tp_factor)
    sl = entry * sl_factor if side == 'LONG' else entry * (2 - sl_factor)

    while True:
        try:
            price = Decimal(str(exchange.fetch_ticker(SYMBOL)['last']))
        except Exception:
            time.sleep(CHECK_INTERVAL); continue

        if (side == 'LONG' and price >= tp) or (side == 'SHORT' and price <= tp):
            exit_price = tp
            break
        if (side == 'LONG' and price <= sl) or (side == 'SHORT' and price >= sl):
            exit_price = sl
            break
        time.sleep(CHECK_INTERVAL)

    gross = (exit_price - entry) * qty if side == 'LONG' else (entry - exit_price) * qty
    fees  = FEE_RATE * qty * (entry + exit_price)
    pnl   = gross - fees

    st['balance']        += pnl
    st['initial_balance'] = max(st['initial_balance'], st['balance'])
    st['loss_streak']     = 0 if pnl > 0 else st['loss_streak'] + 1
    st['open_trade']      = None
    save_state(st)

    log_trade([datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
               side, str(qty), str(entry), str(exit_price), str(pnl), str(st['balance'])])
    print(f"Closed {side} | PnL {pnl:.2f} | Bal {st['balance']:.2f}")

# ── MAIN LOOP ──────────────────────────────────────────────────────
def run():
    state = load_state()
    while True:
        if state['open_trade']:
            print("[INFO] Trade open, monitoring...")
            ot = state['open_trade']
            monitor(state, Decimal(ot['qty']), Decimal(ot['entry']), ot['side'])
            continue

        print("[INFO] No open trade. Checking risk filters...")
        if state['loss_streak'] >= MAX_LOSS_STREAK:
            print(f"[RISK] Max loss streak hit: {state['loss_streak']}")
        if state['balance'] < state['initial_balance'] * (1 - MAX_DRAWDOWN):
            print(f"[RISK] Max drawdown hit: Balance = {state['balance']}, Initial = {state['initial_balance']}")

        if state['loss_streak'] >= MAX_LOSS_STREAK or \
           state['balance'] < state['initial_balance'] * (1 - MAX_DRAWDOWN):
            print("[INFO] Risk filters active. Pausing.")
            time.sleep(CHECK_INTERVAL)
            continue

        print("[INFO] Fetching data...")
        df = fetch_df()
        if df is None:
            print("[WARN] No valid data or ATR is zero. Skipping.")
            time.sleep(CHECK_INTERVAL)
            continue

        sig = get_signal(df)
        print(f"[DEBUG] Signal: {sig}")
        if not sig:
            print("[INFO] No trade signal.")
            time.sleep(CHECK_INTERVAL)
            continue

        price = Decimal(str(df.iloc[-1]['close']))
        atr   = Decimal(str(df.iloc[-1]['atr']))
        print(f"[DEBUG] Price: {price}, ATR: {atr}")
        if atr < MIN_ATR:
            print(f"[INFO] ATR too low ({atr} < {MIN_ATR}). Skipping.")
            time.sleep(CHECK_INTERVAL)
            continue

        qty = size_for_trade(state['balance'], price, atr)
        print(f"[DEBUG] Calculated qty: {qty}")
        if qty == 0:
            print("[INFO] Qty is 0. Skipping.")
            time.sleep(CHECK_INTERVAL)
            continue

        state['open_trade'] = {'qty': str(qty), 'entry': str(price), 'side': sig}
        save_state(state)
        print(f"[TRADE] Opened {sig} | Qty {qty} | Price {price}")

        time.sleep(CHECK_INTERVAL)
        
if __name__ == '__main__':
    run()
