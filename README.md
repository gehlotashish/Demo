# Telegram Options Trading Bot (Nifty/BankNifty)

## Features

- Real-time options signals for Nifty 50 / Bank Nifty
- Scrapes live data from NSE India
- Uses free historical data (NSE Bhavcopy, nsepy, yfinance)
- Machine learning based signal generation
- Sends formatted signals to Telegram group/channel
- Runs only during Indian market hours

## Repository Structure

```
BOT2/
├── main.py                      # Main orchestrator: scheduling, signals, risk mgmt, threading
├── data_fetcher.py              # Fetches live NSE, yfinance, Bhavcopy data (option chain, OHLC, etc.)
├── model_trainer.py             # Feature extraction, ML/ensemble model training, retraining
├── signal_generator.py          # Signal logic: ML, ensemble, indicator, formatting
├── bot_handler.py               # Telegram bot logic, commands, message sending, analytics
├── backtester.py                # Backtesting module: realistic PnL, win rate, drawdown, slippage
├── advanced_feature_engineering.py # Advanced features: OI change, IV Rank, PCR, ATR, candle signals
├── smart_signal_generator.py    # Smart signal logic: ML + indicator + adaptive confidence
├── adaptive_risk_manager.py     # Adaptive position sizing: Kelly criterion, risk %
├── stats_report.py              # Weekly stats, health report, analytics
├── logger.py                    # Error logging utility (writes to error.log)
├── healthcheck.py               # Flask health check endpoint for cloud hosting
├── requirements.txt             # Python dependencies
├── .env.example                 # Example environment config (copy to .env)
├── README.md                    # Documentation and setup guide
├── bot_summary.md               # Full bot features/architecture summary
├── error.log                    # Error log file (auto-generated)
├── backtest_results.csv         # Backtest results (auto-generated)
```

**Modular, production-grade, and easy to extend!**

---

## Setup Instructions

### 1. Clone the repo & install requirements

```bash
git clone <repo-url>
cd BOT2
pip install -r requirements.txt
```

### 2. Configure Environment Variables

- Copy `.env.example` to `.env`:
  ```bash
  cp .env.example .env
  ```
- Fill in your Telegram bot token and chat ID:
  ```env
  TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
  TELEGRAM_CHAT_ID=your_group_or_channel_id
  ```
  - [How to get Telegram bot token?](https://core.telegram.org/bots#6-botfather)
  - [How to get chat ID?](https://stackoverflow.com/a/32572159)

### 3. Train the Model

- Run:
  ```bash
  python model_trainer.py
  ```
- This will fetch latest option chain, extract features, create dummy labels, and train the model.

### 4. Run the Bot

- Start the bot:
  ```bash
  python main.py
  ```
- The bot will send signals to your Telegram group/channel every 5 minutes during Indian market hours (Mon-Fri, 9:15am-3:30pm IST).

---

## Free Hosting (Replit/Railway)

### Deploy on Replit

1. Import this repo into [Replit](https://replit.com/)
2. Add your `.env` variables in the Replit Secrets tab
3. Run `python model_trainer.py` once to train the model
4. Set `python main.py` as the run command
5. Use [UptimeRobot](https://uptimerobot.com/) to keep your Replit bot always on (optional)

### Deploy on Railway

1. Import this repo into [Railway](https://railway.app/)
2. Add your `.env` variables in the Railway dashboard
3. Set up a Python service with `python main.py` as the start command
4. Deploy!

---

## Proxy/VPN Support (Optional)

- If your IP gets blocked by NSE or any data source, you can add HTTP/HTTPS proxies in your `.env` file:
  ```env
  PROXIES=http://user:pass@proxy1:port,http://user:pass@proxy2:port
  ```
- The bot will auto-rotate proxies if it detects a block (403/429/connection error).
- All requests (NSE, yfinance, Bhavcopy) will use the proxy if set.
- **Warning:** Free proxies are often unreliable and insecure. For best results, use paid/private proxies.

## Troubleshooting (Proxy)

- If you see repeated 'blocked' or 'proxy error' messages in `error.log`, try updating your proxy list or use a different network/VPN.
- Proxy switching events are logged in `error.log`.

---

## File Structure

- `data_fetcher.py` - Data scraping & fetching
- `model_trainer.py` - Feature extraction & ML training
- `signal_generator.py` - Signal logic
- `bot_handler.py` - Telegram bot logic
- `main.py` - Orchestration

---

## Disclaimer

This bot is for educational purposes only. Use at your own risk. No financial advice.
