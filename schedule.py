# schedule.py
from apscheduler.schedulers.blocking import BlockingScheduler
from main import main
from datetime import datetime
import pytz
from flask import Flask
from threading import Thread

# ====== Define timezone ======
IST = pytz.timezone('Asia/Kolkata')

# ====== Flask server to keep Repl awake ======
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running ✅"

def run_flask():
    app.run(host="0.0.0.0", port=3000)

# Run Flask in a separate thread
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

# Schedule daily at 8:30 AM IST
scheduler.add_job(run_main, 'cron', hour=22, minute=24)

print("⏳ Scheduler started. Waiting for 10:24 AM IST daily...")

# Start the scheduler (this will keep the Repl running)
scheduler.start()