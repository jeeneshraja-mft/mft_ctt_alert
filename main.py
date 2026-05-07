from kite_connect import get_kite_instance, get_login_url
from gold_price import calculate_gold_strategy
from silver_price import calculate_silver_strategy
from telegram_alert import send_telegram_message
from db_connect import load_token, is_token_valid


# ---------- FORMAT MESSAGE ----------
def format_message(data, title_color="📊"):
    return f"""
{title_color} <b>{data['tradingsymbol']} Strategy</b>

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


# ---------- LOGIN MESSAGE ----------
def send_login_prompt():
    login_url = get_login_url()

    message = f"""
🔐 <b>Kite Login Required</b>

Your session has expired.

👉 <a href="{login_url}">Click here to login</a>

After login, system will automatically resume trading signals.
"""

    send_telegram_message(message)


# ---------- MAIN RUN ----------
def run():
    try:
        access_token, expiry = load_token()

        # ❌ Token missing or expired
        if not access_token or not is_token_valid(expiry):
            print("❌ Token expired or missing")
            send_login_prompt()
            return

        # ✅ Kite instance
        kite = get_kite_instance()

        print("📊 Running Gold Strategy...")
        gold_data = calculate_gold_strategy(kite)

        print("📊 Running Silver Strategy...")
        silver_data = calculate_silver_strategy(kite)

        # ---------- SEND TELEGRAM ----------
        send_telegram_message(format_message(gold_data))
        send_telegram_message(format_message(silver_data))

        print("✅ All strategies executed successfully")

    except Exception as e:
        print("❌ Error in main execution:", e)
        send_telegram_message(f"❌ Bot Error: {str(e)}")


# ---------- ENTRY POINT ----------
if __name__ == "__main__":
    run()