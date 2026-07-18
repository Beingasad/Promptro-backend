import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import models and calculate_dynamic_score from app
from app.models import Prompt, Base
from app.main import calculate_dynamic_score

# Database setup
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./promptro.db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def run():
    db = SessionLocal()
    print("Starting recalculation of all prompt scores...")
    
    prompts = db.query(Prompt).all()
    count = 0
    
    for p in prompts:
        # If the base score is exactly 70 (the old default that caused the "Verified everywhere" bug),
        # we reset it to 60 (Standard) so that it doesn't artificially inflate untweaked prompts.
        if p.base_quality_score == 70:
            p.base_quality_score = 60
            
        # Recalculate using the fixed formula in main.py
        calculate_dynamic_score(p)
        count += 1
        
    db.commit()
    db.close()
    print(f"Successfully recalculated scores for {count} prompts!")

if __name__ == "__main__":
    run()
