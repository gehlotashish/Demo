import numpy as np

# Example: model must have predict_proba, df must have indicator columns

def smart_signal(df, model, volatility, adaptive_conf=True):
    """
    Generate a smart signal using ML + indicator confirmation.
    - Adaptive confidence threshold: higher in volatile days
    - Returns: 'BUY', 'SELL', or 'NO_SIGNAL'
    """
    # ML model prediction (assume binary: 1=BUY, 0=SELL)
    probs = model.predict_proba(df)[0]
    conf = max(probs)
    pred = np.argmax(probs)
    # Indicator confirmation (example: bullish_engulfing, bearish_engulfing)
    bullish = df.iloc[-1].get('bullish_engulfing', 0)
    bearish = df.iloc[-1].get('bearish_engulfing', 0)
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