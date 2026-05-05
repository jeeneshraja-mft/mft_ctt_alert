# schedule.py
from datetime import datetime, timedelta
from time import sleep
from main import main  # Import your main.py's main function

def schedule_run(minutes_from_now=10):
    # Calculate the run time
    run_time = datetime.now() + timedelta(minutes=minutes_from_now)
    print(f"⏳ Script scheduled to run at: {run_time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Calculate delay in seconds
    delay = (run_time - datetime.now()).total_seconds()
    if delay > 0:
        sleep(delay)

    print(f"🚀 Running main script now: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    try:
        main()
        print("✅ Main script executed successfully!")
    except Exception as e:
        print("❌ Error during main script execution:", e)

if __name__ == "__main__":
    schedule_run(1)  # Schedule 10 minutes from now