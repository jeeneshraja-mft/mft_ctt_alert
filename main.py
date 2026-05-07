from kite_connect import get_kite_instance, get_login_url
from gold_price import calculate_gold_strategy
from silver_price import calculate_silver_strategy
from telegram_alert import send_telegram_message
from db_connect import load_token, is_token_valid


def send_login_prompt():
    login_url = get_login_url()

    message = f"""
🔐 <b>Kite Login Required</b>

Your session has expired.

👉 <a href="{login_url}">Click here to login</a>

After login, system will auto-resume.
"""

    send_telegram_message(message)


def run():
    access_token, expiry = load_token()

    if not access_token or not is_token_valid(expiry):
        print("❌ Token expired or missing")
        send_login_prompt()
        return

    try:
        kite = get_kite_instance()

        print("📊 Running Gold Strategy...")
        gold_result = calculate_gold_strategy(kite)

        print("📊 Running Silver Strategy...")
        silver_result = calculate_silver_strategy(kite)

        send_telegram_message(gold_result)
        send_telegram_message(silver_result)

        print("✅ Strategy executed successfully")

    except Exception as e:
        print("❌ Error in main execution:", e)


if __name__ == "__main__":
    run()