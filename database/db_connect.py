import psycopg2
from config.config import SUPABASE_DSN

def save_token(access_token, expiry=None):
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()

    # Ensure table exists with expiry column
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kite_tokens (
            id SERIAL PRIMARY KEY,
            access_token TEXT NOT NULL,
            expiry TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    if expiry is None:
        # Default expiry ~23 hours from now if not provided
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
    conn = psycopg2.connect(SUPABASE_DSN)
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
        return row[0]  # access_token
    return None

def save_gold_strategy(data):
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()

    # Check if a record exists for today
    cur.execute("""
        SELECT *
        FROM gold_strategy
        WHERE strategy_date = %s
        ORDER BY created_at DESC
        LIMIT 1
    """, (data["strategy_date"],))

    row = cur.fetchone()

    if row:
        # Compare values with existing record
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

        # If identical, skip insert
        if all(data[k] == existing[k] for k in existing):
            print("⚪ Gold strategy unchanged — not saving duplicate")
            cur.close()
            conn.close()
            return False

    # Insert new record
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
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()

    # Check if a record exists for today
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

        # If identical, skip insert
        if all(data[k] == existing[k] for k in existing):
            print("⚪ Silver strategy unchanged — not saving duplicate")
            cur.close()
            conn.close()
            return False

    # Insert new record
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
