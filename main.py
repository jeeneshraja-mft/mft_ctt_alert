from kite_connect import get_kite_instance
from gold_price import fetch_today_high
from telegram_alert import send_telegram_message
from config import TRADINGSYMBOL

def main():
    kite = get_kite_instance()
    high_price = fetch_today_high(kite)
    if high_price:
        message = f"📈 <b>{TRADINGSYMBOL}</b> - Today's High: {high_price}"
        print(message)
        send_telegram_message(message)

if __name__ == "__main__":
    main()