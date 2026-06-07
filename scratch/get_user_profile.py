import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

email = "testuser@example.com"
cur.execute("SELECT id, first_name, last_name, provider, terms_accepted, terms_accepted_at, email_verified, created_at FROM user_profiles WHERE email = ?", (email,))
row = cur.fetchone()

if row:
    print("User profile found in database:")
    print(f"ID: {row[0]}")
    print(f"Name: {row[1]} {row[2]}")
    print(f"Provider: {row[3]}")
    print(f"Terms Accepted: {row[4]}")
    print(f"Terms Accepted At: {row[5]}")
    print(f"Email Verified: {row[6]}")
    print(f"Created At: {row[7]}")
else:
    print(f"No profile found for email {email}.")

conn.close()
