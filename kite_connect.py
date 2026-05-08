from kiteconnect import KiteConnect
from config import API_KEY
from db_connect import load_token


def get_kite_instance():
    kite = KiteConnect(api_key=API_KEY)

    access_token, expiry = load_token()

    print("DEBUG access_token:", access_token)
    print("DEBUG expiry:", expiry)

    # ❌ DO NOT validate expiry anymore
    if not access_token:
        print("❌ No access token in DB")
        return None

    try:
        kite.set_access_token(access_token)

        # 🔥 TEST CALL (IMPORTANT)
        kite.profile()

        print("🟢 Kite authentication SUCCESS")
        return kite

    except Exception as e:
        print("❌ Kite auth failed:", e)
        return None