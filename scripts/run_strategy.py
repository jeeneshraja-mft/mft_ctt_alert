from brokers.kite_connect import get_kite_instance
from strategies.gold_price import calculate_gold_strategy
from strategies.silver_price import calculate_silver_strategy
from tele.telegram_alert import send_telegram_message
from tele.telegram_bot import send_login_link, format_message


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