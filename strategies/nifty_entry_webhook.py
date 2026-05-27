from kiteconnect import KiteTicker
from config.config import API_KEY
from database.db_connect import load_token

def start_tick_stream(instrument_tokens=None):
    """
    Start KiteTicker stream and print ticks to console.
    """
    access_token = load_token()
    if not access_token:
        print("❌ No access token found, please login again")
        return

    if instrument_tokens is None:
        instrument_tokens = [256265]  # Default: Nifty index token

    # ✅ Pass API_KEY and access_token directly
    kws = KiteTicker(API_KEY, access_token)

    def on_ticks(ws, ticks):
        for tick in ticks:
            print(f"📊 Tick: Token={tick['instrument_token']} LTP={tick['last_price']} OI={tick.get('oi')}")

    def on_connect(ws, response):
        print("✅ Tick WebSocket connected")
        ws.subscribe(instrument_tokens)
        ws.set_mode(ws.MODE_FULL, instrument_tokens)

    def on_close(ws, code, reason):
        print(f"❌ Tick WebSocket closed: {code} {reason}")

    kws.on_ticks = on_ticks
    kws.on_connect = on_connect
    kws.on_close = on_close

    kws.connect(threaded=True)
