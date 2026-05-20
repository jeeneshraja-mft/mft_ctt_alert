import os

from kiteconnect import KiteConnect

from database.db_connect import load_token
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()
API_KEY = os.getenv("KITE_API_KEY")
API_SECRET = os.getenv("KITE_API_SECRET")

# =========================================
# GET KITE INSTANCE
# =========================================

def get_kite_instance():
    access_token = load_token()

    if not access_token:
        print("❌ No access token found")
        return None

    try:
        kite = KiteConnect(api_key=API_KEY)
        kite.set_access_token(access_token)

        # Validate session
        kite.profile()

        print("✅ Kite session valid")

        return kite

    except Exception as e:
        print(f"❌ Invalid Kite session: {e}")
        return None


# =========================================
# GENERATE LOGIN URL
# =========================================

def generate_login_url():
    kite = KiteConnect(api_key=API_KEY)
    return kite.login_url()


# =========================================
# GENERATE ACCESS TOKEN
# =========================================

def generate_kite_session(request_token):
    kite = KiteConnect(api_key=API_KEY)

    data = kite.generate_session(
        request_token,
        api_secret=API_SECRET
    )

    return data["access_token"]