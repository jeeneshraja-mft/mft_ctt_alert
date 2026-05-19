# ====== CONFIG ======
import os

API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

PORT = os.getenv("PORT", "8080")  # default to 8080 if not set
TRADINGSYMBOL = os.getenv("TRADINGSYMBOL")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ====== SUPABASE CONFIG ======
SUPABASE_DSN = os.getenv("SUPABASE_DSN")

# ====== Trading Symbols ======
SILVERMIC_TRADINGSYMBOL = os.getenv("SILVERMIC_TRADINGSYMBOL")

# Local server port (duplicate safeguard)
PORT = os.getenv("PORT", "8080")
