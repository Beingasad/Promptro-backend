import sys
import os
sys.path.append(os.path.abspath("."))
from app.database import SessionLocal
from app import models

db = SessionLocal()
try:
    print("Querying user profiles...")
    profiles = db.query(models.UserProfile).all()
    print(f"Success! Found {len(profiles)} profiles.")
    for p in profiles:
        print(p.id, p.first_name, p.email)
except Exception as e:
    print("Error querying user profiles:")
    print(e)
finally:
    db.close()
