from kiteconnect import KiteConnect
from config import API_KEY
from db_connect import load_token, is_token_valid

def get_kite_instance():
    kite = KiteConnect(api_key=API_KEY)

    access_token, expiry = load_token()

    if not access_token:
        raise Exception("❌ No access token found in DB. Please login via Telegram link.")

    if expiry and not is_token_valid(expiry):
        raise Exception("❌ Access token expired. Please login again.")

    kite.set_access_token(access_token)

    print("✅ Kite instance ready using DB token")

    return kite


def get_login_url():
    kite = KiteConnect(api_key=API_KEY)
    return kite.login_url()