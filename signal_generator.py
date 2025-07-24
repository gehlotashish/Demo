import joblib
import pandas as pd
import numpy as np
from model_trainer import extract_features
import pandas_ta as ta

def generate_signal(df: pd.DataFrame, symbol: str = "BANKNIFTY") -> str:
    """
    Use trained model to predict and format signal message for given symbol.
    Supports Buy/Sell CE/PE signals.
    """
    features = extract_features(df)
    model = joblib.load('model.pkl')
    # For demo: 0 = Buy PE, 1 = Buy CE, 2 = Sell PE, 3 = Sell CE
    if hasattr(model, 'predict_proba'):
        probs = model.predict_proba(features)
        if probs.shape[1] == 2:
            # Binary: 1 = Buy CE, 0 = Buy PE
            idx = np.argmax(np.abs(probs[:, 1] - 0.5))
            pred = int(probs[idx, 1] > 0.5)
        else:
            idx = np.argmax(np.max(probs, axis=1))
            pred = np.argmax(probs[idx])
        conf = int(np.max(probs[idx]) * 100)
    else:
        preds = model.predict(features)
        idx = 0
        pred = preds[idx]
        conf = 50
    row = df.iloc[idx]
    strike = row['strike']
    if pred == 0:
        action = "Buy PE"
        price = row['PE_LTP']
        opt_type = "PE"
    elif pred == 1:
        action = "Buy CE"
        price = row['CE_LTP']
        opt_type = "CE"
    elif pred == 2:
        action = "Sell PE"
        price = row['PE_LTP']
        opt_type = "PE"
    else:
        action = "Sell CE"
        price = row['CE_LTP']
        opt_type = "CE"
    sl = round(price * 0.85, 2)
    tgt = round(price * 1.25, 2)
    msg = f"🔔 [SIGNAL] {action} {symbol} {int(strike)}{opt_type} @ ₹{price}, Target ₹{tgt}, SL ₹{sl} (🧠 {conf}% confidence)"
    return msg


def generate_ohlc_signal(df: pd.DataFrame, symbol: str = "BANKNIFTY", return_details: bool = False) -> str:
    """
    Generate Buy/Sell signal from OHLCV data using multi-indicator confirmation (RSI, MACD, Supertrend).
    Only signal if at least 2/3 indicators agree.
    If return_details=True, also return entry, sl for risk management.
    """
    # Calculate indicators
    df.loc[:, 'RSI'] = ta.rsi(df['Close'], length=14)
    macd = ta.macd(df['Close'])
    df['MACD'] = macd['MACD_12_26_9']
    df['MACDs'] = macd['MACDs_12_26_9']
    df['MACDh'] = macd['MACDh_12_26_9']
    st = ta.supertrend(df['High'], df['Low'], df['Close'])
    df['Supertrend'] = st['SUPERT_7_3.0']
    last = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else last
    # Multi-indicator confirmation
    buy_votes = 0
    sell_votes = 0
    # RSI
    if last['RSI'] < 35:
        buy_votes += 1
    if last['RSI'] > 65:
        sell_votes += 1
    # MACD
    if prev['MACD'] < prev['MACDs'] and last['MACD'] > last['MACDs']:
        buy_votes += 1
    if prev['MACD'] > prev['MACDs'] and last['MACD'] < last['MACDs']:
        sell_votes += 1
    # Supertrend
    if last['Close'] > last['Supertrend']:
        buy_votes += 1
    if last['Close'] < last['Supertrend']:
        sell_votes += 1
    action = "No clear signal"
    conf = 50
    if buy_votes >= 2:
        action = "Buy"
        conf = 80
    elif sell_votes >= 2:
        action = "Sell"
        conf = 80
    price = last['Close']
    sl = round(price * 0.98, 2) if action == "Buy" else round(price * 1.02, 2)
    tgt = round(price * 1.02, 2) if action == "Buy" else round(price * 0.98, 2)
    msg = f"🔔 [OHLC SIGNAL] {action} {symbol} @ ₹{price}, Target ₹{tgt}, SL ₹{sl} (🧠 {conf}% confidence)"
    if return_details:
        return msg, price, sl
    return msg 


def generate_ensemble_signal(features: pd.DataFrame, symbol: str = "BANKNIFTY", return_details: bool = False) -> str:
    """
    Use trained ensemble model to predict and format signal message.
    If return_details=True, also return entry, sl for risk management.
    """
    model = joblib.load('model_ensemble.pkl')
    probs = model.predict_proba(features)
    idx = probs[:, 1].argmax() if probs.shape[1] == 2 else probs.argmax(axis=0)[0]
    conf = int(probs[idx].max() * 100)
    # For demo: 1 = Buy CE, 0 = Buy PE (binary), else multiclass
    if probs.shape[1] == 2:
        pred = int(probs[idx, 1] > 0.5)
    else:
        pred = probs[idx].argmax()
    row = features.iloc[idx] if hasattr(features, 'iloc') else features
    strike = row.get('strike', 0)
    if pred == 0:
        action = "Buy PE"
        price = row.get('PE_LTP', 0)
        opt_type = "PE"
    elif pred == 1:
        action = "Buy CE"
        price = row.get('CE_LTP', 0)
        opt_type = "CE"
    elif pred == 2:
        action = "Sell PE"
        price = row.get('PE_LTP', 0)
        opt_type = "PE"
    else:
        action = "Sell CE"
        price = row.get('CE_LTP', 0)
        opt_type = "CE"
    sl = round(price * 0.85, 2)
    tgt = round(price * 1.25, 2)
    msg = f"🔔 [ENSEMBLE] {action} {symbol} {int(strike)}{opt_type} @ ₹{price}, Target ₹{tgt}, SL ₹{sl} (🧠 {conf}% confidence)"
    if return_details:
        return msg, price, sl
    return msg 


# Example: model must have predict_proba, df must have indicator columns

def smart_signal(df, model, volatility, adaptive_conf=True):
    """
    Generate a smart signal using ML + indicator confirmation.
    - Adaptive confidence threshold: higher in volatile days
    - Returns: 'BUY', 'SELL', or 'NO_SIGNAL'
    """
    if df is None or df.empty:
        return 'NO_SIGNAL'
    # ML model prediction (assume binary: 1=BUY, 0=SELL)
    probs = model.predict_proba(df)[0]
    conf = max(probs)
    pred = np.argmax(probs)
    # Indicator confirmation (example: bullish_engulfing, bearish_engulfing)
    bullish = df.iloc[-1].get('bullish_engulfing', 0) if not df.empty else 0
    bearish = df.iloc[-1].get('bearish_engulfing', 0) if not df.empty else 0
    # Adaptive confidence threshold
    base_threshold = 0.7
    if adaptive_conf:
        if volatility > 1.5:  # Example: high ATR or VIX
            threshold = 0.8
        else:
            threshold = base_threshold
    else:
        threshold = base_threshold
    # Signal logic
    if pred == 1 and conf >= threshold and bullish:
        return 'BUY'
    elif pred == 0 and conf >= threshold and bearish:
        return 'SELL'
    else:
        return 'NO_SIGNAL' 