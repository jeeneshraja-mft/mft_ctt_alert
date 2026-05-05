from http.server import HTTPServer, BaseHTTPRequestHandler
import webbrowser
from urllib.parse import urlparse, parse_qs
from kiteconnect import KiteConnect
from datetime import date
import pandas as pd
import requests  # for Telegram notifications
import psycopg2

# ====== CONFIG ======
API_KEY = "hqszgobglsa0drch"
API_SECRET = "8xnttgisqub0vbb6j5xxdd7wkkczk66u"
PORT = 8000  # local server port
TRADINGSYMBOL = "GOLDTEN26MAYFUT"  # MCX GoldTen May 26 future

TELEGRAM_BOT_TOKEN = "8629379589:AAEeYlqkqWvDnvGh__TLyUlk4qSL2QP_wYo"
TELEGRAM_CHAT_ID = "1200810241"

# ====== SUPABASE CONFIG ======
SUPABASE_DSN = "postgresql://postgres.nqxtoltiqyeouqcndqfb:MFT_CTT_123$@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"


# ====== INIT KITE ======
kite = KiteConnect(api_key=API_KEY)

# ====== Local server handler ======
class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query = parse_qs(parsed_url.query)
        if "request_token" in query:
            self.server.request_token = query["request_token"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Login successful! You can close this window.</h2></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<html><body><h2>Error: request_token not found.</h2></body></html>")

# ====== Function to send Telegram message ======
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
        print("✅ Sent message to Telegram")
    except Exception as e:
        print("❌ Failed to send Telegram message:", e)

# ====== Function to insert high price into Supabase ======
def insert_price(tradingsymbol, high_price, alert_date):
    try:
        high_price = float(high_price)  # Convert numpy.int64 to float
        conn = psycopg2.connect(SUPABASE_DSN)
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS gold_prices (
                id SERIAL PRIMARY KEY,
                tradingsymbol TEXT NOT NULL,
                high_price NUMERIC NOT NULL,
                alert_date DATE NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)
        cur.execute("""
            INSERT INTO gold_prices (tradingsymbol, high_price, alert_date)
            VALUES (%s, %s, %s)
        """, (tradingsymbol, high_price, alert_date))
        conn.commit()
        cur.close()
        conn.close()
        print("✅ Price inserted into Supabase!")
    except Exception as e:
        print("❌ Supabase insert failed:", e)

# ====== Start local server ======
httpd = HTTPServer(('127.0.0.1', PORT), RequestHandler)
print(f"🌐 Starting local server on http://127.0.0.1:{PORT}/")

# ====== Open Kite login URL ======
login_url = kite.login_url()
print("🔗 Opening Kite login URL in browser...")
webbrowser.open(login_url)

# ====== Wait for login ======
print("⏳ Waiting for you to login and complete 2FA...")
httpd.handle_request()
request_token = httpd.request_token
print(f"✅ Request token received: {request_token}")

# ====== Generate access token and fetch high price ======
try:
    data = kite.generate_session(request_token, api_secret=API_SECRET)
    access_token = data["access_token"]
    kite.set_access_token(access_token)
    print("✅ Access token generated successfully!\n")

    # Step 1: Find GOLDTEN26MAY instrument token
    mcx_instruments = kite.instruments("MCX")
    instrument_token = None
    for inst in mcx_instruments:
        if inst['tradingsymbol'] == TRADINGSYMBOL:
            instrument_token = inst['instrument_token']
            break

    if not instrument_token:
        print(f"❌ Could not find instrument token for {TRADINGSYMBOL}")
        exit()

    print(f"✅ Found instrument token for {TRADINGSYMBOL}: {instrument_token}")

    # Step 2: Get today's high price
    today = date.today().strftime("%Y-%m-%d")
    data = kite.historical_data(
        instrument_token=instrument_token,
        from_date=today + " 09:15:00",
        to_date=today + " 15:30:00",
        interval="minute"
    )

    df = pd.DataFrame(data)

    if not df.empty:
        high_price = df['high'].max()
        message = f"📈 <b>{TRADINGSYMBOL}</b> - Today's High: {high_price}"
        print(message)

        # Insert into Supabase
        insert_price(TRADINGSYMBOL, high_price, today)

        # Send Telegram notification
        send_telegram_message(message)
    else:
        print("No data found for today.")

except Exception as e:
    print("\n❌ Error:", e)