def adaptive_position_size(balance, risk_percent, stoploss_points, accuracy_score):
    """
    Calculate position size using Kelly criterion and risk percent.
    - balance: total capital
    - risk_percent: max risk per trade (e.g. 0.01 for 1%)
    - stoploss_points: stoploss in points/rupees
    - accuracy_score: expected win rate (0-1)
    Returns: position size (number of lots/contracts)
    """
    # Kelly fraction: f* = W - (1-W)/R
    # W = win rate, R = win/loss ratio (assume 1:1 for simplicity)
    W = accuracy_score
    L = 1 - W
    R = 1  # If you have avg win/avg loss, use that
    kelly_fraction = max(0, W - L/R)
    # Final risk per trade
    risk_amt = balance * risk_percent * kelly_fraction
    if stoploss_points <= 0:
        return 1
    size = int(risk_amt / stoploss_points)
    return max(1, size) 