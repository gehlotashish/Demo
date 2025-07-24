import pandas as pd

def get_model_health(trade_log_df: pd.DataFrame) -> str:
    """
    Generate a weekly stats/health report for the model.
    - trade_log_df: DataFrame with columns ['pnl', 'signal', 'actual', ...]
    Returns: string summary for Telegram
    """
    if trade_log_df.empty:
        return "No trades this week."
    total = len(trade_log_df)
    wins = (trade_log_df['pnl'] > 0).sum()
    losses = (trade_log_df['pnl'] <= 0).sum()
    win_rate = wins / total * 100
    avg_pnl = trade_log_df['pnl'].mean()
    max_drawdown = trade_log_df['pnl'].cumsum().min()
    false_signals = (trade_log_df['signal'] != trade_log_df['actual']).sum() if 'actual' in trade_log_df.columns else 'N/A'
    false_rate = (false_signals / total * 100) if false_signals != 'N/A' else 'N/A'
    report = (
        f"📊 *Model Health (Weekly)*\n"
        f"Total Trades: {total}\n"
        f"Win Rate: {win_rate:.2f}%\n"
        f"Avg PnL: {avg_pnl:.2f}\n"
        f"Max Drawdown: {max_drawdown:.2f}\n"
        f"False Signal Rate: {false_rate if false_rate != 'N/A' else 'N/A'}%\n"
        f"Best Trade: {trade_log_df['pnl'].max():.2f}\n"
        f"Worst Trade: {trade_log_df['pnl'].min():.2f}"
    )
    return report 