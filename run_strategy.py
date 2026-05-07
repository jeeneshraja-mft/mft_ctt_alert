from kite_connect import get_kite_instance
from gold_price import calculate_gold_strategy
from silver_price import calculate_silver_strategy
from telegram_alert import send_telegram_message
from telegram_bot import send_login_link


def run():
    print("🟡 Step 1: Starting strategy engine")

    kite = get_kite_instance()

    print("🟡 Step 2: Kite instance created")

    if kite is None:
        print("🔴 Token expired - sending login link")
        send_login_link()
        return

    print("🟡 Step 3: Fetching GOLD strategy")
    gold = calculate_gold_strategy(kite)
    print("🟢 GOLD calculated")

    print("🟡 Step 4: Fetching SILVER strategy")
    silver = calculate_silver_strategy(kite)
    print("🟢 SILVER calculated")

    print("🟡 Step 5: Sending Telegram messages")

    send_telegram_message(f"🟡 GOLD\n{gold}")
    send_telegram_message(f"⚪ SILVER\n{silver}")

    print("🟢 DONE - Messages sent")


if __name__ == "__main__":
    run()