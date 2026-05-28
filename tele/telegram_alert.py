import os
import requests
import time
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("❌ TELEGRAM_BOT_TOKEN not set or invalid")
if not TELEGRAM_CHAT_ID:
    raise RuntimeError("❌ TELEGRAM_CHAT_ID not set or invalid")

def send_telegram_message(message: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }

    for attempt in range(3):  # retry up to 3 times
        try:
            resp = requests.post(url, data=payload, timeout=10)
            if resp.status_code == 200:
                return True
            else:
                print(f"Telegram error: {resp.status_code} {resp.text}")
        except Exception as e:
            print("Telegram error:", e)
            time.sleep(2)  # wait before retry

    return False

def notify_trading_holiday(holiday):
    # NSE
    nse_status = "*Holiday*" if holiday['nse_holiday'] == 'Y' else "_*Open*_"
    # MCX Morning
    mcx_morning_status = "*Holiday*" if holiday['mcx_morning'] == 'Y' else "_*Open*_"
    # MCX Evening
    mcx_evening_status = "*Holiday*" if holiday['mcx_evening'] == 'Y' else "_*Open*_"

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚨 *URGENT TRADING HOLIDAY ALERT* 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 _Today ({holiday['date']}) is {holiday['holiday_name']}_\n\n"
        f"🛑 NSE: {nse_status}\n"
        f"⚠️ MCX Morning: {mcx_morning_status}\n"
        f"⚠️ MCX Evening: {mcx_evening_status}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    send_telegram_message(msg)  # ensure parse_mode="Markdown" or "MarkdownV2"
    print("📨 Trading holiday notification sent to Telegram")