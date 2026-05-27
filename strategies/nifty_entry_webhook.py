import psycopg2
import os
import time
import math
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from kiteconnect import KiteTicker, KiteConnect
from config.config import API_KEY
from database.db_connect import load_token, save_nifty_strategy
from tele.telegram_alert import send_telegram_message
from strategies.nifty_options import (
    get_all_expiries,
    find_strikes_for_expiry,
    check_strike_eligibility,
    calculate_entry_levels,
)

load_dotenv()
SUPABASE_DSN = os.getenv("SUPABASE_DSN")

# ---------- Utility ----------
def mround(value, base=1):
    return round(value / base) * base

def ceiling(value, base=50):
    return int(math.ceil(value / base) * base)

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

# ---------- Recalculate PE levels after breach ----------
def recalc_pe_levels(kite):
    try:
        # Get today's Nifty spot high till 9:30
        instrument_token = 256265  # Nifty index token
        today = datetime.today().date()
        data = kite.historical_data(instrument_token, today, today, "minute")
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"].dt.time <= datetime.strptime("09:30", "%H:%M").time()]

        if df.empty:
            print("⚠️ No intraday data available for Nifty till 9:30")
            return

        todays_high = df["high"].max()
        buffer_high = mround(todays_high * (1 + 0.00125), 1)  # 0.125%
        pe_end_strike = ceiling(buffer_high, 50)

        # Build PE strike list from pe_end_strike downwards
        PE_strikes = list(range(pe_end_strike, pe_end_strike - (50 * 9), -50))
        PE_strikes.reverse()

        # Expiry fallback: current → next → next-to-next
        expiries = get_all_expiries(kite)
        if not expiries:
            return

        eligible_pe_ts = None
        eligible_pe_token = None

        for expiry_index in range(min(3, len(expiries))):
            expiry = expiries[expiry_index]
            print(f"🔍 Checking expiry {expiry} for recalculated PE strike")
            symbol_map = find_strikes_for_expiry(kite, expiry)

            for strike in PE_strikes:
                key = f"{strike}PE"
                if key in symbol_map:
                    ts = symbol_map[key]["tradingsymbol"]
                    token = symbol_map[key]["token"]
                    result = check_strike_eligibility(kite, ts, token, strike)
                    if result and "✅ Eligible" in result:
                        eligible_pe_ts = ts
                        eligible_pe_token = token
                        break

            if eligible_pe_ts and eligible_pe_token:
                break  # ✅ stop once found

        if eligible_pe_ts and eligible_pe_token:
            pe_levels = calculate_entry_levels(kite, eligible_pe_ts, eligible_pe_token, option_type="PE")
            if pe_levels:
                send_telegram_message(
                    f"🔄 Recalculated PE Levels for {eligible_pe_ts}\n"
                    f"2D High: {pe_levels['2D_HIGH']}\n"
                    f"2D Low: {pe_levels['2D_LOW']}\n"
                    f"Entry: {pe_levels['ENTRY']}\n"
                    f"Target: {pe_levels['TARGET']}\n"
                    f"Stoploss: {pe_levels['STOPLOSS']}"
                )
                save_nifty_strategy({
                    "strategy_date": datetime.today().date(),
                    "tradingsymbol": eligible_pe_ts,
                    "token": eligible_pe_token,
                    "option_type": "PE",
                    **pe_levels
                })
    except Exception as e:
        print(f"❌ Error in PE recalculation: {e}")

# ---------- Recalculate CE levels after breach ----------
def recalc_ce_levels(kite):
    try:
        instrument_token = 256265  # Nifty index token
        today = datetime.today().date()
        data = kite.historical_data(instrument_token, today, today, "minute")
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"].dt.time <= datetime.strptime("09:30", "%H:%M").time()]

        if df.empty:
            print("⚠️ No intraday data available for Nifty till 9:30")
            return

        todays_low = df["low"].min()
        buffer_low = mround(todays_low * (1 - 0.00125), 1)  # 0.125% below
        ce_end_strike = floor(buffer_low, 50)

        # Build CE strike list upwards from ce_end_strike
        CE_strikes = list(range(ce_end_strike, ce_end_strike + (50 * 9), 50))
        CE_strikes.reverse()

        expiries = get_all_expiries(kite)
        if not expiries:
            return

        eligible_ce_ts = None
        eligible_ce_token = None

        for expiry_index in range(min(3, len(expiries))):
            expiry = expiries[expiry_index]
            print(f"🔍 Checking expiry {expiry} for recalculated CE strike")
            symbol_map = find_strikes_for_expiry(kite, expiry)

            for strike in CE_strikes:
                key = f"{strike}CE"
                if key in symbol_map:
                    ts = symbol_map[key]["tradingsymbol"]
                    token = symbol_map[key]["token"]
                    result = check_strike_eligibility(kite, ts, token, strike)
                    if result and "✅ Eligible" in result:
                        eligible_ce_ts = ts
                        eligible_ce_token = token
                        break

            if eligible_ce_ts and eligible_ce_token:
                break

        if eligible_ce_ts and eligible_ce_token:
            ce_levels = calculate_entry_levels(kite, eligible_ce_ts, eligible_ce_token, option_type="CE")
            if ce_levels:
                send_telegram_message(
                    f"🔄 Recalculated CE Levels for {eligible_ce_ts}\n"
                    f"2D High: {ce_levels['2D_HIGH']}\n"
                    f"2D Low: {ce_levels['2D_LOW']}\n"
                    f"Entry: {ce_levels['ENTRY']}\n"
                    f"Target: {ce_levels['TARGET']}\n"
                    f"Stoploss: {ce_levels['STOPLOSS']}"
                )
                save_nifty_strategy({
                    "strategy_date": datetime.today().date(),
                    "tradingsymbol": eligible_ce_ts,
                    "token": eligible_ce_token,
                    "option_type": "CE",
                    **ce_levels
                })
    except Exception as e:
        print(f"❌ Error in CE recalculation: {e}")

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
    last_alert_time = {}
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(access_token)

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

                        # Trigger recalculation
                        if opt_type == "PE":
                            recalc_pe_levels(kite)
                        elif opt_type == "CE":
                            recalc_ce_levels(kite)

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
