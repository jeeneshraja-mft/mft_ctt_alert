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

    # rollover logic: skip expiry if too close
    days_to_expiry = (current_expiry - today).days
    if (current_expiry.weekday() == 1 and weekday == 0) or \
       (current_expiry.weekday() == 0 and weekday == 4) or \
       days_to_expiry <= 2:
        return expiries[1] if len(expiries) > 1 else current_expiry
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

# ---------- Strike Eligibility ----------
def check_strike_eligibility(kite, tradingsymbol, instrument_token, strike, threshold_oi=35000):
    today = datetime.today().date()
    from_date = today - timedelta(days=5)

    try:
        data = kite.historical_data(instrument_token, from_date, today, "day")
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[df["date"] < today].sort_values(by="date", ascending=False)

        if df.empty:
            return None, False

        low2 = df.head(2)["low"].min()
        threshold = strike * 0.0085

        quote = kite.quote([f"NFO:{tradingsymbol}"])
        oi = quote[f"NFO:{tradingsymbol}"]["oi"]

        eligible = (oi >= threshold_oi) and (low2 > threshold)
        status = "✅ Eligible" if eligible else "❌ Not Eligible"
        return f"{tradingsymbol} => {threshold:.2f} (0.85%) => {low2} (2d low) => {oi} (OI) => {status}", eligible

    except Exception as e:
        print(f"Eligibility check failed for {tradingsymbol}: {e}")
        return None, False

# ---------- Calculate Nifty Option Strikes ----------
def calculate_nifty_options(kite, instrument_token):
    df = load_nifty_data(kite, instrument_token)

    A = df.head(2)["high"].max()
    B = df.head(2)["low"].min()

    AB = A * (1 + 0.0015)
    BB = B * (1 - 0.0015)

    PE_END = ceiling(AB, 50)
    PE_START = floor(B, 50)
    CE_END = floor(BB, 50)
    CE_START = ceiling(A, 50)

    print("\nNifty")
    print(f"High of previous 2 days\t\t{A}")
    print(f"Low of previous 2 days\t\t{B}\n")
    print(f"\tBUFFER\tHigh {mround(AB)}")
    print(f"\tBuffer Low {mround(BB)}\n")
    print("Next strike selection to the buffer\n")
    print(f"\tPut start strike\t{PE_START}")
    print(f"\tPut end strike\t{PE_END}")
    print(f"\tCall start strike\t{CE_START}")
    print(f"\tCall end strike\t{CE_END}\n")

    # Candidate strikes (limit to 10, from START to END)
    PE_strikes = list(range(PE_START, PE_END + 50, 50))[:10]
    CE_strikes = list(range(CE_START, CE_END + 50, 50))[:10]

    print("PE strike list:", PE_strikes)
    print("CE strike list:", CE_strikes)

    expiry = get_weekly_expiry(kite)
    if not expiry:
        return

    symbol_map = find_strikes_for_expiry(kite, expiry)

    eligible_pe = None
    eligible_ce = None

    # Loop PE strikes from START upwards
    for strike in PE_strikes:
        key = f"{strike}PE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            result, ok = check_strike_eligibility(kite, ts, token, strike)
            if result:
                print(result)
                if ok and not eligible_pe:
                    eligible_pe = (expiry, result)
                    break

    # Loop CE strikes from START upwards
    for strike in CE_strikes:
        key = f"{strike}CE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            result, ok = check_strike_eligibility(kite, ts, token, strike)
            if result:
                print(result)
                if ok and not eligible_ce:
                    eligible_ce = (expiry, result)
                    break

    # Telegram notification
    msg = "📊 Eligible NIFTY Strikes\n"
    if eligible_pe:
        msg += f"Expiry: {eligible_pe[0]}\n{eligible_pe[1]}\n"
    if eligible_ce:
        msg += f"Expiry: {eligible_ce[0]}\n{eligible_ce[1]}\n"
    if not eligible_pe and not eligible_ce:
        msg += f"❌ No eligible strikes found for Expiry: {expiry}"
    send_telegram_message(msg)

# ---------- Public entry point ----------
def start_nifty_options():
    kite = get_kite_instance()
    if not kite:
        send_telegram_message("❌ Kite login expired, please login again")
        return
    instrument_token = 256265
    calculate_nifty_options(kite, instrument_token)
