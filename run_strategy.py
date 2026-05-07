from kite_connect import get_kite_instance
from gold_price import calculate_gold_strategy
from silver_price import calculate_silver_strategy
from telegram_alert import send_telegram_message


def run():
    kite = get_kite_instance()

    if kite is None:
        send_telegram_message("❌ Token expired")
        return

    gold = calculate_gold_strategy(kite)
    silver = calculate_silver_strategy(kite)

    send_telegram_message(f"🟡 GOLD\n{gold}")
    send_telegram_message(f"⚪ SILVER\n{silver}")


if __name__ == "__main__":
    run()