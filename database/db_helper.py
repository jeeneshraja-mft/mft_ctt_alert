import psycopg2
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv

load_dotenv()
SUPABASE_DSN = os.getenv("SUPABASE_DSN")

IST = pytz.timezone("Asia/Kolkata")

def get_today_holiday():
    today = datetime.now(IST).date()
    weekday = today.weekday()  # Monday=0, Sunday=6

    # Weekend check
    if weekday in (5, 6):
        return {
            "date": today,
            "holiday_name": "Weekend",
            "nse_holiday": "Y",
            "mcx_morning": "Y",
            "mcx_evening": "Y"
        }

    try:
        conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
        cur = conn.cursor()
        cur.execute("""
            SELECT holiday_name, nse_holiday, mcx_morning, mcx_evening
            FROM trading_holidays
            WHERE date = %s
        """, (today,))
        result = cur.fetchone()
        cur.close()
        conn.close()

        if result:
            holiday_name, nse, mcx_morning, mcx_evening = result
            return {
                "date": today,
                "holiday_name": holiday_name,
                "nse_holiday": nse,
                "mcx_morning": mcx_morning,
                "mcx_evening": mcx_evening
            }
        else:
            return None
    except Exception as e:
        print(f"⚠️ Holiday check error: {e}")
        return None
