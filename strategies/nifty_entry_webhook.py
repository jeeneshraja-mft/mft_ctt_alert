import psycopg2
import os
import time
from datetime import datetime
from dotenv import load_dotenv
from kiteconnect import KiteTicker
from config.config import API_KEY
from database.db_connect import load_token
from tele.telegram_alert import send_telegram_message

load_dotenv()
SUPABASE_DSN = os.getenv("SUPABASE_DSN")

# ---------- Fetch today's CE/PE strikes ----------
def fetch_today_tokens():
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()
    today = datetime.today().date()
    cur.execute("""
        SELECT token, tradingsymbol, option_type, entry, stoploss, target
        FROM nifty_strategy
        WHERE strategy_date = %s
    """, (today,))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "token": row[0],
            "tradingsymbol": row[1],
            "option_type": row[2],
            "entry": float(row[3]),
            "stoploss": float(row[4]),
            "target": float(row[5])
        }
        for row in rows if row[0]
    ]

# ---------- Tick Stream ----------
def start_tick_stream():
    access_token = load_token()
    if not access_token:
        print("❌ No access token found, please login again")
        return

    instrument_data = fetch_today_tokens()
    instrument_tokens = [row["token"] for row in instrument_data]

    if not instrument_tokens:
        print("⚠️ No instrument tokens found for today, cannot subscribe")
        return

    kws = KiteTicker(API_KEY, access_token)

    # Track last alert time per symbol to throttle
    last_alert_time = {}

    def on_ticks(ws, ticks):
        now = datetime.now()
        for tick in ticks:
            symbol_info = next((row for row in instrument_data
                                if row["token"] == tick["instrument_token"]), None)
            if not symbol_info:
                continue

            ts = symbol_info["tradingsymbol"]
            opt_type = symbol_info["option_type"]
            entry = symbol_info["entry"]

            ltp = tick["last_price"]
            oi = tick.get("oi")

            print(f"📊 Tick: {ts} (Token={tick['instrument_token']}) LTP={ltp} OI={oi}")

            # Only check between 9:15 and 9:30
            if now.hour == 9 and 15 <= now.minute <= 30:
                breached = False
                if opt_type == "PE" and ltp < entry:
                    breached = True
                elif opt_type == "CE" and ltp > entry:
                    breached = True

                if breached:
                    last_sent = last_alert_time.get(ts)
                    if not last_sent or (now - last_sent).seconds >= 180:
                        send_telegram_message(
                            f"⚠️ {opt_type} Entry Breach!\n"
                            f"{ts} crossed entry {entry} → LTP {ltp}"
                        )
                        last_alert_time[ts] = now

    def on_connect(ws, _response):
        print("✅ Tick WebSocket connected")
        ws.subscribe(instrument_tokens)
        ws.set_mode(ws.MODE_FULL, instrument_tokens)

    def on_close(ws, code, reason):
        print(f"❌ Tick WebSocket closed: {code} {reason}")

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    kws.connect(threaded=True)
