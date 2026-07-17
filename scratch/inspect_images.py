import sys
import os
import json

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import database session
from app.database import SessionLocal
from app.models import Prompt

db = SessionLocal()
try:
    prompts = db.query(Prompt).all()
    print("PROMPTS IN DB:")
    for p in prompts:
        print(f"ID: {p.id} | Title: {p.title}")
        print(f"  image_url: {p.image_url}")
        print(f"  images:    {p.images}")
        print("-" * 50)
finally:
    db.close()
