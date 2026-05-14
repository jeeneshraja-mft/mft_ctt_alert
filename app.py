from flask import Flask, request
from kiteconnect import KiteConnect
from datetime import datetime
from datetime import timedelta

from config.config import API_KEY, API_SECRET
from database.db_connect import save_token
from tele.telegram_alert import send_telegram_message

app = Flask(__name__)

kite = KiteConnect(api_key=API_KEY)


@app.route("/")
def home():
    return "✅ Kite Token Server Running"


# STEP 1: Redirect URL for Zerodha login
@app.route("/login")
def login():
    return kite.login_url()


# STEP 2: Callback after Zerodha login
@app.route("/callback")
def callback():
    request_token = request.args.get("request_token")
    status = request.args.get("status")

    if status != "success":
        return "❌ Login failed"

    try:
        # Generate session
        data = kite.generate_session(request_token, api_secret=API_SECRET)
        access_token = data["access_token"]

        expiry = datetime.utcnow() + timedelta(hours=23)

        # Save to DB
        save_token(access_token, expiry)

        # Set token for this instance
        kite.set_access_token(access_token)

        # Telegram alert
        send_telegram_message("✅ Kite login successful. Token updated in DB.")

        return "✅ Login successful! You can close this page."

    except Exception as e:
        return f"❌ Error: {str(e)}"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)