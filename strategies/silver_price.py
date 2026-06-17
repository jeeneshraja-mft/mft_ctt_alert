from kiteconnect import KiteConnect
from datetime import datetime,date, timedelta
import pytz
import pandas as pd
from database.db_connect import save_silver_strategy
from strategies.gold_price import mround, IST, working_days_between

# ---------- Helper ----------
def mround(value, base=1):
    return round(value / base) * base

IST = pytz.timezone("Asia/Kolkata")

# ---------- Get Latest Contract ----------
def get_latest_silver_token(kite: KiteConnect):
    mcx_instruments = kite.instruments("MCX")
    today = datetime.now(IST).date()

    valid_contracts = []
    for inst in mcx_instruments:
        ts = inst["tradingsymbol"]
        if inst["segment"] == "MCX-FUT" and ts.startswith(("SILVERMIC", "SILVERM")):
            expiry = inst["expiry"]
            if expiry and expiry >= today:
                valid_contracts.append(inst)

    if not valid_contracts:
        raise Exception("❌ No active SILVERMIC/SILVERM contracts found")

    silvermic = [x for x in valid_contracts if x["tradingsymbol"].startswith("SILVERMIC")]
    contracts = silvermic if silvermic else valid_contracts
    contracts = sorted(contracts, key=lambda x: x["expiry"])

    selected = None
    for inst in contracts:
        working_days_left = working_days_between(today, inst["expiry"])
        if working_days_left > 10:
            selected = inst
            break

    if not selected:
        selected = contracts[0]

    print(f"✅ Using SILVER contract: {selected['tradingsymbol']} (Expiry: {selected['expiry']})")
    return selected["instrument_token"], selected["tradingsymbol"]

# ---------- Strategy Function ----------
def fetch_silver_strategy_levels(kite: KiteConnect):
    instrument_token, tradingsymbol = get_latest_silver_token(kite)

    to_date = datetime.now(IST).date()
    from_date = to_date - timedelta(days=10)

    data = kite.historical_data(
        instrument_token=instrument_token,
        from_date=from_date,
        to_date=to_date,
        interval="day"
    )

    df = pd.DataFrame(data)

    if df.empty:
        raise Exception("❌ No historical data found")

    df["date"] = pd.to_datetime(df["date"]).dt.date
    today = datetime.now(IST).date()
    df = df[df["date"] < today]

    if len(df) < 4:
        raise Exception("❌ Not enough historical candles")

    df = df.sort_values(by="date", ascending=False)

    # ---------- Last 4 Days ----------
    last4 = df.head(4)
    a = last4["high"].max()
    b = last4["low"].min()

    # ---------- Last 2 Days ----------
    last2 = df.head(2)
    c = last2["high"].max()
    d = last2["low"].min()

    # BUY (2%)
    buy_entry = mround(a * (1 + 0.0012), 1)
    buy_target = mround(buy_entry * (1 + 0.02), 1)

    buy_sl1 = mround(max(buy_entry * (1 - 0.02), d * (1 - 0.0012)), 1)
    buy_sl2 = mround(max(buy_entry * (1 - 0.02), b * (1 - 0.0012)), 1)

    buy_diff = buy_target - buy_entry
    buy_target2 = mround(buy_entry + (buy_diff * 3), 1)

    # SELL (2%)
    sell_entry = mround(b * (1 - 0.0012), 1)
    sell_target = mround(sell_entry * (1 - 0.02), 1)

    sell_sl1 = mround(min(sell_entry * (1 + 0.02), c * (1 + 0.0012)), 1)
    sell_sl2 = mround(min(sell_entry * (1 + 0.02), a * (1 + 0.0012)), 1)

    sell_diff = sell_entry - sell_target
    sell_target2 = mround(sell_entry - (sell_diff * 3), 1)

    return {
        "tradingsymbol": tradingsymbol,
        "strategy_date": datetime.now(IST).date(),

        "a_last4_high": a,
        "b_last4_low": b,
        "c_last2_high": c,
        "d_last2_low": d,

        "buy_entry": buy_entry,
        "buy_target": buy_target,
        "buy_target2": buy_target2,
        "buy_sl1": buy_sl1,
        "buy_sl2": buy_sl2,

        "sell_entry": sell_entry,
        "sell_target": sell_target,
        "sell_target2": sell_target2,
        "sell_sl1": sell_sl1,
        "sell_sl2": sell_sl2
    }

# ---------- MAIN ENTRY POINT ----------

def calculate_silver_strategy(kite):
    data = fetch_silver_strategy_levels(kite)
    changed = save_silver_strategy(data)
    if changed:
        print("📨 New silver strategy stored and will be alerted")
    else:
        print("📨 Silver strategy unchanged — only alert")
    return data
