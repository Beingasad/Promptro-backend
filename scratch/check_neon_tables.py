import psycopg2

NEON_URL = "postgresql://neondb_owner:npg_uOd34niXHloK@ep-patient-art-aqgw24bl.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

print("Connecting to Neon...")
try:
    conn = psycopg2.connect(NEON_URL)
    cur = conn.cursor()
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
        ORDER BY table_name;
    """)
    tables = cur.fetchall()
    print("\nExisting Tables in Production:")
    for t in tables:
        print(f"- {t[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print("Error:", e)
