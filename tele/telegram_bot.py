import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from brokers.kite_connect import get_kite_instance, generate_login_url
from strategies.gold_price import calculate_gold_strategy
from strategies.silver_price import calculate_silver_strategy
from strategies.nifty_options import calculate_nifty_options
from tele.telegram_alert import send_telegram_message
from dotenv import load_dotenv

# ✅ Import the new handlers
from strategies.gold_gapupdown import handle_rc_gold_request, get_latest_goldten_token
from strategies.silver_gapupdown import handle_rc_silver_request, get_latest_silver_token

# Load environment variables from .env
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# =========================================
# FORMAT MESSAGE
# =========================================
def format_message(data, title):
    if "error" in data:
        return f"{title}\n❌ Error: {data['error']}"
    return f"""{title}
Symbol: {data['tradingsymbol']}

BUY ENTRY: {data['buy_entry']}
BUY TARGET 1: {data['buy_target']}
BUY TARGET 2: {data['buy_target2']}
BUY SL1: {data['buy_sl1']}
BUY SL2: {data['buy_sl2']}

SELL ENTRY: {data['sell_entry']}
SELL TARGET 1: {data['sell_target']}
SELL TARGET 2: {data['sell_target2']}
SELL SL1: {data['sell_sl1']}
SELL SL2: {data['sell_sl2']}"""

# =========================================
# LOGIN LINK
# =========================================
def send_login_link():
    login_url = generate_login_url()
    send_telegram_message(f"🔐 Kite Login Required\n\n{login_url}")
    print("📨 Login link sent to Telegram")

# =========================================
# COMMANDS
# =========================================
async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Stock Alert Bot Running")

async def gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    if not kite:
        await update.message.reply_text("❌ Kite login expired")
        send_login_link()
        return
    try:
        gold = calculate_gold_strategy(kite)
        await update.message.reply_text(format_message(gold, "🟡 GOLD"))
    except Exception as e:
        await update.message.reply_text(f"❌ Gold strategy error: {e}")

async def silver_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    if not kite:
        await update.message.reply_text("❌ Kite login expired")
        send_login_link()
        return
    try:
        silver = calculate_silver_strategy(kite)
        await update.message.reply_text(format_message(silver, "⚪ SILVER"))
    except Exception as e:
        await update.message.reply_text(f"❌ Silver strategy error: {e}")

async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    if not kite:
        await update.message.reply_text("❌ Kite login expired")
        send_login_link()
        return
    try:
        gold = calculate_gold_strategy(kite)
        silver = calculate_silver_strategy(kite)
        instrument_token = 256265  # Nifty index token
        calculate_nifty_options(kite, instrument_token)

        await update.message.reply_text(format_message(gold, "🟡 GOLD"))
        await update.message.reply_text(format_message(silver, "⚪ SILVER"))
        await update.message.reply_text("📊 NIFTY strategy executed. Levels sent to Telegram.")
    except Exception as e:
        await update.message.reply_text(f"❌ Strategy run error: {e}")

async def nifty_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    if not kite:
        await update.message.reply_text("❌ Kite login expired")
        send_login_link()
        return
    try:
        instrument_token = 256265
        calculate_nifty_options(kite, instrument_token)
        await update.message.reply_text("📊 NIFTY strategy executed. Levels sent to Telegram.")
    except Exception as e:
        await update.message.reply_text(f"❌ Nifty strategy error: {e}")

# ✅ NEW GOLD RECALCULATION COMMAND
async def rc_gold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    if not kite:
        await update.message.reply_text("❌ Kite login expired")
        send_login_link()
        return
    try:
        instrument_token, tradingsymbol = get_latest_goldten_token(kite)
        handle_rc_gold_request(kite, instrument_token, tradingsymbol)
        await update.message.reply_text("📊 GOLD recalculation process triggered. Alerts will be sent to Telegram.")
    except Exception as e:
        await update.message.reply_text(f"❌ rc_gold error: {e}")

# ✅ NEW SILVER RECALCULATION COMMAND
async def rc_silver_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kite = get_kite_instance()
    if not kite:
        await update.message.reply_text("❌ Kite login expired")
        send_login_link()
        return
    try:
        instrument_token, tradingsymbol = get_latest_silver_token(kite)
        handle_rc_silver_request(kite, instrument_token, tradingsymbol)
        await update.message.reply_text("📊 SILVER recalculation process triggered. Alerts will be sent to Telegram.")
    except Exception as e:
        await update.message.reply_text(f"❌ rc_silver error: {e}")

# =========================================
# ERROR HANDLER
# =========================================
async def error_handler(update, context):
    print(f"⚠️ Error: {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ An error occurred")

# =========================================
# START BOT
# =========================================
def start_bot(use_signals=False):
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("gold", gold_command))
    app.add_handler(CommandHandler("silver", silver_command))
    app.add_handler(CommandHandler("run", run_command))
    app.add_handler(CommandHandler("nifty", nifty_command))
    app.add_handler(CommandHandler("rc_gold", rc_gold_command))     # ✅ Register new gold recalculation command
    app.add_handler(CommandHandler("rc_silver", rc_silver_command)) # ✅ Register new silver recalculation command
    app.add_error_handler(error_handler)

    print("🤖 Telegram bot running...")
    app.run_polling(drop_pending_updates=True, stop_signals=() if not use_signals else None)
