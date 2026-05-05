# schedule.py
from apscheduler.schedulers.background import BackgroundScheduler
from main import main
from datetime import datetime
import pytz
from flask import Flask
from threading import Thread
import os
import time

# ====== Define timezone ======
IST = pytz.timezone('Asia/Kolkata')

# ====== Flask server to keep Repl awake ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

def run_flask():
    # Use Replit PORT environment variable
    port = int(os.environ.get("PORT", 3000))
    app.run(host="0.0.0.0", port=port)

# Start Flask in a separate thread
Thread(target=run_flask, daemon=True).start()

# ====== Function to run main.py ======
def run_main():
    print(f"🚀 Running main script at {datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')} IST")
    try:
        main()
        print("✅ Main script executed successfully!")
    except Exception as e:
        print("❌ Error during main script execution:", e)

# ====== Setup Background Scheduler ======
scheduler = BackgroundScheduler(timezone=IST)
scheduler.add_job(run_main, 'cron', hour=8, minute=30)
scheduler.start()

print("⏳ Scheduler started. Waiting for 8:30 AM IST daily...")

# ====== Keep the script alive ======
try:
    while True:
        time.sleep(60)  # sleep 1 minute, loop forever
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
    print("Scheduler stopped.")