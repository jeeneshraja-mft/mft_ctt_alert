import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()
SUPABASE_DSN = os.getenv("SUPABASE_DSN")

def save_token(access_token, expiry=None):
    print("SUPABASE_DSN at runtime:", SUPABASE_DSN)
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kite_tokens (
            id SERIAL PRIMARY KEY,
            access_token TEXT NOT NULL,
            expiry TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    if expiry is None:
        from datetime import datetime, timedelta
        expiry = datetime.utcnow() + timedelta(hours=23)
    cur.execute("""
        INSERT INTO kite_tokens (access_token, expiry)
        VALUES (%s, %s)
    """, (access_token, expiry))
    conn.commit()
    cur.close()
    conn.close()

def load_token():
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()
    cur.execute("""
        SELECT access_token, expiry
        FROM kite_tokens
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row[0]
    return None

def save_gold_strategy(data):
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM gold_strategy
        WHERE strategy_date = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (data["strategy_date"],))
    row = cur.fetchone()
    if row:
        existing = {
            "buy_entry": row[3],
            "buy_target": row[4],
            "buy_target2": row[5],
            "buy_sl1": row[6],
            "buy_sl2": row[7],
            "sell_entry": row[8],
            "sell_target": row[9],
            "sell_target2": row[10],
            "sell_sl1": row[11],
            "sell_sl2": row[12],
        }
        if all(data[k] == existing[k] for k in existing):
            print("⚪ Gold strategy unchanged — not saving duplicate")
            cur.close()
            conn.close()
            return False
    cur.execute("""
        INSERT INTO gold_strategy (
            strategy_date, tradingsymbol,
            buy_entry, buy_target, buy_target2, buy_sl1, buy_sl2,
            sell_entry, sell_target, sell_target2, sell_sl1, sell_sl2
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["strategy_date"], data["tradingsymbol"],
        data["buy_entry"], data["buy_target"], data["buy_target2"],
        data["buy_sl1"], data["buy_sl2"],
        data["sell_entry"], data["sell_target"], data["sell_target2"],
        data["sell_sl1"], data["sell_sl2"]
    ))
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Gold strategy saved to DB")
    return True

def save_silver_strategy(data):
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()
    cur.execute("""
        SELECT *
        FROM silver_strategy
        WHERE strategy_date = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (data["strategy_date"],))
    row = cur.fetchone()
    if row:
        existing = {
            "buy_entry": row[3],
            "buy_target": row[4],
            "buy_target2": row[5],
            "buy_sl1": row[6],
            "buy_sl2": row[7],
            "sell_entry": row[8],
            "sell_target": row[9],
            "sell_target2": row[10],
            "sell_sl1": row[11],
            "sell_sl2": row[12],
        }
        if all(data[k] == existing[k] for k in existing):
            print("⚪ Silver strategy unchanged — not saving duplicate")
            cur.close()
            conn.close()
            return False
    cur.execute("""
        INSERT INTO silver_strategy (
            strategy_date, tradingsymbol,
            buy_entry, buy_target, buy_target2, buy_sl1, buy_sl2,
            sell_entry, sell_target, sell_target2, sell_sl1, sell_sl2
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["strategy_date"], data["tradingsymbol"],
        data["buy_entry"], data["buy_target"], data["buy_target2"],
        data["buy_sl1"], data["buy_sl2"],
        data["sell_entry"], data["sell_target"], data["sell_target2"],
        data["sell_sl1"], data["sell_sl2"]
    ))
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Silver strategy saved to DB")
    return True

# ---------- NEW: Save Nifty Strategy ----------
def save_nifty_strategy(data):
    conn = psycopg2.connect(dsn=SUPABASE_DSN, sslmode="require")
    cur = conn.cursor()

    # Ensure table exists with token column
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nifty_strategy (
            id SERIAL PRIMARY KEY,
            strategy_date DATE NOT NULL,
            tradingsymbol TEXT NOT NULL,
            token BIGINT,                  -- ✅ new column
            option_type TEXT NOT NULL,
            two_day_high NUMERIC,
            two_day_low NUMERIC,
            entry NUMERIC,
            target NUMERIC,
            stoploss NUMERIC,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 🔍 Check if record already exists for same date + symbol + option_type
    cur.execute("""
        SELECT two_day_high, two_day_low, entry, target, stoploss, token
        FROM nifty_strategy
        WHERE strategy_date = %s
          AND tradingsymbol = %s
          AND option_type = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (data["strategy_date"], data["tradingsymbol"], data["option_type"]))

    row = cur.fetchone()
    if row:
        existing = {
            "2D_HIGH": float(row[0]),
            "2D_LOW": float(row[1]),
            "ENTRY": float(row[2]),
            "TARGET": float(row[3]),
            "STOPLOSS": float(row[4]),
            "TOKEN": row[5],
        }
        # If identical, skip insert
        if all(round(data[k]) == round(existing[k]) for k in ["2D_HIGH","2D_LOW","ENTRY","TARGET","STOPLOSS"]) \
           and data.get("token") == existing["TOKEN"]:
            print(f"⚪ Nifty strategy unchanged for {data['tradingsymbol']} — not saving duplicate")
            cur.close()
            conn.close()
            return False

    # ✅ Insert new record with token
    cur.execute("""
        INSERT INTO nifty_strategy (
            strategy_date, tradingsymbol, token, option_type,
            two_day_high, two_day_low, entry, target, stoploss
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, (
        data["strategy_date"],
        data["tradingsymbol"],
        data.get("token"),   # ✅ include token
        data["option_type"],
        float(data["2D_HIGH"]),
        float(data["2D_LOW"]),
        float(data["ENTRY"]),
        float(data["TARGET"]),
        float(data["STOPLOSS"])
    ))

    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Nifty strategy saved for {data['tradingsymbol']}")
    return True
