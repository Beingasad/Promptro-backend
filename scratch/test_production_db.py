import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app import models

NEON_URL = "postgresql://neondb_owner:npg_uOd34niXHloK@ep-patient-art-aqgw24bl.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

print("Connecting to Neon...")
engine = create_engine(NEON_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

try:
    print("Querying existing user profiles...")
    profiles = db.query(models.UserProfile).limit(5).all()
    print(f"Found {len(profiles)} profiles.")
    
    print("\nAttempting to insert a test OTPVerification record...")
    test_otp = models.OTPVerification(
        email="testsignup123@gmail.com",
        otp_code="123456",
        expires_at=datetime.utcnow() + timedelta(minutes=5)
    )
    db.add(test_otp)
    db.commit()
    print("Successfully inserted test OTP record!")
    
    # Clean up
    print("Cleaning up test record...")
    db.delete(test_otp)
    db.commit()
    print("Cleanup successful!")
    
except Exception as e:
    print("\nDATABASE ERROR:")
    import traceback
    traceback.print_exc()
finally:
    db.close()
