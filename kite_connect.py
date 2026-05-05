from kiteconnect import KiteConnect
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

from config import API_KEY, API_SECRET, PORT
from db_connect import save_token, load_token, is_token_valid

# ---- Local server for 2FA ----
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

def run_login_flow(kite):
    httpd = HTTPServer(('127.0.0.1', PORT), RequestHandler)
    print(f"🌐 Starting local server on http://127.0.0.1:{PORT}/")
    login_url = kite.login_url()
    print("🔗 Opening Kite login URL in browser...")
    webbrowser.open(login_url)
    print("⏳ Waiting for you to login and complete 2FA...")
    httpd.handle_request()
    return httpd.request_token

def get_kite_instance():
    kite = KiteConnect(api_key=API_KEY)
    access_token, expiry = load_token()
    
    if access_token and is_token_valid(expiry):
        kite.set_access_token(access_token)
        print("✅ Using saved Kite access token from DB")
        return kite

    # Else, run login flow
    request_token = run_login_flow(kite)
    data = kite.generate_session(request_token, api_secret=API_SECRET)
    access_token = data["access_token"]
    expiry = datetime.utcnow() + timedelta(hours=24)
    save_token(access_token, expiry)
    kite.set_access_token(access_token)
    print("✅ New Kite access token saved in DB")
    return kite