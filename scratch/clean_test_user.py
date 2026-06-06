import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

email = "testuser@example.com"
print(f"Cleaning database records for {email}...")

for table in ["user_profiles", "user_consents", "otp_verifications", "email_verification_tokens"]:
    cur.execute(f"DELETE FROM {table} WHERE email = ?", (email,))
    print(f"Deleted from {table}: {cur.rowcount} rows.")

conn.commit()
conn.close()
print("Database clean up complete!")
