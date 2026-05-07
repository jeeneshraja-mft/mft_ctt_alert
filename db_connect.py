import psycopg2
from datetime import datetime, timezone
from config import SUPABASE_DSN


# =========================================
# 🔐 KITE TOKEN FUNCTIONS
# =========================================

def save_token(access_token, expiry):
    conn = None
    cur = None

    try:
        conn = psycopg2.connect(SUPABASE_DSN)
        cur = conn.cursor()

        # Create table if not exists
        cur.execute("""
            CREATE TABLE IF NOT EXISTS kite_tokens (
                id SERIAL PRIMARY KEY,
                access_token TEXT NOT NULL,
                expiry TIMESTAMPTZ NOT NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            );
        """)

        # Insert new token
        cur.execute("""
            INSERT INTO kite_tokens (access_token, expiry)
            VALUES (%s, %s)
        """, (access_token, expiry))

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Error saving token: {e}")
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================================
# 🔥 FIXED: LOAD LATEST TOKEN (IMPORTANT)
# =========================================

def load_token():
    conn = None
    cur = None

    try:
        conn = psycopg2.connect(SUPABASE_DSN)
        cur = conn.cursor()

        # 🔥 ALWAYS fetch latest token
        cur.execute("""
            SELECT access_token, expiry
            FROM kite_tokens
            ORDER BY created_at DESC
            LIMIT 1
        """)

        row = cur.fetchone()

        if not row:
            return None, None

        return row[0], row[1]

    except Exception as e:
        print(f"❌ Error loading token: {e}")
        return None, None

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# =========================================
# 📊 TOKEN VALIDATION
# =========================================

def is_token_valid(expiry):
    if not expiry:
        return False

    try:
        now_utc = datetime.now(timezone.utc)
        return expiry > now_utc
    except:
        return False


# =========================================
# 📊 STRATEGY STORAGE (GOLD + SILVER)
# =========================================

def insert_strategy_levels(data: dict):
    conn = None
    cur = None

    try:
        conn = psycopg2.connect(SUPABASE_DSN)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS strategy_levels (
                id SERIAL PRIMARY KEY,
                tradingsymbol TEXT NOT NULL,
                strategy_date DATE NOT NULL,

                a_last4_high NUMERIC,
                b_last4_low NUMERIC,
                c_last2_high NUMERIC,
                d_last2_low NUMERIC,

                buy_entry NUMERIC,
                buy_target1 NUMERIC,
                buy_target2 NUMERIC,
                buy_sl1 NUMERIC,
                buy_sl2 NUMERIC,

                sell_entry NUMERIC,
                sell_target1 NUMERIC,
                sell_target2 NUMERIC,
                sell_sl1 NUMERIC,
                sell_sl2 NUMERIC,

                created_at TIMESTAMPTZ DEFAULT now(),

                UNIQUE(tradingsymbol, strategy_date)
            );
        """)

        cur.execute("""
            INSERT INTO strategy_levels (
                tradingsymbol, strategy_date,
                a_last4_high, b_last4_low, c_last2_high, d_last2_low,
                buy_entry, buy_target1, buy_target2, buy_sl1, buy_sl2,
                sell_entry, sell_target1, sell_target2, sell_sl1, sell_sl2
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (tradingsymbol, strategy_date) DO NOTHING
        """, (
            data["tradingsymbol"],
            data["strategy_date"],

            float(data["a_last4_high"]),
            float(data["b_last4_low"]),
            float(data["c_last2_high"]),
            float(data["d_last2_low"]),

            float(data["buy_entry"]),
            float(data["buy_target"]),
            float(data["buy_target2"]),
            float(data["buy_sl1"]),
            float(data["buy_sl2"]),

            float(data["sell_entry"]),
            float(data["sell_target"]),
            float(data["sell_target2"]),
            float(data["sell_sl1"]),
            float(data["sell_sl2"])
        ))

        conn.commit()

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ DB Insert Error: {e}")
        raise

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()