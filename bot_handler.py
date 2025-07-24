import os
import asyncio
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes
import datetime
from logger import log_error
import pandas as pd
import matplotlib.pyplot as plt
import io

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Create a single global Application instance with increased pool size and timeout
application = Application.builder()\
    .token(TELEGRAM_BOT_TOKEN)\
    .connection_pool_size(20)\
    .pool_timeout(30)\
    .build()

# These will be set by main.py
paused_ref = None
pnl_ref = None

interval_ref = None
risk_ref = None
maxloss_ref = None

log_ref = None
running_ref = None
symbol_ref = None
version_str = "v1.0-advanced"

retrain_ref = None

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global paused_ref
    if paused_ref is not None:
        paused_ref[0] = True
        await update.message.reply_text("🚦 Bot paused by user command.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global paused_ref
    if paused_ref is not None:
        paused_ref[0] = False
        await update.message.reply_text("✅ Bot resumed by user command.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global paused_ref, pnl_ref
    paused = paused_ref[0] if paused_ref else False
    pnl = pnl_ref[0] if pnl_ref else 0
    await update.message.reply_text(f"Bot status: {'Paused' if paused else 'Active'}\nDaily PnL: {pnl:.2f}")

def set_refs(paused, pnl):
    global paused_ref, pnl_ref
    paused_ref = paused
    pnl_ref = pnl

def set_config_refs(interval, risk, maxloss):
    global interval_ref, risk_ref, maxloss_ref
    interval_ref = interval
    risk_ref = risk
    maxloss_ref = maxloss

async def setinterval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global interval_ref
    try:
        value = int(context.args[0])
        if interval_ref is not None:
            interval_ref[0] = value
            await update.message.reply_text(f"Signal interval set to {value} minutes.")
    except Exception:
        await update.message.reply_text("Usage: /setinterval [minutes]")

async def setrisk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global risk_ref
    try:
        value = float(context.args[0])
        if risk_ref is not None:
            risk_ref[0] = value
            await update.message.reply_text(f"Risk per trade set to {value*100:.2f}%.")
    except Exception:
        await update.message.reply_text("Usage: /setrisk [percent, e.g. 0.01 for 1%]")

async def setmaxloss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global maxloss_ref
    try:
        value = float(context.args[0])
        if maxloss_ref is not None:
            maxloss_ref[0] = value
            await update.message.reply_text(f"Max loss per day set to {value*100:.2f}%.")
    except Exception:
        await update.message.reply_text("Usage: /setmaxloss [percent, e.g. 0.03 for 3%]")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/pause - Pause signals\n"
        "/resume - Resume signals\n"
        "/status - Show bot status\n"
        "/setinterval [min] - Set signal interval\n"
        "/setrisk [0.01] - Set risk per trade\n"
        "/setmaxloss [0.03] - Set max loss per day\n"
        "/log - Show today's signals/trades\n"
        "/stats - Show win rate, avg PnL, drawdown\n"
        "/equitycurve - Show PnL graph\n"
        "/shutdown - Remotely shutdown the bot\n"
        "/symbol [SYMBOL] - Change trading symbol\n"
        "/version - Show bot version/config\n"
        "/retrain - Retrain the model\n"
        "/chatid - Show this chat's ID\n"
        "/help - Show this help message"
    )
    await update.message.reply_text(help_text)

async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global log_ref
    if log_ref is not None and log_ref[0]:
        await update.message.reply_text(f"Today's log:\n{log_ref[0]}")
    else:
        await update.message.reply_text("No log available.")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global running_ref
    if running_ref is not None:
        running_ref[0] = False
        await update.message.reply_text("Bot is shutting down (by user command). Bye!")

async def symbol(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global symbol_ref
    try:
        value = context.args[0].upper()
        if value in ["NIFTY", "BANKNIFTY"] and symbol_ref is not None:
            symbol_ref[0] = value
            await update.message.reply_text(f"Symbol changed to {value}.")
        else:
            await update.message.reply_text("Usage: /symbol [NIFTY|BANKNIFTY]")
    except Exception:
        await update.message.reply_text("Usage: /symbol [NIFTY|BANKNIFTY]")

async def version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Bot version: {version_str}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global log_ref
    if log_ref is not None and log_ref[0]:
        # Parse log lines
        lines = [l for l in log_ref[0].split('\n') if l.strip()]
        if not lines:
            await update.message.reply_text("No trades to analyze today.")
            return
        pnls = []
        for l in lines:
            if "PnL:" in l:
                try:
                    val = float(l.split("PnL:")[-1].split()[0])
                    pnls.append(val)
                except:
                    pass
        if not pnls:
            await update.message.reply_text("No PnL data in log.")
            return
        df = pd.DataFrame({'pnl': pnls})
        win_rate = (df['pnl'] > 0).mean() * 100
        avg_pnl = df['pnl'].mean()
        max_drawdown = df['pnl'].cumsum().min()
        best = df['pnl'].max()
        worst = df['pnl'].min()
        await update.message.reply_text(
            f"Today's Stats:\nWin Rate: {win_rate:.2f}%\nAvg PnL: {avg_pnl:.2f}\nMax Drawdown: {max_drawdown:.2f}\nBest: {best:.2f}\nWorst: {worst:.2f}"
        )
    else:
        await update.message.reply_text("No log available.")

async def equitycurve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global log_ref
    if log_ref is not None and log_ref[0]:
        lines = [l for l in log_ref[0].split('\n') if l.strip()]
        pnls = []
        for l in lines:
            if "PnL:" in l:
                try:
                    val = float(l.split("PnL:")[-1].split()[0])
                    pnls.append(val)
                except:
                    pass
        if not pnls:
            await update.message.reply_text("No PnL data in log.")
            return
        eq = pd.Series(pnls).cumsum()
        plt.figure(figsize=(6,3))
        plt.plot(eq, label="Equity Curve")
        plt.xlabel("Trade #")
        plt.ylabel("Cumulative PnL")
        plt.title("Equity Curve")
        plt.legend()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        await update.message.reply_photo(photo=buf)
        plt.close()
    else:
        await update.message.reply_text("No log available.")

async def retrain(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global retrain_ref
    if retrain_ref is not None:
        retrain_ref[0] = True
        await update.message.reply_text("Model retrain triggered!")
    else:
        await update.message.reply_text("Retrain not available.")

async def chatid(update, context):
    chat_id = update.effective_chat.id
    await update.message.reply_text(f"Your Chat ID is: `{chat_id}`", parse_mode="Markdown")

# Update set_advanced_refs to accept new refs

def set_advanced_refs(interval, risk, maxloss, log=None, running=None, symbol=None, version=None, retrain=None):
    global interval_ref, risk_ref, maxloss_ref, log_ref, running_ref, symbol_ref, version_str, retrain_ref
    interval_ref = interval
    risk_ref = risk
    maxloss_ref = maxloss
    log_ref = log
    running_ref = running
    symbol_ref = symbol
    retrain_ref = retrain
    if version:
        version_str = version

async def start_bot():
    await application.run_polling()

def start_bot_sync():
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("setinterval", setinterval))
    application.add_handler(CommandHandler("setrisk", setrisk))
    application.add_handler(CommandHandler("setmaxloss", setmaxloss))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("log", log_cmd))
    application.add_handler(CommandHandler("shutdown", shutdown))
    application.add_handler(CommandHandler("symbol", symbol))
    application.add_handler(CommandHandler("version", version))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("equitycurve", equitycurve))
    application.add_handler(CommandHandler("retrain", retrain))
    application.add_handler(CommandHandler("chatid", chatid))
    application.run_polling()

async def send_signal(message: str):
    try:
        await application.bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except Exception as e:
        from logger import log_error
        log_error(f"Telegram send_signal error: {e}")

# --- Market Hours Checker ---
def is_market_open() -> bool:
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
    return now.weekday() < 5 and (now.hour > 9 or (now.hour == 9 and now.minute >= 15)) and (now.hour < 15 or (now.hour == 15 and now.minute <= 30)) 