import time
from datetime import datetime, time as dtime
import psycopg2
import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from tele.telegram_alert import send_telegram_message

load_dotenv()
SUPABASE_DSN = os.getenv("SUPABASE_DSN")

app = Flask(__name__)

# Cache entry levels from DB
def fetch_nifty_levels():
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()
    today = datetime.today().date()
    cur.execute("""
        SELECT tradingsymbol, option_type, entry
        FROM nifty_strategy
        WHERE strategy_date = %s
    """, (today,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return {row[0]: {"option_type": row[1], "entry": row[2]} for row in rows}

levels = fetch_nifty_levels()

# Track last alert time per symbol
last_alert_time = {}

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
        return jsonify({"status": "ignored"}), 200

    entry = levels[ts]["entry"]
    option_type = levels[ts]["option_type"]

    now = datetime.now()
    current_time = now.time()

    # Only monitor between 9:15 and 9:30
    if current_time < dtime(9, 15) or current_time > dtime(9, 30):
        return jsonify({"status": "outside window"}), 200

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

    return jsonify({"status": "processed"}), 200
