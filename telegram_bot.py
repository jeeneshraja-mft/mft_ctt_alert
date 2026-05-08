from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from kite_connect import get_kite_instance
from gold_price import calculate_gold_strategy
from silver_price import calculate_silver_strategy
from db_connect import load_token, is_token_valid
from config import TELEGRAM_BOT_TOKEN
from telegram_alert import send_telegram_message


# ---------------- LOGIN LINK ----------------
def send_login_link():
    from kiteconnect import KiteConnect
    from config import API_KEY

    kite = KiteConnect(api_key=API_KEY)
    login_url = "https://kite-token-server.onrender.com/login"

    msg = f"""
🔐 <b>Kite Login Required</b>

Session expired.

👉 <a href="{login_url}">Click here to login</a>

After login, bot will resume automatically.
"""

    send_telegram_message(msg)


# ---------------- FORMAT MESSAGE ----------------
def format_message(data, title):
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


# ---------------- /RUN ----------------
async def run_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()

    if kite is None:
        send_login_link()
        await update.message.reply_text("❌ Token expired. Login link sent.")
        return

    gold = calculate_gold_strategy(kite)
    silver = calculate_silver_strategy(kite)

    await update.message.reply_text("🚀 Running full strategy...")

    send_telegram_message(format_message(gold, "🟡 GOLD"))
    send_telegram_message(format_message(silver, "⚪ SILVER"))


# ---------------- /GOLD ----------------
async def gold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()

    if kite is None:
        send_login_link()
        await update.message.reply_text("❌ Token expired. Login link sent.")
        return

    gold = calculate_gold_strategy(kite)
    send_telegram_message(format_message(gold, "🟡 GOLD"))

    await update.message.reply_text("✅ Gold sent")


# ---------------- /SILVER ----------------
async def silver_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()

    if kite is None:
        send_login_link()
        await update.message.reply_text("❌ Token expired. Login link sent.")
        return

    silver = calculate_silver_strategy(kite)
    send_telegram_message(format_message(silver, "⚪ SILVER"))

    await update.message.reply_text("✅ Silver sent")


# ---------------- /STATUS ----------------
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    access_token, expiry = load_token()

    if access_token and is_token_valid(expiry):
        msg = "🟢 Bot ACTIVE\nToken valid"
    else:
        msg = "🔴 Bot INACTIVE\nToken expired or missing"

    await update.message.reply_text(msg)


# ---------------- START BOT ----------------
def start_bot():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("run", run_cmd))
    app.add_handler(CommandHandler("gold", gold_cmd))
    app.add_handler(CommandHandler("silver", silver_cmd))
    app.add_handler(CommandHandler("status", status_cmd))

    print("🤖 Telegram bot running...")

    app.run_polling()