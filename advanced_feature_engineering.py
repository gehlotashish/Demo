import pandas as pd
import pandas_ta as ta
import numpy as np

def add_advanced_features(df: pd.DataFrame, symbol: str) -> pd.DataFrame:
    """
    Add advanced features to the DataFrame:
    - OI change, IV Rank, PCR, ATR
    - Combine with candle signals (bullish/bearish engulfing, etc.)
    Returns a new DataFrame with added features.
    """
    features = df.copy()
    # OI Change
    if 'openInterest' in features.columns:
        features['OI_Change'] = features['openInterest'].diff().fillna(0)
    # IV Rank (relative to last 20 periods)
    if 'impliedVolatility' in features.columns:
        iv = features['impliedVolatility']
        features['IV_Rank'] = (iv - iv.rolling(20).min()) / (iv.rolling(20).max() - iv.rolling(20).min() + 1e-6)
    # Put/Call Ratio (PCR)
    if 'PE_OI' in features.columns and 'CE_OI' in features.columns:
        features['PCR'] = features['PE_OI'] / (features['CE_OI'] + 1e-6)
    # ATR (Average True Range)
    if all(x in features.columns for x in ['High', 'Low', 'Close']):
        features['ATR'] = ta.atr(features['High'], features['Low'], features['Close'])
    # Candle signals (bullish/bearish engulfing)
    if all(x in features.columns for x in ['Open', 'High', 'Low', 'Close']):
        features['bullish_engulfing'] = ((features['Close'] > features['Open']) &
                                         (features['Close'].shift(1) < features['Open'].shift(1)) &
                                         (features['Open'] < features['Close'].shift(1)) &
                                         (features['Close'] > features['Open'].shift(1))).astype(int)
        features['bearish_engulfing'] = ((features['Close'] < features['Open']) &
                                         (features['Close'].shift(1) > features['Open'].shift(1)) &
                                         (features['Open'] > features['Close'].shift(1)) &
                                         (features['Close'] < features['Open'].shift(1))).astype(int)
    # Symbol as categorical feature
    features['symbol'] = symbol
    return features 