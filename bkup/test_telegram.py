import requests

TELEGRAM_TOKEN = "8629379589:AAEeYlqkqWvDnvGh__TLyUlk4qSL2QP_wYo"
CHAT_ID = "1200810241"

def send_message(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": msg})

send_message("✅ Telegram test successful from Python!")
print("Message sent")