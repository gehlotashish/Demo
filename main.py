import schedule
import time
import os
import threading
from data_fetcher import fetch_nse_option_chain, fetch_ohlc_yfinance
from signal_generator import generate_signal, generate_ohlc_signal, generate_ensemble_signal
from bot_handler import send_signal, is_market_open, set_refs, start_bot_sync, set_advanced_refs
from logger import log_error
from model_trainer import train_model, extract_features, create_dummy_labels
import os.path
from advanced_feature_engineering import add_advanced_features
from smart_signal_generator import smart_signal
from adaptive_risk_manager import adaptive_position_size
from stats_report import get_model_health
import joblib
from dotenv import load_dotenv
import asyncio
load_dotenv()

retrain_ref = [False]

SYMBOLS_ENV = os.getenv("SYMBOLS")
if SYMBOLS_ENV:
    SYMBOLS = [s.strip().upper() for s in SYMBOLS_ENV.split(",") if s.strip()]
else:
    SYMBOLS = ["BANKNIFTY", "NIFTY"]  # Default
INTERVAL_MINUTES = [int(os.getenv("INTERVAL_MINUTES", 5))]

# --- Risk Management Settings ---
CAPITAL = float(os.getenv("CAPITAL", 100000))  # Total capital
RISK_PER_TRADE = [float(os.getenv("RISK_PER_TRADE", 0.01))]  # 1% per trade
MAX_LOSS_PER_DAY = [float(os.getenv("MAX_LOSS_PER_DAY", 0.03))]  # 3% per day

daily_pnl = [0]  # Use list for mutable reference
paused = [False]
last_date = None
log = [""]
running = [True]
symbol = [SYMBOLS[0]]  # Default to first symbol

# Sync with bot_handler for Telegram commands
set_refs(paused, daily_pnl)
set_advanced_refs(INTERVAL_MINUTES, RISK_PER_TRADE, MAX_LOSS_PER_DAY, log, running, symbol, version="v1.0-advanced", retrain=retrain_ref)

USE_ENSEMBLE = True  # Toggle to use ensemble model if available

MAX_TRADE_LOSS = 200  # Max loss per trade (demo value)

TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

def get_position_size(entry, sl):
    risk_amt = CAPITAL * RISK_PER_TRADE[0]
    per_unit_risk = abs(entry - sl)
    if per_unit_risk == 0:
        return 1
    size = max(1, int(risk_amt / per_unit_risk))
    return size

def job():
    print("job() running...")  # Debug
    global last_date
    try:
        if not TELEGRAM_CHAT_ID:
            print("❌ TELEGRAM_CHAT_ID is missing! Please set it in your .env file.")
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(send_signal("Test message from job() (debug)"))
        except RuntimeError:
            asyncio.run(send_signal("Test message from job() (debug)"))
        today = time.strftime('%Y-%m-%d')
        if last_date != today:
            daily_pnl[0] = 0
            paused[0] = False
            last_date = today
            log[0] = ""
        if retrain_ref[0]:
            from data_fetcher import fetch_nse_option_chain
            print("Retraining model for", symbol[0])
            df = fetch_nse_option_chain(symbol[0])
            if df is None or df.empty:
                send_signal(f"❌ Option chain data fetch failed for {symbol[0]}, skipping retrain.")
                retrain_ref[0] = False
                return
            features = add_advanced_features(df, symbol[0])
            labels = create_dummy_labels(df)
            train_model(features, labels, model_type='auto')
            from model_trainer import train_ensemble_model
            train_ensemble_model(features, labels)
            retrain_ref[0] = False
            send_signal(f"Model retrained for {symbol[0]}! (Ensemble included)")
        if not running[0]:
            send_signal("Bot is shutting down (by user command). Bye!")
            exit(0)
        if paused[0]:
            print("Bot is paused.")
            return
        now = time.localtime()
        if now.tm_hour == 9 and now.tm_min < 20:
            send_signal("⏳ News filter: No signals in first 5 min after market open.")
            print("News filter active.")
            return
        if is_market_open():
            for symbol_name in [symbol[0]]:
                print(f"Fetching yfinance OHLC for {symbol_name}")
                ohlc = fetch_ohlc_yfinance(symbol_name, interval='5m', lookback=60)
                if ohlc is None or ohlc.empty:
                    send_signal(f"❌ yfinance data not available for {symbol_name}, skipping.")
                    print(f"yfinance data not available for {symbol_name}")
                    continue
                import pandas_ta as ta
                atr = ta.atr(ohlc['High'], ohlc['Low'], ohlc['Close'])
                if atr is None or atr.empty:
                    send_signal(f"❌ ATR calculation failed for {symbol_name}, skipping.")
                    print(f"ATR calculation failed for {symbol_name}")
                    continue
                atr_val = atr.iloc[-1]
                price = ohlc['Close'].iloc[-1]
                if atr_val > 0.02 * price:
                    paused[0] = True
                    send_signal(f"⚡ Volatility too high (ATR {atr_val:.2f}), bot auto-paused!")
                    print(f"Volatility too high for {symbol_name}, bot auto-paused!")
                    return
                if atr_val > 0.01 * price:
                    send_signal(f"⚡ Volatility filter: ATR too high ({atr_val:.2f}), skipping signal.")
                    print(f"Volatility filter: ATR too high for {symbol_name}")
                    continue
                try:
                    print(f"Fetching option chain for {symbol_name}")
                    df = fetch_nse_option_chain(symbol_name)
                    if df is None or df.empty:
                        send_signal(f"❌ Option chain data fetch failed for {symbol_name}, skipping.")
                        print(f"Option chain data fetch failed for {symbol_name}")
                        continue
                    features = add_advanced_features(df, symbol_name)
                    try:
                        model = joblib.load('model_ensemble.pkl')
                    except:
                        from model_trainer import train_model
                        model = train_model(features, create_dummy_labels(df), model_type='auto')
                    volatility = atr_val if 'atr_val' in locals() else 1.0
                    signal = smart_signal(features, model, volatility, adaptive_conf=True)
                    if signal == 'BUY':
                        action = 'Buy CE'
                    elif signal == 'SELL':
                        action = 'Buy PE'
                    else:
                        action = 'NO_SIGNAL'
                    msg = f"🔔 [SMART] {action} {symbol_name} (Smart Signal)"
                    if features is None or features.empty:
                        send_signal(f"❌ Features missing for {symbol_name}, skipping.")
                        print(f"Features missing for {symbol_name}")
                        continue
                    if action == 'Buy CE':
                        entry = features.iloc[-1].get('CE_LTP', 0)
                    elif action == 'Buy PE':
                        entry = features.iloc[-1].get('PE_LTP', 0)
                    else:
                        entry = 0
                    sl = round(entry * 0.98, 2) if entry else 0
                    print(f"Signal generated: {msg}, entry: {entry}, sl: {sl}")
                except Exception as e:
                    log_error(f"Option chain failed for {symbol_name}: {e}")
                    print(f"Option chain failed for {symbol_name}: {e}")
                    try:
                        ohlc = fetch_ohlc_yfinance(symbol_name, interval='5m', lookback=60)
                        if ohlc is None or ohlc.empty:
                            send_signal(f"❌ yfinance data not available for {symbol_name}, skipping.")
                            print(f"yfinance data not available for {symbol_name}")
                            continue
                        features = add_advanced_features(ohlc, symbol_name)
                        try:
                            model = joblib.load('model_ensemble.pkl')
                        except:
                            from model_trainer import train_model
                            model = train_model(features, create_dummy_labels(ohlc), model_type='auto')
                        volatility = atr_val if 'atr_val' in locals() else 1.0
                        signal = smart_signal(features, model, volatility, adaptive_conf=True)
                        if signal == 'BUY':
                            action = 'Buy CE'
                        elif signal == 'SELL':
                            action = 'Buy PE'
                        else:
                            action = 'NO_SIGNAL'
                        msg = f"🔔 [SMART] {action} {symbol_name} (Smart Signal)"
                        if features is None or features.empty:
                            send_signal(f"❌ Features missing for {symbol_name}, skipping.")
                            print(f"Features missing for {symbol_name}")
                            continue
                        if action == 'Buy CE':
                            entry = features.iloc[-1].get('CE_LTP', 0)
                        elif action == 'Buy PE':
                            entry = features.iloc[-1].get('PE_LTP', 0)
                        else:
                            entry = 0
                        sl = round(entry * 0.98, 2) if entry else 0
                        print(f"Signal generated: {msg}, entry: {entry}, sl: {sl}")
                    except Exception as e2:
                        log_error(f"yfinance OHLC failed for {symbol_name}: {e2}")
                        print(f"yfinance OHLC failed for {symbol_name}: {e2}")
                        msg, entry, sl = f"❌ No data available for {symbol_name}", None, None
                balance = 100000  # Example, replace with real balance
                accuracy_score = 0.75  # Example, replace with rolling win rate
                pos_size = adaptive_position_size(balance, 0.01, abs(entry - sl) if entry and sl else 1, accuracy_score)
                trailing_sl = sl
                if entry and sl:
                    import random
                    price = entry * (1 + random.uniform(-0.01, 0.03))
                    if price > entry * 1.02:
                        trailing_sl = round(entry * 1.01, 2)
                    elif price > entry * 1.01:
                        trailing_sl = round(entry, 2)
                    sl_hit = price <= trailing_sl if entry > sl else price >= trailing_sl
                    if sl_hit:
                        send_signal(f"🚨 Trailing SL hit for {symbol_name}! Exit at ₹{trailing_sl}")
                trade_pnl = round(random.uniform(-100, 150), 2)
                daily_pnl[0] += trade_pnl
                log[0] += f"{today} {symbol_name}: {msg} | Size: {pos_size} | PnL: {trade_pnl} | Trailing SL: {trailing_sl}\n"
                if trade_pnl < -MAX_TRADE_LOSS:
                    paused[0] = True
                    send_signal(f"🚨 Trade loss {trade_pnl} exceeded max allowed, bot auto-paused!")
                    break
                if daily_pnl[0] < -CAPITAL * MAX_LOSS_PER_DAY[0]:
                    paused[0] = True
                    send_signal(f"🚨 Bot auto-paused: Max loss for the day hit! (PnL: {daily_pnl[0]:.2f})")
                    break
                send_signal(f"{msg}\nPosition Size: {pos_size}\nPnL: {trade_pnl}\nTrailing SL: {trailing_sl}")
    except Exception as e:
        print("job() error:", e)
        log_error(f"main.py job error: {e}")

# Regular auto-retrain every Sunday at 10:00
schedule.every().sunday.at("10:00").do(lambda: retrain_ref.__setitem__(0, True))

def run_signals_scheduler():
    last_interval = INTERVAL_MINUTES[0]
    schedule.every(last_interval).minutes.do(job)
    while True:
        if INTERVAL_MINUTES[0] != last_interval:
            schedule.clear()
            schedule.every(INTERVAL_MINUTES[0]).minutes.do(job)
            last_interval = INTERVAL_MINUTES[0]
        time.sleep(1)
        schedule.run_pending()
        if not running[0]:
            break

if __name__ == "__main__":
    t = threading.Thread(target=run_signals_scheduler, daemon=True)
    t.start()
    start_bot_sync() 