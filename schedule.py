# schedule.py
from apscheduler.schedulers.blocking import BlockingScheduler
from main import main
from datetime import datetime
import pytz
from flask import Flask
from threading import Thread
import os  # Needed for Replit PORT

# ====== Define timezone ======
IST = pytz.timezone('Asia/Kolkata')

# ====== Flask server to keep Repl awake ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

def run_flask():
    # Use Replit's PORT environment variable; fallback to 3000
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)

# Start Flask in a separate thread
Thread(target=run_flask).start()

# ====== Function to run main.py ======
def run_main():
    print(f"🚀 Running main script at {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
    try:
        main()
        print("✅ Main script executed successfully!")
    except Exception as e:
        print("❌ Error during main script execution:", e)

# ====== Setup scheduler ======
scheduler = BlockingScheduler(timezone=IST)

# Schedule daily at 22:30 AM IST
scheduler.add_job(run_main, 'cron', hour=22, minute=30)

print("⏳ Scheduler started. Waiting for 8:30 AM IST daily...")

# Start the scheduler (this will keep the Repl running)
scheduler.start()