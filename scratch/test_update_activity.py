import sys
import os
sys.path.append(os.path.abspath("."))
from app.database import SessionLocal
from app import models

db = SessionLocal()
try:
    user_id = "LKzXuTzGvAcJ1nAyzKKNHtEXujU2"
    print(f"Updating activity for user {user_id}...")
    activity = db.query(models.UserActivity).filter(models.UserActivity.user_id == user_id).first()
    if activity:
        activity.collections = [{"id": "col-1", "name": "Test Board", "prompts": []}]
        db.commit()
        db.refresh(activity)
        print("Success! Updated collections in DB:", activity.collections)
    else:
        print("User activity record not found!")
except Exception as e:
    print("Error:", e)
finally:
    db.close()
