from tele.telegram_alert import send_telegram_message
from brokers.kite_connect import get_kite_instance

def fetch_positions_and_alert():
    try:
        kite = get_kite_instance()
        positions = kite.positions()["net"]

        if not positions:
            send_telegram_message("No running positions found in Kite.")
            return

        for pos in positions:
            tradingsymbol = pos["tradingsymbol"]
            qty = pos["quantity"]
            avg_price = pos["average_price"]
            pnl = pos["pnl"]

            # Build alert message
            msg = (
                f"📊 Position Alert\n"
                f"Symbol: {tradingsymbol}\n"
                f"Quantity: {qty}\n"
                f"Entry Price: {avg_price}\n"
                f"PnL: {pnl}"
            )

            # Trigger Telegram alert
            send_telegram_message(msg)

    except Exception as e:
        send_telegram_message(f"⚠️ Error fetching positions: {str(e)}")
