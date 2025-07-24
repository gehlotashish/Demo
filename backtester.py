import pandas as pd
from data_fetcher import fetch_ohlc_yfinance
from signal_generator import generate_ohlc_signal
import datetime

SYMBOL = "BANKNIFTY"
INTERVAL = "5m"
DAYS = 10  # Backtest last 10 days
POSITION_SIZE = 1  # 1 lot per trade (for demo)

SLIPPAGE_PCT = 0.001  # 0.1% slippage per trade
BROKERAGE = 20  # Flat brokerage per trade (demo value)

results = []
for d in pd.date_range(datetime.date.today() - datetime.timedelta(days=DAYS), datetime.date.today() - datetime.timedelta(days=1)):
    try:
        df = fetch_ohlc_yfinance(SYMBOL, interval=INTERVAL, lookback=390)  # 1 day = 390 min (5m candles)
        if df.empty or len(df) < 20:
            continue
        entry_price = None
        entry_time = None
        direction = None
        pnl = 0
        slippage = 0
        brokerage = 0
        for i in range(20, len(df)):
            subdf = df.iloc[:i+1]
            signal = generate_ohlc_signal(subdf, SYMBOL)
            last = subdf.iloc[-1]
            if "Buy" in signal and entry_price is None:
                entry_price = last['Close']
                entry_time = last['Datetime'] if 'Datetime' in last else last['index']
                direction = "Buy"
                sl = entry_price * 0.98
                tgt = entry_price * 1.02
            elif "Sell" in signal and entry_price is None:
                entry_price = last['Close']
                entry_time = last['Datetime'] if 'Datetime' in last else last['index']
                direction = "Sell"
                sl = entry_price * 1.02
                tgt = entry_price * 0.98
            if entry_price is not None:
                # Check SL/Target hit
                if direction == "Buy":
                    if last['Low'] <= sl:
                        exit_price = sl
                        slippage = abs(exit_price - entry_price) * SLIPPAGE_PCT
                        brokerage = BROKERAGE
                        pnl = (exit_price - entry_price - slippage) * POSITION_SIZE - brokerage
                        break
                    elif last['High'] >= tgt:
                        exit_price = tgt
                        slippage = abs(exit_price - entry_price) * SLIPPAGE_PCT
                        brokerage = BROKERAGE
                        pnl = (exit_price - entry_price - slippage) * POSITION_SIZE - brokerage
                        break
                elif direction == "Sell":
                    if last['High'] >= sl:
                        exit_price = sl
                        slippage = abs(entry_price - exit_price) * SLIPPAGE_PCT
                        brokerage = BROKERAGE
                        pnl = (entry_price - exit_price - slippage) * POSITION_SIZE - brokerage
                        break
                    elif last['Low'] <= tgt:
                        exit_price = tgt
                        slippage = abs(entry_price - exit_price) * SLIPPAGE_PCT
                        brokerage = BROKERAGE
                        pnl = (entry_price - exit_price - slippage) * POSITION_SIZE - brokerage
                        break
        results.append({
            "date": d.strftime("%Y-%m-%d"),
            "entry_time": entry_time,
            "direction": direction,
            "entry_price": entry_price,
            "pnl": pnl,
            "slippage": slippage,
            "brokerage": brokerage
        })
    except Exception as e:
        results.append({"date": d.strftime("%Y-%m-%d"), "error": str(e)})

# Calculate stats
required_cols = ['pnl', 'entry_time', 'exit_time', 'direction', 'entry_price', 'exit_price']
if results:
    resdf = pd.DataFrame(results)
    # Ensure all required columns exist
    for col in required_cols:
        if col not in resdf.columns:
            resdf[col] = None
else:
    resdf = pd.DataFrame(columns=required_cols)

resdf.to_csv("backtest_results.csv", index=False)

if not resdf.empty and 'pnl' in resdf.columns:
    total_pnl = resdf['pnl'].sum()
    win_rate = (resdf['pnl'] > 0).mean() * 100
    max_drawdown = resdf['pnl'].cumsum().min()
    print(f"Total PnL: {total_pnl:.2f}, Win Rate: {win_rate:.2f}%, Max Drawdown: {max_drawdown:.2f}")
else:
    print("No trades found, or 'pnl' column missing.") 