import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Using sqlite by default for local dev to avoid setup issues.
# For production, change this to your hosted PostgreSQL URL (e.g. Supabase or Render DB)
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./promptro.db")

# check_same_thread is needed only for SQLite
connect_args = {"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args=connect_args
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
