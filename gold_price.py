from kiteconnect import KiteConnect
from datetime import date
import pandas as pd

from config import TRADINGSYMBOL
from db_connect import insert_price

def fetch_today_high(kite: KiteConnect):
    mcx_instruments = kite.instruments("MCX")
    instrument_token = None
    for inst in mcx_instruments:
        if inst['tradingsymbol'] == TRADINGSYMBOL:
            instrument_token = inst['instrument_token']
            break

    if not instrument_token:
        raise Exception(f"❌ Could not find instrument token for {TRADINGSYMBOL}")

    today = date.today().strftime("%Y-%m-%d")
    data = kite.historical_data(
        instrument_token=instrument_token,
        from_date=today + " 09:15:00",
        to_date=today + " 15:30:00",
        interval="minute"
    )
    df = pd.DataFrame(data)

    if df.empty:
        print("No data found for today.")
        return None

    high_price = df['high'].max()
    insert_price(TRADINGSYMBOL, float(high_price), today)
    return high_price