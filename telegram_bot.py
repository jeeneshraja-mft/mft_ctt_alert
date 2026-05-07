from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from kite_connect import get_kite_instance
from gold_price import calculate_gold_strategy
from silver_price import calculate_silver_strategy
from db_connect import load_token, is_token_valid
from config import TELEGRAM_BOT_TOKEN


# ---------- FORMAT ----------
def format_message(data, title="📊"):
    return f"""
{title} <b>{data['tradingsymbol']} Strategy</b>

🟢 BUY
Entry: {data['buy_entry']}
Target1: {data['buy_target']}
Target2: {data['buy_target2']}
SL1: {data['buy_sl1']}
SL2: {data['buy_sl2']}

🔴 SELL
Entry: {data['sell_entry']}
Target1: {data['sell_target']}
Target2: {data['sell_target2']}
SL1: {data['sell_sl1']}
SL2: {data['sell_sl2']}
"""


# ---------- /RUN ----------
async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access_token, expiry = load_token()

    if not access_token or not is_token_valid(expiry):
        await update.message.reply_text("❌ Token expired. Please login via Telegram link.")
        return

    kite = get_kite_instance()

    gold = calculate_gold_strategy(kite)
    silver = calculate_silver_strategy(kite)

    await update.message.reply_text("🚀 Running full strategy...")

    await update.message.reply_text(format_message(gold, "🟡 GOLD"))
    await update.message.reply_text(format_message(silver, "⚪ SILVER"))


# ---------- /GOLD ----------
async def gold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    gold = calculate_gold_strategy(kite)

    await update.message.reply_text(format_message(gold, "🟡 GOLD"))


# ---------- /SILVER ----------
async def silver_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    silver = calculate_silver_strategy(kite)

    await update.message.reply_text(format_message(silver, "⚪ SILVER"))


# ---------- /STATUS ----------
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access_token, expiry = load_token()

    if access_token and is_token_valid(expiry):
        msg = "🟢 Bot is ACTIVE\nToken is valid"
    else:
        msg = "🔴 Bot is INACTIVE\nToken expired or missing"

    await update.message.reply_text(msg)


# ---------- START BOT ----------
def start_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("run", run_cmd))
    app.add_handler(CommandHandler("gold", gold_cmd))
    app.add_handler(CommandHandler("silver", silver_cmd))
    app.add_handler(CommandHandler("status", status_cmd))

    print("🤖 Telegram bot running...")

    app.run_polling()