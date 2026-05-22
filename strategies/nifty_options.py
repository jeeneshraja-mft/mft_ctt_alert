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
 
def floor_val(value, base=50):
    return int(math.floor(value / base) * base)
 
# ---------- Load Nifty historical data (index) ----------
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
    nifty_options = [i for i in instruments if i["name"] == "NIFTY" and i["instrument_type"] in ["CE", "PE"]]
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
 
    if current_expiry.weekday() == 1:   # Tuesday expiry
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
            "token":         inst["instrument_token"]
        }
    return symbol_map
 
# ---------- Strike Eligibility Check ----------
# threshold  = strike * 0.0085  (0.85% of strike)
# low2       = min of option's last 2 trading day lows
# Eligible   = OI >= 35000  AND  low2 > threshold
def check_strike_eligibility(kite, tradingsymbol, instrument_token, strike, threshold_oi=35000):
    today     = datetime.today().date()
    from_date = today - timedelta(days=5)
 
    try:
        data = kite.historical_data(instrument_token, from_date, today, "day")
        df   = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"]).dt.date
        df   = df[df["date"] < today].sort_values(by="date", ascending=False)
 
        if df.empty:
            print(f"  [SKIP] {tradingsymbol} — no historical data")
            return None
 
        low2      = df.head(2)["low"].min()
        threshold = strike * 0.0085
 
        quote = kite.quote([f"NFO:{tradingsymbol}"])
        oi    = quote[f"NFO:{tradingsymbol}"]["oi"]
 
        eligible = (oi >= threshold_oi) and (low2 > threshold)
 
        status = "✅ Eligible" if eligible else "❌ Not Eligible"
        print(f"{tradingsymbol} => {threshold:.2f} (0.85%) => {low2} (2d low) => {oi} (OI) => {status}")
 
        return {
            "eligible":      eligible,
            "tradingsymbol": tradingsymbol,
            "threshold":     threshold,
            "low2":          low2,
            "oi":            oi
        }
 
    except Exception as e:
        print(f"  [ERROR] Eligibility check failed for {tradingsymbol}: {e}")
        return None
 
# ---------- Calculate Nifty Option Strikes ----------
def calculate_nifty_options(kite, instrument_token):
    df = load_nifty_data(kite, instrument_token)
 
    A = df.head(2)["high"].max()   # 2-day high of Nifty index
    B = df.head(2)["low"].min()    # 2-day low  of Nifty index
 
    # 0.15% buffer
    AB = A * (1 + 0.0015)   # buffer high
    BB = B * (1 - 0.0015)   # buffer low
 
    # Strike anchors — matching Excel:
    #
    #   PE_START = ceiling(A, 50)   → nearest strike ABOVE 2d high  e.g. 23450
    #   PE_END   = ceiling(AB, 50)  → nearest strike ABOVE buffer high  e.g. 23900
    #   Scan PE : PE_START → PE_END  (low to high, step +50)
    #
    #   CE_START = floor_val(B, 50)   → nearest strike BELOW 2d low   e.g. 23800
    #   CE_END   = floor_val(BB, 50)  → nearest strike BELOW buffer low  e.g. 23350
    #   Scan CE : CE_START → CE_END  (high to low, step -50)
 
    PE_START = ceiling(A, 50)       # above 2d high  → e.g. 23450
    PE_END   = ceiling(AB, 50)      # above buffer high → e.g. 23900
 
    CE_START = floor_val(B, 50)     # below 2d low   → e.g. 23800
    CE_END   = floor_val(BB, 50)    # below buffer low → e.g. 23350
 
    print("\n=== NIFTY STRIKE CALCULATION ===")
    print(f"2-Day High (A)        : {A}")
    print(f"2-Day Low  (B)        : {B}")
    print(f"Buffer High (AB)      : {mround(AB)}")
    print(f"Buffer Low  (BB)      : {mround(BB)}")
    print(f"\nPut  Sell Start Strike : {PE_START}")
    print(f"Put  Sell End Strike   : {PE_END}")
    print(f"Call Sell Start Strike : {CE_START}")
    print(f"Call Sell End Strike   : {CE_END}")
 
    # PE: ceiling(A) → ceiling(AB), step +50  (low to high)
    PE_strikes = list(range(PE_START, PE_END + 50,  50))[:10]
 
    # CE: floor(B) → floor(BB), step -50  (high to low)
    CE_strikes = list(range(CE_START, CE_END - 50, -50))[:10]
 
    print(f"\nPE strike list : {PE_strikes}")
    print(f"CE strike list : {CE_strikes}")
 
    expiry = get_weekly_expiry(kite)
    if not expiry:
        return
 
    symbol_map = find_strikes_for_expiry(kite, expiry)
 
    eligible_pe = None
    eligible_ce = None
 
    # -------- PE loop — break on FIRST eligible --------
    print("\n--- PE Strike Eligibility ---")
    for strike in PE_strikes:
        key = f"{strike}PE"
        if key not in symbol_map:
            print(f"  [SKIP] {key} not found in symbol map")
            continue
        ts    = symbol_map[key]["tradingsymbol"]
        token = symbol_map[key]["token"]
        result = check_strike_eligibility(kite, ts, token, strike)
        if result and result["eligible"]:
            eligible_pe = result
            print(f"  → First eligible PE: {ts}  (stopping scan)")
            break
 
    # -------- CE loop — break on FIRST eligible --------
    print("\n--- CE Strike Eligibility ---")
    for strike in CE_strikes:
        key = f"{strike}CE"
        if key not in symbol_map:
            print(f"  [SKIP] {key} not found in symbol map")
            continue
        ts    = symbol_map[key]["tradingsymbol"]
        token = symbol_map[key]["token"]
        result = check_strike_eligibility(kite, ts, token, strike)
        if result and result["eligible"]:
            eligible_ce = result
            print(f"  → First eligible CE: {ts}  (stopping scan)")
            break
 
    # -------- Telegram notification --------
    print("\n--- Telegram Notification ---")
 
    if eligible_pe or eligible_ce:
        lines = [
            "📊 *NIFTY Eligible Strikes*",
            f"📅 Expiry: {expiry}",
            ""
        ]
        if eligible_pe:
            lines += [
                "🟢 *PUT (PE) — First Eligible*",
                f"  Symbol    : `{eligible_pe['tradingsymbol']}`",
                f"  2d Low    : {eligible_pe['low2']}",
                f"  Threshold : {eligible_pe['threshold']:.2f}  (0.85% of strike)",
                f"  OI        : {eligible_pe['oi']:,}",
                ""
            ]
        if eligible_ce:
            lines += [
                "🔴 *CALL (CE) — First Eligible*",
                f"  Symbol    : `{eligible_ce['tradingsymbol']}`",
                f"  2d Low    : {eligible_ce['low2']}",
                f"  Threshold : {eligible_ce['threshold']:.2f}  (0.85% of strike)",
                f"  OI        : {eligible_ce['oi']:,}",
                ""
            ]
        msg = "\n".join(lines)
        send_telegram_message(msg)
        print("✅ Telegram alert sent with eligible strikes.")
    else:
        msg = f"⚠️ No eligible NIFTY strikes found.\nExpiry: {expiry}"
        send_telegram_message(msg)
        print("⚠️ No eligible strikes found — alert sent.")
 
# ---------- Public entry point ----------
def start_nifty_options():
    kite = get_kite_instance()
    if not kite:
        send_telegram_message("❌ Kite login expired, please login again")
        return
 
    instrument_token = 256265  # Nifty 50 index token
    calculate_nifty_options(kite, instrument_token)