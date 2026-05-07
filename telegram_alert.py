import requests
import time
from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


# =========================================
# 📤 SEND TELEGRAM MESSAGE
# =========================================
def send_telegram_message(message, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }

    try:
        requests.post(url, data=payload)
        print("✅ Sent message to Telegram")
    except Exception as e:
        print("❌ Failed to send Telegram message:", e)


# =========================================
# 📥 LISTEN FOR COMMANDS (POLLING)
# =========================================
def listen_for_commands(callback):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
    last_update_id = None

    print("🤖 Listening for Telegram commands...")

    while True:
        try:
            params = {
                "timeout": 10
            }

            if last_update_id:
                params["offset"] = last_update_id + 1

            response = requests.get(url, params=params)
            data = response.json()

            if not data.get("ok"):
                print("❌ Telegram API error:", data)
                time.sleep(5)
                continue

            for update in data.get("result", []):
                last_update_id = update["update_id"]

                if "message" in update:
                    message = update["message"]
                    text = message.get("text", "").strip()
                    chat_id = message["chat"]["id"]

                    print(f"📩 Received command: {text} (chat_id: {chat_id})")

                    # 👇 Send to main handler
                    callback(text, chat_id)

        except Exception as e:
            print("❌ Error in Telegram listener:", e)

        time.sleep(2)