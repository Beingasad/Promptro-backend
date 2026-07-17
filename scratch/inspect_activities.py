import sys
import os
sys.path.append(os.path.abspath("."))
from app.database import SessionLocal
from app import models

db = SessionLocal()
try:
    print("Querying user activities...")
    activities = db.query(models.UserActivity).all()
    print(f"Found {len(activities)} user activities:")
    for a in activities:
        print(f"User ID: {a.user_id}")
        print(f"Saved Prompts: {a.saved_prompts}")
        print(f"Liked Prompts: {a.liked_prompts}")
        print(f"Collections: {a.collections}")
        print("-" * 50)
except Exception as e:
    print("Error querying user activities:", e)
finally:
    db.close()
