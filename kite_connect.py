from kiteconnect import KiteConnect
from config import API_KEY
from db_connect import load_token, is_token_valid


def get_kite_instance():
    kite = KiteConnect(api_key=API_KEY)

    access_token, expiry = load_token()

    # ❌ SAFE MODE: no exceptions
    if not access_token or not is_token_valid(expiry):
        return None

    kite.set_access_token(access_token)
    return kite