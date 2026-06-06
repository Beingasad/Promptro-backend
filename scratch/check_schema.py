import sqlite3

def check_db(path):
    print(f"--- DB: {path} ---")
    try:
        conn = sqlite3.connect(path)
        cur = conn.cursor()
        for table in ["user_profiles", "user_consents", "otp_verifications", "email_verification_tokens"]:
            cur.execute(f"SELECT sql FROM sqlite_master WHERE name='{table}'")
            row = cur.fetchone()
            if row:
                print(f"--- Table: {table} ---")
                print(row[0])
            else:
                print(f"Table {table} does not exist")
        conn.close()
    except Exception as e:
        print(f"Error checking {path}: {e}")

check_db("promptro.db")
