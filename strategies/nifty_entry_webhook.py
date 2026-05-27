import psycopg2
import os
from dotenv import load_dotenv
from kiteconnect import KiteTicker
from config.config import API_KEY
from database.db_connect import load_token
from datetime import datetime

load_dotenv()
SUPABASE_DSN = os.getenv("SUPABASE_DSN")

def fetch_today_tokens():
    """Fetch instrument tokens for today's CE/PE strikes from DB"""
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()
    today = datetime.today().date()
    cur.execute("""
        SELECT token, tradingsymbol
        FROM nifty_strategy
        WHERE strategy_date = %s
    """, (today,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    # Return both token and tradingsymbol for clarity
    return [{"token": row[0], "tradingsymbol": row[1]} for row in rows]


def start_tick_stream():
    access_token = load_token()
    if not access_token:
        print("❌ No access token found, please login again")
        return

    instrument_tokens = fetch_today_tokens()
    if not instrument_tokens:
        print("⚠️ No CE/PE tokens found in DB for today")
        return

    kws = KiteTicker(API_KEY, access_token)

    instrument_data = fetch_today_tokens()
    instrument_tokens = [row["token"] for row in instrument_data]

    def on_ticks(ws, ticks):
        for tick in ticks:
            # Find tradingsymbol for this token
            symbol = next((row["tradingsymbol"] for row in instrument_data 
                        if row["token"] == tick["instrument_token"]), None)
            print(f"📊 Tick: {symbol} (Token={tick['instrument_token']}) "
                f"LTP={tick['last_price']} OI={tick.get('oi')}")

    def on_connect(ws, response):
        print("✅ Tick WebSocket connected")
        ws.subscribe(instrument_tokens)
        ws.set_mode(ws.MODE_FULL, instrument_tokens)

    def on_close(ws, code, reason):
        print(f"❌ Tick WebSocket closed: {code} {reason}")

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    kws.connect(threaded=True)
