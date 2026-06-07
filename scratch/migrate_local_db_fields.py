import sys
import os
import sqlite3
from pathlib import Path
from sqlalchemy import create_engine

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app import models

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_paths = [
    BASE_DIR / "promptro.db",
    BASE_DIR / "backend" / "promptro.db"
]

print("=======================================================")
# We will check and migrate each database
for path in db_paths:
    print(f"\nChecking database at: {path}")
    if not path.exists():
        print("Database file does not exist, skipping.")
        continue

    conn = sqlite3.connect(path)
    # Enable dict factory to easily map columns by name
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        # Check table columns in user_profiles
        cur.execute("PRAGMA table_info(user_profiles)")
        columns = [col['name'] for col in cur.fetchall()]
        
        if not columns:
            print("Table 'user_profiles' does not exist in this database. Running Base.metadata.create_all...")
            conn.close()
            # Just create it
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            Base.metadata.create_all(bind=engine)
            print("Created successfully!")
            continue

        if "firstName" in columns:
            print("Found camelCase columns (e.g. 'firstName'). Migrating to snake_case...")
            
            # 1. Fetch all existing data
            cur.execute("SELECT * FROM user_profiles")
            rows = [dict(row) for row in cur.fetchall()]
            print(f"Fetched {len(rows)} user profiles for migration.")

            # 2. Drop the existing user_profiles table
            # (which drops indexes and constraints too)
            cur.execute("DROP TABLE user_profiles")
            conn.commit()
            conn.close()

            # 3. Use SQLAlchemy to create the table with the new snake_case schema
            print("Recreating 'user_profiles' table with new snake_case schema using SQLAlchemy...")
            engine = create_engine(f"sqlite:///{path.as_posix()}")
            Base.metadata.create_all(bind=engine)

            # 4. Connect again via raw SQLite to restore the records with correct mapping
            conn = sqlite3.connect(path)
            cur = conn.cursor()
            
            for row in rows:
                # Map camelCase to snake_case
                mapped_row = {
                    "id": row.get("id"),
                    "firebase_uid": row.get("firebase_uid"),
                    "username": row.get("username"),
                    "first_name": row.get("firstName"),
                    "last_name": row.get("lastName"),
                    "gender": row.get("gender"),
                    "email": row.get("email"),
                    "provider": row.get("provider"),
                    "terms_accepted": row.get("termsAccepted"),
                    "terms_accepted_at": row.get("termsAcceptedAt"),
                    "email_verified": row.get("emailVerified"),
                    "created_at": row.get("createdAt")
                }
                
                columns_str = ", ".join(mapped_row.keys())
                placeholders = ", ".join(["?" for _ in mapped_row])
                values = list(mapped_row.values())
                
                cur.execute(
                    f"INSERT INTO user_profiles ({columns_str}) VALUES ({placeholders})",
                    values
                )
            conn.commit()
            print(f"Migration completed for {path}. {len(rows)} rows restored successfully!")

        else:
            print("Database is already in snake_case format. No migration needed.")

    except Exception as e:
        print(f"❌ Error during migration of {path}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            conn.close()
        except:
            pass

print("\n=======================================================")
print("  LOCAL DATABASE MIGRATION SCRIPT FINISHED")
print("=======================================================")
