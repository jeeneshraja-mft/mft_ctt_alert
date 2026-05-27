from flask import Flask, request
from threading import Thread
from datetime import datetime, time as dtime

from brokers.kite_connect import get_kite_instance, generate_kite_session
from database.db_connect import save_token
from tele.telegram_bot import start_bot, send_login_link, format_message
from tele.telegram_alert import send_telegram_message
from strategies.gold_price import calculate_gold_strategy
from strategies.silver_price import calculate_silver_strategy
from strategies.gold_gapupdown import start_gold_gapupdown
from strategies.silver_gapupdown import start_silver_gapupdown
from strategies.nifty_options import start_nifty_options
from database.db_connect import save_token
from strategies.nifty_entry_webhook import fetch_nifty_levels, levels, last_alert_time


app = Flask(__name__)

# =========================================
# STRATEGY
# =========================================
def run_strategy():
    print("🚀 Running strategy")
    kite = get_kite_instance()
    if not kite:
        print("❌ Invalid Kite session")
        send_login_link()
        return

    print("✅ Kite login valid")
    try:
        print("🟡 Calculating GOLD")
        gold = calculate_gold_strategy(kite)
        print("⚪ Calculating SILVER")
        silver = calculate_silver_strategy(kite)

        send_telegram_message(format_message(gold, "🟡 GOLD"))
        send_telegram_message(format_message(silver, "⚪ SILVER"))
        print("✅ Strategy alerts sent")
    except Exception as e:
        print(f"❌ Strategy error: {e}")
        send_telegram_message(f"❌ Strategy error: {e}")

# =========================================
# ROUTES
# =========================================
@app.route("/")
def home():
    return "✅ Stock Alert App Running"

@app.route("/callback")
def callback():
    request_token = request.args.get("request_token")
    try:
        access_token = generate_kite_session(request_token)
        save_token(access_token)
        send_telegram_message("✅ Kite login successful")

        # Run strategy + monitoring in background
        Thread(target=run_strategy).start()
        Thread(target=start_gold_gapupdown, args=(False,), daemon=True).start()
        Thread(target=start_silver_gapupdown, args=(False,), daemon=True).start()
        Thread(target=start_nifty_options, daemon=True).start()

        return "<h2>✅ Login Successful</h2><h3>You can close this window</h3>"
    except Exception as e:
        return f"❌ Error: {str(e)}"

@app.route("/tick", methods=["POST"])
def tick_handler():
    """
    Webhook endpoint to receive tick data.
    Expected JSON: { "tradingsymbol": "NIFTY2660224150PE", "ltp": 199.0 }
    """
    data = request.json
    ts = data.get("tradingsymbol")
    ltp = data.get("ltp")

    if not ts or ts not in levels:
        return {"status": "ignored"}, 200

    entry = levels[ts]["entry"]
    option_type = levels[ts]["option_type"]

    now = datetime.now()
    current_time = now.time()

    # Only monitor between 9:15 and 9:30
    if current_time < dtime(9, 15) or current_time > dtime(9, 30):
        return {"status": "outside window"}, 200

    breached = False
    # ✅ Breach condition: price crosses below entry
    if ltp < entry:
        breached = True

    if breached:
        # Throttle alerts to once every 3 minutes per symbol
        last_sent = last_alert_time.get(ts)
        if not last_sent or (now - last_sent).seconds >= 180:
            send_telegram_message(
                f"⚠️ {option_type} Entry Breach!\n"
                f"{ts} crossed below entry {entry} → LTP {ltp}"
            )
            last_alert_time[ts] = now

    return {"status": "processed"}, 200


# =========================================
# MAIN
# =========================================
if __name__ == "__main__":
    print("🚀 Starting Stock Alert App")

    # ✅ Start Telegram bot in background thread with signals disabled
    Thread(target=lambda: start_bot(use_signals=False), daemon=True).start()

    # Check token immediately
    kite = get_kite_instance()
    if kite:
        Thread(target=run_strategy).start()
        Thread(target=start_gold_gapupdown, daemon=True).start()
        Thread(target=start_silver_gapupdown, daemon=True).start()
        Thread(target=start_nifty_options, daemon=True).start()
    else:
        send_login_link()

    # Start Flask
    app.run(host="0.0.0.0", port=10000, use_reloader=False)
