# schedule.py
from apscheduler.schedulers.blocking import BlockingScheduler
from main import main
from datetime import datetime
import pytz

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

# ====== Setup scheduler ======
scheduler = BlockingScheduler(timezone=IST)

# Schedule daily at 10:07 PM IST
scheduler.add_job(run_main, 'cron', hour=22, minute=7)

print("⏳ Scheduler started. Waiting for 8:15 PM IST daily...")

# Start the scheduler (this will keep the Repl running)
scheduler.start()