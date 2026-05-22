import pandas as pd
from datetime import datetime, timedelta
import math
from kiteconnect import KiteConnect
from config.config import API_KEY
from database.db_connect import load_token
from tele.telegram_alert import send_telegram_message

# ---------- Get Kite Instance ----------
def get_kite_instance():
    token = load_token()
    if not token:
        return None
    kite = KiteConnect(api_key=API_KEY)
    kite.set_access_token(token)
    return kite

# ---------- Utility ----------
def mround(value, base=1):
    return round(value / base) * base

def ceiling(value, base=50):
    return int(math.ceil(value / base) * base)

def floor(value, base=50):
    return int(math.floor(value / base) * base)

# ---------- Load Nifty historical data ----------
def load_nifty_data(kite, instrument_token):
    today = datetime.today().date()
    from_date = today - timedelta(days=10)
    data = kite.historical_data(instrument_token, from_date, today, "day")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[df["date"] < today].sort_values(by="date", ascending=False)
    return df

# ---------- Expiry Selection ----------
def get_all_expiries(kite):
    instruments = kite.instruments("NFO")
    nifty_options = [i for i in instruments if i["name"] == "NIFTY" and i["instrument_type"] in ["CE","PE"]]
    expiries = sorted(set([i["expiry"] for i in nifty_options]))
    return expiries

def get_weekly_expiry(kite):
    expiries = get_all_expiries(kite)
    today = datetime.today().date()
    weekday = today.weekday()

    if not expiries:
        send_telegram_message("❌ No NIFTY option expiries found")
        return None

    current_expiry = expiries[0]
    print("Available expiries:", expiries)
    print("Current expiry chosen:", current_expiry)

    if current_expiry.weekday() == 1:  # Tuesday expiry
        if weekday in [0, 1]:
            return expiries[1] if len(expiries) > 1 else current_expiry
        else:
            return current_expiry
    elif current_expiry.weekday() == 0:  # Monday expiry
        if weekday == 4:
            return expiries[1] if len(expiries) > 1 else current_expiry
        else:
            return current_expiry
    else:
        return current_expiry

# ---------- Strike Mapping ----------
def find_strikes_for_expiry(kite, expiry):
    instruments = kite.instruments("NFO")
    expiry_instruments = [i for i in instruments if i["expiry"] == expiry and i["name"] == "NIFTY"]

    symbol_map = {}
    for inst in expiry_instruments:
        key = f"{int(inst['strike'])}{inst['instrument_type']}"
        symbol_map[key] = {
            "tradingsymbol": inst["tradingsymbol"],
            "token": inst["instrument_token"]
        }

    return symbol_map

# ---------- Strike Eligibility with Logs ----------
def check_strike_eligibility(kite, tradingsymbol, instrument_token, strike, threshold_oi=32500):
    today = datetime.today().date()
    from_date = today - timedelta(days=5)

    try:
        data = kite.historical_data(instrument_token, from_date, today, "day")
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[df["date"] < today].sort_values(by="date", ascending=False)

        if df.empty:
            return False

        low2 = df.head(2)["low"].min()
        threshold = strike * 0.0085

        quote = kite.quote([f"NFO:{tradingsymbol}"])
        oi = quote[f"NFO:{tradingsymbol}"]["oi"]

        # Log details
        print(f"{tradingsymbol} => {threshold:.2f} (0.85%) => {low2} (2d low) => {oi} (OI)")

        return oi >= threshold_oi and low2 > threshold

    except Exception as e:
        print(f"Eligibility check failed for {tradingsymbol}: {e}")
        return False

# ---------- Calculate Nifty Option Strikes ----------
def calculate_nifty_options(kite, instrument_token):
    df = load_nifty_data(kite, instrument_token)

    A = df.head(2)["high"].max()
    B = df.head(2)["low"].min()

    # Anchors
    PE_END = floor(A, 50)    # nearest strike <= A
    CE_END = floor(B, 50)    # nearest strike <= B
    CE_START = ceiling(A, 50)  # nearest strike >= A

    # Generate candidate strikes
    PE_strikes = list(range(PE_END, PE_END - 50*10, -50))
    CE_strikes = list(range(CE_START, CE_END - 50, -50))  # descending from CE_START to CE_END

    expiries = get_all_expiries(kite)
    expiry = get_weekly_expiry(kite)
    if not expiry:
        return

    symbol_map = find_strikes_for_expiry(kite, expiry)

    # Find eligible PE_TODAY
    PE_TODAY, PE_TS = None, None
    for strike in PE_strikes:
        key = f"{strike}PE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            if check_strike_eligibility(kite, ts, token, strike):
                PE_TODAY, PE_TS = strike, ts
                break

    # Find eligible CE_TODAY
    CE_TODAY, CE_TS = None, None
    for strike in CE_strikes:
        key = f"{strike}CE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            if check_strike_eligibility(kite, ts, token, strike):
                CE_TODAY, CE_TS = strike, ts
                break

    send_telegram_message(
        f"📊 NIFTY Options Levels\n"
        f"Expiry: {expiry}\n"
        f"A (2d High): {A}\nB (2d Low): {B}\n"
        f"PE_END: {PE_END}, PE_TODAY: {PE_TODAY} ({PE_TS if PE_TS else '-'})\n"
        f"CE_START: {CE_START}, CE_END: {CE_END}, CE_TODAY: {CE_TODAY} ({CE_TS if CE_TS else '-'})"
    )

    return {
        "expiry": expiry,
        "PE_END": PE_END,
        "PE_TODAY": PE_TODAY,
        "CE_START": CE_START,
        "CE_END": CE_END,
        "CE_TODAY": CE_TODAY
    }

# ---------- Public entry point ----------
def start_nifty_options():
    kite = get_kite_instance()
    if not kite:
        send_telegram_message("❌ Kite login expired, please login again")
        return

    instrument_token = 256265  # Nifty index token
    calculate_nifty_options(kite, instrument_token)
