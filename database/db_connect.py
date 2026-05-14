import psycopg2
from config.config import SUPABASE_DSN

def save_token(access_token, expiry=None):
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS kite_tokens (
            id SERIAL PRIMARY KEY,
            access_token TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("INSERT INTO kite_tokens (access_token) VALUES (%s)", (access_token,))
    conn.commit()
    cur.close()
    conn.close()

def load_token():
    conn = psycopg2.connect(SUPABASE_DSN)
    cur = conn.cursor()
    cur.execute("SELECT access_token FROM kite_tokens ORDER BY created_at DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None
