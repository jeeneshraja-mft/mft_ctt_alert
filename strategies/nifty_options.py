import pandas as pd
from datetime import datetime, timedelta
import math
from kiteconnect import KiteConnect
from config.config import API_KEY
from tele.telegram_alert import send_telegram_message
from database.db_connect import load_token, save_nifty_strategy


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

    print("\nNifty")
    print(f"High of previous 2 days\t\t{A}")
    print(f"Low of previous 2 days\t\t{B}\n")
    print(f"\tBUFFER\tHigh {mround(AB)}")
    print(f"\tBuffer Low {mround(BB)}\n")
    print("Next strike selection to the buffer\n")
    print(f"\tPut Sell Start Strike\t{PE_START}")
    print(f"\tPut Sell End Strike\t{PE_END}")
    print(f"\tCall Sell Start Strike\t{CE_START}")
    print(f"\tCall Sell End Strike\t{CE_END}\n")

    # ---------- Strike Lists ----------
    PE_strikes = list(range(PE_END, PE_START - 50, -50))
    CE_strikes = list(range(CE_END, CE_START + 50, 50))

    PE_strikes.reverse()
    CE_strikes.reverse()

    print("PE strike list:", PE_strikes)
    print("CE strike list:", CE_strikes)

    expiries = get_all_expiries(kite)
    if not expiries:
        return

    current_expiry = expiries[0]
    symbol_map = find_strikes_for_expiry(kite, current_expiry)

    eligible_pe = None
    eligible_pe_ts = None
    eligible_pe_token = None

    eligible_ce = None
    eligible_ce_ts = None
    eligible_ce_token = None

    # Loop through PE strikes
    for strike in PE_strikes:
        key = f"{strike}PE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            result = check_strike_eligibility(kite, ts, token, strike)
            if result:
                print(result)
                if "✅ Eligible" in result:
                    eligible_pe = f"{result} (Expiry {current_expiry})"
                    eligible_pe_ts = ts
                    eligible_pe_token = token
                    break

    # Loop through CE strikes
    for strike in CE_strikes:
        key = f"{strike}CE"
        if key in symbol_map:
            ts = symbol_map[key]["tradingsymbol"]
            token = symbol_map[key]["token"]
            result = check_strike_eligibility(kite, ts, token, strike)
            if result:
                print(result)
                if "✅ Eligible" in result:
                    eligible_ce = f"{result} (Expiry {current_expiry})"
                    eligible_ce_ts = ts
                    eligible_ce_token = token
                    break

    # If PE not found, check next expiry
    if not eligible_pe and len(expiries) > 1:
        next_expiry = expiries[1]
        print(f"\nNo eligible PE in {current_expiry}, checking next expiry: {next_expiry}")
        symbol_map = find_strikes_for_expiry(kite, next_expiry)
        for strike in PE_strikes:
            key = f"{strike}PE"
            if key in symbol_map:
                ts = symbol_map[key]["tradingsymbol"]
                token = symbol_map[key]["token"]
                result = check_strike_eligibility(kite, ts, token, strike)
                if result:
                    print(result)
                    if "✅ Eligible" in result:
                        eligible_pe = f"{result} (Expiry {next_expiry})"
                        eligible_pe_ts = ts
                        eligible_pe_token = token
                        break

    # If CE not found, check next expiry
    if not eligible_ce and len(expiries) > 1:
        next_expiry = expiries[1]
        print(f"\nNo eligible CE in {current_expiry}, checking next expiry: {next_expiry}")
        symbol_map = find_strikes_for_expiry(kite, next_expiry)
        for strike in CE_strikes:
            key = f"{strike}CE"
            if key in symbol_map:
                ts = symbol_map[key]["tradingsymbol"]
                token = symbol_map[key]["token"]
                result = check_strike_eligibility(kite, ts, token, strike)
                if result:
                    print(result)
                    if "✅ Eligible" in result:
                        eligible_ce = f"{result} (Expiry {next_expiry})"
                        eligible_ce_ts = ts
                        eligible_ce_token = token
                        break

    # Final Telegram message
    if eligible_pe or eligible_ce:

        # After confirming an eligible PE strike
        if eligible_pe and eligible_pe_ts and eligible_pe_token:
            pe_levels = calculate_entry_levels(kite, eligible_pe_ts, eligible_pe_token, option_type="PE")
            if pe_levels:
                send_telegram_message(
                    f"📉 Entry Levels for {eligible_pe_ts}\n"
                    f"2D High: {pe_levels['2D_HIGH']}\n"
                    f"2D Low: {pe_levels['2D_LOW']}\n"
                    f"Entry: {pe_levels['ENTRY']}\n"
                    f"Target: {pe_levels['TARGET']}\n"
                    f"Stoploss: {pe_levels['STOPLOSS']}"
                )
                # ✅ Save to DB
                save_nifty_strategy({
                    "strategy_date": datetime.today().date(),
                    "tradingsymbol": eligible_pe_ts,
                    "option_type": "PE",
                    **pe_levels
                })

        # After confirming an eligible CE strike
        if eligible_ce and eligible_ce_ts and eligible_ce_token:
            ce_levels = calculate_entry_levels(kite, eligible_ce_ts, eligible_ce_token, option_type="CE")
            if ce_levels:
                send_telegram_message(
                    f"📈 Entry Levels for {eligible_ce_ts}\n"
                    f"2D High: {ce_levels['2D_HIGH']}\n"
                    f"2D Low: {ce_levels['2D_LOW']}\n"
                    f"Entry: {ce_levels['ENTRY']}\n"
                    f"Target: {ce_levels['TARGET']}\n"
                    f"Stoploss: {ce_levels['STOPLOSS']}"
                )
                # ✅ Save to DB
                save_nifty_strategy({
                    "strategy_date": datetime.today().date(),
                    "tradingsymbol": eligible_ce_ts,
                    "option_type": "CE",
                    **ce_levels
                })


    else:
        send_telegram_message("❌ No eligible strikes found in current or next expiry")


# ---------- New Implementation: Entry, Target, Stoploss ----------
def calculate_entry_levels(kite, tradingsymbol, instrument_token, option_type="CE"):
    """
    Calculate entry, target, and stoploss for CE/PE strikes
    """

    today = datetime.today().date()
    from_date = today - timedelta(days=5)

    # Historical data (daily candles)
    data = kite.historical_data(instrument_token, from_date, today, "day")
    df = pd.DataFrame(data)
    df["date"] = pd.to_datetime(df["date"]).dt.date

    # ✅ Use same filter as eligibility check
    df = df[df["date"] < today].sort_values(by="date", ascending=False)

    if df.empty or len(df) < 2:
        send_telegram_message(f"⚠️ Not enough data for {tradingsymbol}")
        return None

    # ✅ Same definition of 2D high/low
    two_day_high = df.head(2)["high"].max()
    two_day_low  = df.head(2)["low"].min()

    # Excel-aligned calculations
    entry    = mround(two_day_low * 0.90, 0.05)
    target   = entry * 0.25
    slc1     = entry * 1.75
    slc2     = two_day_high * 1.10
    stoploss = min(slc1, slc2)

    result = {
    "Strike": tradingsymbol,
    "OptionType": option_type,
    "2D_HIGH": round(two_day_high),
    "2D_LOW": round(two_day_low),
    "ENTRY": round(entry),
    "TARGET": round(target),
    "STOPLOSS": round(stoploss)
    }

    return result



def start_nifty_options():
    kite = get_kite_instance()
    if not kite:
        send_telegram_message("❌ Kite login expired, please login again")
        return

    instrument_token = 256265  # Nifty index token
    calculate_nifty_options(kite, instrument_token)