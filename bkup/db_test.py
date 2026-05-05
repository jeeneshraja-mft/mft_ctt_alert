import psycopg2

# Session Pooler connection URL
dsn = "postgresql://postgres.nqxtoltiqyeouqcndqfb:MFT_CTT_123$@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres"

try:
    conn = psycopg2.connect(dsn)
    cur = conn.cursor()
    cur.execute("SELECT NOW();")
    print("✅ Connected via Session Pooler! Current time:", cur.fetchone()[0])
    cur.close()
    conn.close()
except Exception as e:
    print("❌ Connection failed:", e)