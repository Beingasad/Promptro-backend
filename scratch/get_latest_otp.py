import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"

conn = sqlite3.connect(db_path)
cur = conn.cursor()

cur.execute("SELECT email, otp_code, verified, created_at FROM otp_verifications ORDER BY created_at DESC LIMIT 1")
row = cur.fetchone()

if row:
    print(f"Latest OTP details:")
    print(f"Email: {row[0]}")
    print(f"OTP: {row[1]}")
    print(f"Verified: {row[2]}")
    print(f"Created At: {row[3]}")
else:
    print("No OTP records found in database.")

conn.close()
