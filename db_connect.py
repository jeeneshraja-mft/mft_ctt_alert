import psycopg2
from datetime import datetime
from config import SUPABASE_DSN
from datetime import datetime, timezone

# ---- Kite token functions ----
def save_token(access_token, expiry):
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kite_tokens (
            id SERIAL PRIMARY KEY,
            access_token TEXT NOT NULL,
            expiry TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
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
        ORDER BY id DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row:
        return row[0], row[1]
    return None, None

def is_token_valid(expiry):
    """
    Checks if the Kite access token is still valid.
    expiry: datetime object from DB (timezone-aware)
    """
    if not expiry:
        return False
    # Convert current UTC time to timezone-aware datetime
    now_utc = datetime.now(timezone.utc)
    return expiry > now_utc

# ---- Gold price storage ----
def insert_price(tradingsymbol, high_price, alert_date):
    high_price = float(high_price)  # convert numpy types to float
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS gold_prices (
            id SERIAL PRIMARY KEY,
            tradingsymbol TEXT NOT NULL,
            high_price NUMERIC NOT NULL,
            alert_date DATE NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now()
        );
    """)
    cur.execute("""
        INSERT INTO gold_prices (tradingsymbol, high_price, alert_date)
        VALUES (%s, %s, %s)
    """, (tradingsymbol, high_price, alert_date))
    conn.commit()
    cur.close()
    conn.close()