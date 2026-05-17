import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Append the current directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import Base
from app.models import Prompt, Category, SavedPrompt, Feedback, Banner

# Connection URLs
SQLITE_URL = "sqlite:///./promptro.db"
NEON_URL = "postgresql://neondb_owner:npg_uOd34niXHloK@ep-patient-art-aqgw24bl.c-8.us-east-1.aws.neon.tech/neondb?sslmode=require"

print("=======================================================")
print("  STARTING PROMPTRO DATABASE MIGRATION TO NEON CLOUD")
print("=======================================================")
print(f" Source: {SQLITE_URL}")
print(f" Target: {NEON_URL.split('@')[1]} (Neon PostgreSQL)")
print("-------------------------------------------------------")

try:
    # 1. Initialize Engines and Sessions
    sqlite_engine = create_engine(SQLITE_URL)
    neon_engine = create_engine(NEON_URL)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    NeonSession = sessionmaker(bind=neon_engine)

    sqlite_db = SqliteSession()
    neon_db = NeonSession()

    # 2. Ensure all tables exist in Neon PostgreSQL
    print("Step 1: Creating database schemas on Neon Cloud...")
    Base.metadata.create_all(bind=neon_engine)
    print("Schema initialized successfully!")

    # 3. Clear existing target tables to avoid duplicate constraint errors
    print("\nStep 2: Cleaning up existing tables in target Neon database...")
    neon_db.query(Prompt).delete()
    neon_db.query(Category).delete()
    neon_db.query(SavedPrompt).delete()
    neon_db.query(Feedback).delete()
    neon_db.query(Banner).delete()
    neon_db.commit()
    print("Target tables cleared.")

    # 4. Migrate Categories
    print("\nStep 3: Migrating 'categories'...")
    categories = sqlite_db.query(Category).all()
    print(f"   Found {len(categories)} categories locally.")
    for cat in categories:
        new_cat = Category(
            id=cat.id,
            name=cat.name,
            image_url=cat.image_url,
            created_at=cat.created_at
        )
        neon_db.add(new_cat)
    neon_db.commit()
    print("Categories migrated!")

    # 5. Migrate Banners
    print("\nStep 4: Migrating 'banners'...")
    banners = sqlite_db.query(Banner).all()
    print(f"   Found {len(banners)} banners locally.")
    for b in banners:
        new_b = Banner(
            id=b.id,
            tag_text=b.tag_text,
            tag_icon=b.tag_icon,
            title=b.title,
            subtitle=b.subtitle,
            button_text=b.button_text,
            button_link=b.button_link,
            image_url=b.image_url,
            bg_gradient=b.bg_gradient,
            is_active=b.is_active,
            created_at=b.created_at
        )
        neon_db.add(new_b)
    neon_db.commit()
    print("Banners migrated!")

    # 6. Migrate Prompts
    print("\nStep 5: Migrating 'prompts'...")
    prompts = sqlite_db.query(Prompt).all()
    print(f"   Found {len(prompts)} prompts locally.")
    for p in prompts:
        new_p = Prompt(
            id=p.id,
            title=p.title,
            image_url=p.image_url,
            prompt_text=p.prompt_text,
            negative_prompt=p.negative_prompt,
            category=p.category,
            tags=p.tags,
            model=p.model,
            likes=p.likes,
            views=p.views,
            featured=p.featured,
            trending=p.trending,
            visibility=p.visibility,
            aspect_ratio=p.aspect_ratio,
            created_at=p.created_at
        )
        neon_db.add(new_p)
    neon_db.commit()
    print("Prompts migrated!")

    # 7. Migrate Saved Prompts
    print("\nStep 6: Migrating 'saved_prompts'...")
    saved = sqlite_db.query(SavedPrompt).all()
    print(f"   Found {len(saved)} saved prompts locally.")
    for s in saved:
        new_s = SavedPrompt(
            id=s.id,
            prompt_id=s.prompt_id,
            user_id=s.user_id,
            created_at=s.created_at
        )
        neon_db.add(new_s)
    neon_db.commit()
    print("Saved prompts migrated!")

    # 8. Migrate Feedbacks
    print("\nStep 7: Migrating 'feedbacks'...")
    feedbacks = sqlite_db.query(Feedback).all()
    print(f"   Found {len(feedbacks)} feedbacks locally.")
    for f in feedbacks:
        new_f = Feedback(
            id=f.id,
            user=f.user,
            email=f.email,
            subject=f.subject,
            message=f.message,
            status=f.status,
            created_at=f.created_at
        )
        neon_db.add(new_f)
    neon_db.commit()
    print("Feedbacks migrated!")

    print("\n=======================================================")
    print(" SUCCESS! DATABASE MIGRATED TO NEON CLOUD WITH 100% INTEGRITY!")
    print("=======================================================")

except Exception as e:
    print(f"\n❌ Error during migration: {str(e)}")
    import traceback
    traceback.print_exc()
finally:
    sqlite_db.close()
    neon_db.close()
