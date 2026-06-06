import sys
import os
sys.path.append(os.path.abspath("."))
from app.database import SessionLocal
from app import models

db = SessionLocal()
try:
    print("Querying EmailVerificationToken...")
    tokens = db.query(models.EmailVerificationToken).all()
    print(f"Success! Found {len(tokens)} tokens.")
except Exception as e:
    print("Error querying EmailVerificationToken:")
    print(e)
finally:
    db.close()
