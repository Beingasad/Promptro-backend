import sqlite3
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

for path in [BASE_DIR / "promptro.db", BASE_DIR / "backend" / "promptro.db"]:
    print(f"\n--- Checking DB at {path} ---")
    if not path.exists():
        print("File does not exist")
        continue
    
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cur.fetchall()]
        print(f"Tables: {tables}")
        if "user_profiles" in tables:
            cur.execute("PRAGMA table_info(user_profiles)")
            cols = cur.fetchall()
            print("Columns in user_profiles:")
            for col in cols:
                print(f"  {col[1]} ({col[2]})")
            
            cur.execute("SELECT count(*) FROM user_profiles")
            count = cur.fetchone()[0]
            print(f"Number of profiles: {count}")
            if count > 0:
                cur.execute("SELECT * FROM user_profiles LIMIT 2")
                rows = cur.fetchall()
                print("First 2 rows:")
                for r in rows:
                    print(r)
    except Exception as e:
        print(f"Error checking table: {e}")
    finally:
        conn.close()
