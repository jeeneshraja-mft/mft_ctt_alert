# schedule.py
from apscheduler.schedulers.background import BackgroundScheduler
from main import main
from datetime import datetime
import pytz
import time

# ====== Define timezone ======
IST = pytz.timezone('Asia/Kolkata')

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
scheduler.add_job(run_main, 'cron', hour=22, minute=42)
scheduler.start()

print("⏳ Scheduler started. Waiting for 22:42 AM IST daily...")

# ====== Keep the script alive ======
try:
    while True:
        time.sleep(60)  # sleep 1 minute, loop forever
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
    print("Scheduler stopped.")