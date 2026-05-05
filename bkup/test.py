from kiteconnect import KiteConnect

API_KEY = "YOUR_API_KEY"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

kite = KiteConnect(api_key=API_KEY)
kite.set_access_token(ACCESS_TOKEN)

# Fetch all MCX instruments
mcx_instruments = kite.instruments("MCX")

print("🔎 Searching for GOLD contracts in May...\n")

for inst in mcx_instruments:
    if "GOLDTEN" in inst['tradingsymbol'] and "MAY" in inst['tradingsymbol']:
        print(inst['tradingsymbol'], inst['instrument_token'])