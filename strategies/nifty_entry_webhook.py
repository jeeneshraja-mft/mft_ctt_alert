from kiteconnect import KiteTicker
from brokers.kite_connect import get_kite_instance

def start_tick_stream(instrument_tokens=None):
    """
    Start KiteTicker stream and print ticks to console.
    instrument_tokens: list of instrument tokens to subscribe (default Nifty index)
    """
    kite = get_kite_instance()
    if not kite:
        print("❌ Kite session invalid, cannot start tick stream")
        return

    if instrument_tokens is None:
        instrument_tokens = [256265]  # Default: Nifty index token

    kws = KiteTicker(kite._api_key, kite._access_token)

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
