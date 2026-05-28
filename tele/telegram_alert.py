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
        "parse_mode": "MarkdownV2"
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
    # Escape parentheses and hyphens for MarkdownV2
    holiday_name = holiday['holiday_name'].replace("(", "\\(").replace(")", "\\)").replace("-", "\\-")

    # NSE
    nse_status = "*Holiday*" if holiday['nse_holiday'] == 'Y' else "__Open__"
    # MCX Morning
    mcx_morning_status = "*Holiday*" if holiday['mcx_morning'] == 'Y' else "__Open__"
    # MCX Evening
    mcx_evening_status = "*Holiday*" if holiday['mcx_evening'] == 'Y' else "__Open__"

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚨 *URGENT TRADING HOLIDAY ALERT* 🚨\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📅 _Today ({holiday['date']}) is {holiday_name}_\n\n"
        f"🛑 NSE: {nse_status}\n"
        f"⚠️ MCX Morning: {mcx_morning_status}\n"
        f"⚠️ MCX Evening: {mcx_evening_status}\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )

    # IMPORTANT: set parse_mode to MarkdownV2
    send_telegram_message(msg, parse_mode="MarkdownV2")
    print("📨 Trading holiday notification sent to Telegram")