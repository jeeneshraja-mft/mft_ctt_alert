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
            return None

        low2 = df.head(2)["low"].min()
        threshold = strike * 0.0085

        quote = kite.quote([f"NFO:{tradingsymbol}"])
        oi = quote[f"NFO:{tradingsymbol}"]["oi"]

        eligible = (oi >= threshold_oi) and (low2 > threshold)

        status = "✅ Eligible" if eligible else "❌ Not Eligible"
        return f"{tradingsymbol} => {threshold:.2f} (0.85%) => {low2} (2d low) => {oi} (OI) => {status}"

    except Exception as e:
        print(f"Eligibility check failed for {tradingsymbol}: {e}")
        return None

# ---------- Calculate Nifty Option Strikes ----------
def calculate_nifty_options(kite, instrument_token):
    df = load_nifty_data(kite, instrument_token)

    A = df.head(2)["high"].max()
    B = df.head(2)["low"].min()

    # Buffer calculations
    AB = A * (1 + 0.0015)
    BB = B * (1 - 0.0015)

    # ---------- Strike Anchors ----------
    PE_END   = ceiling(AB, 50)
    PE_START = PE_END - (50 * 9)

    CE_END   = floor(BB, 50)
    CE_START = CE_END + (50 * 9)

    PE_strikes = list(range(PE_END, PE_START - 50, -50))
    CE_strikes = list(range(CE_END, CE_START + 50, 50))
    PE_strikes.reverse()
    CE_strikes.reverse()

    expiries = get_all_expiries(kite)
    if not expiries:
        return

    current_expiry = expiries[0]
    symbol_map = find_strikes_for_expiry(kite, current_expiry)

    eligible_pe = None
    eligible_ce = None

    # Loop through PE strikes
    for strike in PE_strikes:
        key = f"{strike}PE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            result = check_strike_eligibility(kite, ts, token, strike)
            if result and "✅ Eligible" in result:
                eligible_pe = {
                    "msg": f"{result} (Expiry {current_expiry})",
                    "strike": strike,
                    "ts": ts,
                    "token": token
                }
                break

    # Loop through CE strikes
    for strike in CE_strikes:
        key = f"{strike}CE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            result = check_strike_eligibility(kite, ts, token, strike)
            if result and "✅ Eligible" in result:
                eligible_ce = {
                    "msg": f"{result} (Expiry {current_expiry})",
                    "strike": strike,
                    "ts": ts,
                    "token": token
                }
                break

    # Fallback to next expiry if needed
    if not eligible_pe and len(expiries) > 1:
        next_expiry = expiries[1]
        symbol_map = find_strikes_for_expiry(kite, next_expiry)
        for strike in PE_strikes:
            key = f"{strike}PE"
            if key in symbol_map:
                ts = symbol_map[key]["tradingsymbol"]
                token = symbol_map[key]["token"]
                result = check_strike_eligibility(kite, ts, token, strike)
                if result and "✅ Eligible" in result:
                    eligible_pe = {
                        "msg": f"{result} (Expiry {next_expiry})",
                        "strike": strike,
                        "ts": ts,
                        "token": token
                    }
                    break

    if not eligible_ce and len(expiries) > 1:
        next_expiry = expiries[1]
        symbol_map = find_strikes_for_expiry(kite, next_expiry)
        for strike in CE_strikes:
            key = f"{strike}CE"
            if key in symbol_map:
                ts = symbol_map[key]["tradingsymbol"]
                token = symbol_map[key]["token"]
                result = check_strike_eligibility(kite, ts, token, strike)
                if result and "✅ Eligible" in result:
                    eligible_ce = {
                        "msg": f"{result} (Expiry {next_expiry})",
                        "strike": strike,
                        "ts": ts,
                        "token": token
                    }
                    break

    # Final Telegram message
    if eligible_pe or eligible_ce:
        msg = "📊 Eligible NIFTY Strikes\n"

        if eligible_ce:
            msg += f"{eligible_ce}\n"
            ce_levels = calculate_strategy_levels_from_result(kite, eligible_ce, symbol_map, "CE")
            if ce_levels:
                print("CE Levels:", ce_levels)  # console log for debugging
                msg += f"➡️ CE Entry: {ce_levels['Entry']}, Target: {ce_levels['Target']}, Stoploss: {ce_levels['Stoploss']}\n"

        if eligible_pe:
            msg += f"{eligible_pe}\n"
            pe_levels = calculate_strategy_levels_from_result(kite, eligible_pe, symbol_map, "PE")
            if pe_levels:
                print("PE Levels:", pe_levels)  # console log for debugging
                msg += f"➡️ PE Entry: {pe_levels['Entry']}, Target: {pe_levels['Target']}, Stoploss: {pe_levels['Stoploss']}\n"

        send_telegram_message(msg)
    else:
        send_telegram_message("❌ No eligible strikes found in current or next expiry")

# ---------- Public entry point ----------
def start_nifty_options():
    kite = get_kite_instance()
    if not kite:
        send_telegram_message("❌ Kite login expired, please login again")
        return

    instrument_token = 256265  # Nifty index token
    calculate_nifty_options(kite, instrument_token)

# ---------- Strategy Calculation ----------
def calculate_strategy_levels_from_result(kite, eligible_result, symbol_map, option_type):
    """
    Calculate Entry, Target, and Stoploss levels for CE/PE based on last 2 days high/low.
    eligible_result: the string you already store (e.g. "NIFTY26MAY23800CE => ... ✅ Eligible")
    symbol_map: the expiry's symbol_map dict
    option_type: "CE" or "PE"
    """
    try:
        # Extract strike from the eligible_result string
        # Example: "NIFTY26MAY23800CE" -> 23800
        parts = eligible_result.split("NIFTY")
        if len(parts) < 2:
            return None
        suffix = parts[1]
        strike_str = suffix.split(option_type)[0]
        strike = int(''.join([c for c in strike_str if c.isdigit()]))

        key = f"{strike}{option_type}"
        if key not in symbol_map:
            return None

        ts = symbol_map[key]["tradingsymbol"]
        token = symbol_map[key]["token"]

        # Load last 2 days data
        today = datetime.today().date()
        from_date = today - timedelta(days=5)
        data = kite.historical_data(token, from_date, today, "day")
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df = df[df["date"] < today].sort_values(by="date", ascending=False)

        if df.empty:
            return None

        opt_high = df.head(2)["high"].max()
        opt_low = df.head(2)["low"].max()

        # Entry
        entry = round(opt_low * (1 - 0.10) / 0.05) * 0.05
        # Target
        target = entry * (1 - 0.75)
        # Stoploss candidates
        sla = entry * (1 + 0.75)
        slb = opt_high * (1 + 0.10)
        stoploss = min(sla, slb)

        return {
            "Option": f"{ts} ({option_type})",
            "High2d": opt_high,
            "Low2d": opt_low,
            "Entry": round(entry, 2),
            "Target": round(target, 2),
            "Stoploss": round(stoploss, 2)
        }

    except Exception as e:
        print(f"Strategy calculation failed: {e}")
        return None
