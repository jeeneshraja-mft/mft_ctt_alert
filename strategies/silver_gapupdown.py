import pandas as pd
from datetime import datetime, timedelta
import psycopg2
import pytz
import time
from kiteconnect import KiteConnect, KiteTicker
from config.config import SUPABASE_DSN, API_KEY
from database.db_connect import load_token
from tele.telegram_alert import send_telegram_message
from strategies.silver_price import get_latest_silver_token, mround

# ---------- Globals ----------
breached_up = False
breached_down = False
breach_type_up = None
breach_type_down = None
next_alert_up = None
next_alert_down = None
levels = None
instrument_token = None
tradingsymbol = None

# ---------- Get Kite Instance ----------
def get_kite_instance():
    token = load_token()
    if not token:
        return None, None
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(token)
    return kite, token

# ---------- Load silver strategy levels from DB ----------
def load_silver_strategy_from_db():
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()
    cur.execute("""
        SELECT buy_entry, sell_entry
        FROM silver_strategy
        WHERE strategy_date = CURRENT_DATE
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return {"buy_entry": row[0], "sell_entry": row[1]}
    return None

# ---------- Tick Handler ----------
def on_ticks(ws, ticks):
    global breached_up, breached_down, breach_type_up, breach_type_down
    global next_alert_up, next_alert_down, levels

    tick = ticks[0]["last_price"]

    # Gap-Up Buy Entry check
    if tick >= levels["buy_entry"] and not breached_up:
        breach_type_up = f"Silver Gapup BUY Entry breached ({levels['buy_entry']})"
        send_telegram_message(f"⚪ {breach_type_up} at {tick}")
        breached_up = True
        next_alert_up = datetime.now() + timedelta(minutes=3)

    if breached_up and datetime.now() >= next_alert_up and datetime.now().hour == 9 and datetime.now().minute < 15:
        send_telegram_message(f"⚠️ Reminder: {breach_type_up}, current price {tick}")
        next_alert_up = datetime.now() + timedelta(minutes=3)

    # Gap-Down Sell Entry check
    if tick <= levels["sell_entry"] and not breached_down:
        breach_type_down = f"Silver Gapdown SELL Entry breached ({levels['sell_entry']})"
        send_telegram_message(f"🔻 {breach_type_down} at {tick}")
        breached_down = True
        next_alert_down = datetime.now() + timedelta(minutes=3)

    if breached_down and datetime.now() >= next_alert_down and datetime.now().hour == 9 and datetime.now().minute < 15:
        send_telegram_message(f"⚠️ Reminder: {breach_type_down}, current price {tick}")
        next_alert_down = datetime.now() + timedelta(minutes=3)

    # At 9:15 → recalc levels if breached
    if (breached_up or breached_down) and datetime.now().hour == 9 and datetime.now().minute == 15:
        recalc_levels(ws.kite, instrument_token, tradingsymbol)
        ws.close()

# ---------- Recalculate levels ----------
def recalc_levels(kite, instrument_token, tradingsymbol):
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    today = now_ist.date()

    start_time = ist.localize(datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0))
    end_time = ist.localize(datetime.combine(today, datetime.min.time()).replace(hour=9, minute=10))

    data = kite.historical_data(instrument_token, start_time, end_time, "minute")
    if not data:
        send_telegram_message("❌ No minute data found for 9:00–9:10 IST")
        return

    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"])
    session_high = df["high"].max()
    session_low = df["low"].min()

    levels = load_silver_strategy_from_db()
    if not levels:
        send_telegram_message("❌ No silver strategy levels found in DB")
        return

    buy_entry = levels["buy_entry"]
    sell_entry = levels["sell_entry"]

    crossed_buy = session_high >= buy_entry
    crossed_sell = session_low <= sell_entry

    if not crossed_buy and not crossed_sell:
        send_telegram_message(
            f"ℹ️ Between 9:00–9:10 IST, price stayed within range.\n"
            f"High: {session_high}, Low: {session_low}\n"
            f"Buy Entry: {buy_entry}, Sell Entry: {sell_entry}"
        )
        return

    if crossed_buy:
        entry_up = mround(session_high * (1 + 0.0012), 1)
        target_up = mround(entry_up * (1 + 0.02), 1)
        sl1_up = mround(max(entry_up * (1 - 0.02), session_low * (1 - 0.0012)), 1)
        sl2_up = mround(max(entry_up * (1 - 0.02), session_low * (1 - 0.0012)), 1)
        send_telegram_message(
            f"📊 SILVER Gap-Up Recalculated (9:00–9:10 IST)\n"
            f"Entry: {entry_up}\nTarget: {target_up}\nSL1: {sl1_up}\nSL2: {sl2_up}"
        )

    if crossed_sell:
        entry_down = mround(session_low * (1 - 0.0012), 1)
        target_down = mround(entry_down * (1 - 0.02), 1)
        sl1_down = mround(min(entry_down * (1 + 0.02), session_high * (1 + 0.0012)), 1)
        sl2_down = mround(min(entry_down * (1 + 0.02), session_high * (1 + 0.0012)), 1)
        send_telegram_message(
            f"📊 SILVER Gap-Down Recalculated (9:00–9:10 IST)\n"
            f"Entry: {entry_down}\nTarget: {target_down}\nSL1: {sl1_down}\nSL2: {sl2_down}"
        )

# ---------- Manual Command Handler ----------
def handle_rc_silver_request(kite, instrument_token, tradingsymbol):
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    target_time = now_ist.replace(hour=9, minute=10, second=0, microsecond=0)

    if now_ist < target_time:
        send_telegram_message("✅ silver recalculation request received, recalculation activated.")
        time.sleep(5)
        send_telegram_message("⏳ SILVER process is running…")
        time.sleep(5)
        remaining = int((target_time - datetime.now(ist)).total_seconds() / 60)
        send_telegram_message(f"📢 SILVER alert will be sent in ~{remaining} minutes (at 9:10 IST).")

        sleep_seconds = (target_time - datetime.now(ist)).total_seconds()
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

        recalc_levels(kite, instrument_token, tradingsymbol)
    else:
        send_telegram_message("⚡ silver recalculation request received, recalculating immediately…")
        recalc_levels(kite, instrument_token, tradingsymbol)

# ---------- Public entry point ----------
def start_silver_gapupdown():
    kite, token = get_kite_instance()
    if not kite:
        send_telegram_message("❌ Kite login expired, please login again")
        return

    global levels, instrument_token, tradingsymbol
    levels = load_silver_strategy_from_db()
    if not levels:
        send_telegram_message("❌ No silver strategy levels found in DB")
        return

    instrument_token, tradingsymbol = get_latest_silver_token(kite)

    kws = KiteTicker(API_KEY, token)
    kws.kite = kite
    kws.on_ticks = on_ticks
    kws.on_connect = lambda ws, _: ws.subscribe([instrument_token])
    kws.connect(threaded=True)
