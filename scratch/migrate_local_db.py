import sqlite3
import os
from pathlib import Path

# Resolve SQLite path relative to project structure (the root directory promptro.db)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"

print(f"Connecting to database at {db_path}...")
if not db_path.exists():
    print("Database file does not exist!")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Check if 'verified' column already exists in 'email_verification_tokens'
cur.execute("PRAGMA table_info(email_verification_tokens)")
columns = [col[1] for col in cur.fetchall()]

if "verified" not in columns:
    print("Adding 'verified' column to 'email_verification_tokens' table...")
    try:
        cur.execute("ALTER TABLE email_verification_tokens ADD COLUMN verified BOOLEAN DEFAULT 0")
        conn.commit()
        print("Column 'verified' added successfully!")
    except Exception as e:
        print(f"Error adding column: {e}")
        conn.rollback()
else:
    print("Column 'verified' already exists in 'email_verification_tokens' table.")

# Print schema of the table to confirm
cur.execute("SELECT sql FROM sqlite_master WHERE name='email_verification_tokens'")
print("Current table schema:")
print(cur.fetchone()[0])

conn.close()
