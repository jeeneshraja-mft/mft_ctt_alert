from kite_connect import get_kite_instance
from gold_price import fetch_strategy_levels
from silver_price import fetch_silver_strategy_levels
from telegram_alert import send_telegram_message, listen_for_commands
from db_connect import insert_strategy_levels
from config import TELEGRAM_CHAT_ID


# =========================
# 📩 FORMAT MESSAGE
# =========================
def format_message(levels):
    return f"""
📊 <b>{levels['tradingsymbol']} Strategy</b>

🟢 BUY
Entry: {levels['buy_entry']}
Target1: {levels['buy_target']}
Target2: {levels['buy_target2']}
SL1: {levels['buy_sl1']}
SL2: {levels['buy_sl2']}

🔴 SELL
Entry: {levels['sell_entry']}
Target1: {levels['sell_target']}
Target2: {levels['sell_target2']}
SL1: {levels['sell_sl1']}
SL2: {levels['sell_sl2']}
"""


# =========================
# 🚀 RUN FULL STRATEGY
# =========================
def run_full_strategy():
    kite = get_kite_instance()

    # ===== GOLD =====
    gold_levels = fetch_strategy_levels(kite)
    insert_strategy_levels(gold_levels)

    gold_msg = format_message(gold_levels)
    print(gold_msg)
    send_telegram_message(gold_msg)

    print("✅ Gold strategy stored & sent")

    # ===== SILVER =====
    silver_levels = fetch_silver_strategy_levels(kite)
    insert_strategy_levels(silver_levels)

    silver_msg = format_message(silver_levels)
    print(silver_msg)
    send_telegram_message(silver_msg)

    print("✅ Silver strategy stored & sent")


# =========================
# 🎮 TELEGRAM COMMAND HANDLER
# =========================
def handle_command(update_text, chat_id):
    # 🔐 Allow only your chat
    if str(chat_id) != str(TELEGRAM_CHAT_ID):
        print(f"⚠️ Unauthorized access attempt from {chat_id}")
        return

    text = update_text.lower().strip()

    try:
        if text == "/run":
            send_telegram_message("🚀 Running full strategy...")
            run_full_strategy()

        elif text == "/gold":
            kite = get_kite_instance()
            gold = fetch_strategy_levels(kite)
            send_telegram_message(format_message(gold))

        elif text == "/silver":
            kite = get_kite_instance()
            silver = fetch_silver_strategy_levels(kite)
            send_telegram_message(format_message(silver))

        elif text == "/status":
            send_telegram_message("✅ Bot is running and ready")

        else:
            send_telegram_message("❓ Unknown command")

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        send_telegram_message(error_msg)


# =========================
# 🤖 TELEGRAM LISTENER LOOP
# =========================
def start_bot():
    print("🤖 Bot started. Listening for commands...")

    def callback(text, chat_id):
        print(f"📩 Command from {chat_id}: {text}")
        handle_command(text, chat_id)

    listen_for_commands(callback)


# =========================
# ▶️ ENTRY POINT
# =========================
if __name__ == "__main__":
    start_bot()