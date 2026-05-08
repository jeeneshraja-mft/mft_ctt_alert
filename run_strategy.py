from kite_connect import get_kite_instance
from gold_price import calculate_gold_strategy
from silver_price import calculate_silver_strategy
from telegram_alert import send_telegram_message
from telegram_bot import send_login_link, format_message


def run():
    print("🟡 Step 1: Starting strategy engine")

    kite = get_kite_instance()

    if kite is None:
        print("🔴 Token expired")
        send_login_link()
        return

    print("🟡 Step 2: Calculating GOLD")
    gold = calculate_gold_strategy(kite)

    print("🟡 Step 3: Calculating SILVER")
    silver = calculate_silver_strategy(kite)

    print("🟡 Step 4: Sending Telegram messages")

    send_telegram_message(
        format_message(gold, "🟡 GOLD")
    )

    send_telegram_message(
        format_message(silver, "⚪ SILVER")
    )

    print("✅ Strategy completed")


if __name__ == "__main__":
    run()