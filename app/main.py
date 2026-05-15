from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import uuid
import cloudinary
import cloudinary.uploader
import os
from pathlib import Path

from app import models, schemas
from app.database import engine, get_db

models.Base.metadata.create_all(bind=engine)
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Seed database if empty
    db = next(get_db())
    if db.query(models.Prompt).count() == 0:
        import uuid
        mock_prompts = [
            models.Prompt(id=str(uuid.uuid4()), title="Cyberpunk Cityscape", category="Sci-Fi", model="Midjourney v6", image_url="https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?q=80&w=1000&auto=format&fit=crop", prompt_text="A highly detailed cyberpunk cityscape at night...", likes=1205, views=4500),
            models.Prompt(id=str(uuid.uuid4()), title="Ethereal Forest Spirit", category="Fantasy", model="DALL-E 3", image_url="https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=800&auto=format&fit=crop", prompt_text="Ethereal glowing spirit in a dark mystical forest...", likes=840, views=3200),
            models.Prompt(id=str(uuid.uuid4()), title="Minimalist Architecture", category="Architecture", model="SDXL", image_url="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=1200&auto=format&fit=crop", prompt_text="Clean minimalist concrete architecture...", likes=532, views=2100),
            models.Prompt(id=str(uuid.uuid4()), title="Neon Samurai", category="Anime", model="Niji Journey", image_url="https://images.unsplash.com/photo-1533613220915-609f661a6fe1?q=80&w=900&auto=format&fit=crop", prompt_text="A neon lit samurai standing in the rain...", likes=2100, views=8900),
        ]
        db.add_all(mock_prompts)
        db.commit()

    if db.query(models.Category).count() == 0:
        default_categories = [
            {"name": "Cinematic", "image_url": "https://images.unsplash.com/photo-1485846234645-a62644f84728?q=80&w=1000"},
            {"name": "Anime", "image_url": "https://images.unsplash.com/photo-1578632738980-28c3fbf061f0?q=80&w=1000"},
            {"name": "Fantasy", "image_url": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=1000"},
            {"name": "Sci-Fi", "image_url": "https://images.unsplash.com/photo-1446776811953-b23d57bd21aa?q=80&w=1000"},
            {"name": "Nature", "image_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?q=80&w=1000"},
            {"name": "Architecture", "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=1000"},
            {"name": "Luxury", "image_url": "https://images.unsplash.com/photo-1503376780353-7e6692767b70?q=80&w=1000"},
            {"name": "Thumbnails", "image_url": "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?q=80&w=1000"},
        ]
        for cat in default_categories:
            db.add(models.Category(name=cat["name"], image_url=cat["image_url"]))
        db.commit()
    db.close()
    yield

app = FastAPI(title="Promptro API", lifespan=lifespan)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Configure CORS
allow_origins = [
    "http://localhost:5173",
    "https://promptro-frontend.vercel.app",
    "https://promptro.in",
    "https://www.promptro.in"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure Cloudinary
# Prioritize individual keys, fallback to CLOUDINARY_URL
cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")

if cloudinary_cloud_name and cloudinary_api_key and cloudinary_api_secret:
    cloudinary.config(
        cloud_name=cloudinary_cloud_name,
        api_key=cloudinary_api_key,
        api_secret=cloudinary_api_secret,
        secure=True
    )
elif os.getenv("CLOUDINARY_URL"):
    cloudinary.config(secure=True)

async def resolve_image_url(image: UploadFile | None, fallback_url: str = ""):
    if not image or not image.filename:
        return fallback_url

    # Always prefer Cloudinary in production
    is_cloudinary_configured = (
        (os.getenv("CLOUDINARY_CLOUD_NAME") and os.getenv("CLOUDINARY_API_KEY")) or 
        os.getenv("CLOUDINARY_URL")
    )

    if is_cloudinary_configured:
        try:
            # Upload to Cloudinary
            result = cloudinary.uploader.upload(image.file)
            return result.get("secure_url", fallback_url)
        except Exception as e:
            print(f"Cloudinary upload error: {e}")
            # If in production, we should probably fail or use the fallback
            # but never save to local disk on Render if possible.

    # Fallback to local storage (only recommended for local dev)
    try:
        extension = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{extension}"
        upload_path = UPLOAD_DIR / filename
        upload_path.write_bytes(await image.read())
        
        # Use BACKEND_URL for absolute paths, fallback to localhost for dev
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip('/')
        return f"{backend_url}/uploads/{filename}"
    except Exception as e:
        print(f"Local upload error: {e}")
        return fallback_url

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Promptro API is running"}

@app.get("/api/prompts", response_model=list[schemas.PromptOut])
def get_prompts(skip: int = 0, limit: int = 20, category: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Prompt)
    if category and category != "All":
        query = query.filter(models.Prompt.category == category)
    prompts = query.order_by(models.Prompt.created_at.desc()).offset(skip).limit(limit).all()
    return prompts

@app.get("/api/prompts/{prompt_id}", response_model=schemas.PromptOut)
def get_prompt(prompt_id: str, db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    
    # Increment views
    prompt.views += 1
    db.commit()
    db.refresh(prompt)
    
    return prompt

@app.post("/api/prompts", response_model=schemas.PromptOut)
async def create_prompt(
    title: str = Form(...),
    prompt_text: str = Form(...),
    negative_prompt: str = Form(None),
    category: str = Form(...),
    model: str = Form(...),
    tags: str = Form(None),
    featured: str = Form("false"),
    trending: str = Form("false"),
    visibility: str = Form("Public"),
    aspectRatio: str = Form(None),
    image: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        is_featured = featured.lower() == "true"
        is_trending = trending.lower() == "true"
        print(f"Creating prompt: {title} ({category}), Featured: {is_featured}")
        image_url = await resolve_image_url(image, "https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?q=80&w=1000&auto=format&fit=crop")

        tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

        db_prompt = models.Prompt(
            id=str(uuid.uuid4()),
            title=title,
            prompt_text=prompt_text,
            negative_prompt=negative_prompt,
            category=category,
            model=model,
            tags=tag_list,
            image_url=image_url,
            aspect_ratio=aspectRatio,
            featured=is_featured,
            trending=is_trending,
            visibility=visibility
        )
        db.add(db_prompt)
        db.commit()
        db.refresh(db_prompt)
        return db_prompt
    except Exception as e:
        print(f"Error creating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.put("/api/prompts/{prompt_id}", response_model=schemas.PromptOut)
async def update_prompt(
    prompt_id: str,
    title: str = Form(None),
    prompt_text: str = Form(None),
    negative_prompt: str = Form(None),
    category: str = Form(None),
    model: str = Form(None),
    tags: str = Form(None),
    featured: str = Form(None),
    trending: str = Form(None),
    visibility: str = Form(None),
    aspectRatio: str = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    try:
        prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
        if not prompt:
            raise HTTPException(status_code=404, detail="Prompt not found")

        if title is not None: prompt.title = title
        if prompt_text is not None: prompt.prompt_text = prompt_text
        if negative_prompt is not None: prompt.negative_prompt = negative_prompt
        if category is not None: prompt.category = category
        if model is not None: prompt.model = model
        if tags is not None:
            prompt.tags = [tag.strip() for tag in tags.split(",")]
        if featured is not None:
            prompt.featured = featured.lower() == "true"
        if trending is not None:
            prompt.trending = trending.lower() == "true"
        if visibility is not None:
            prompt.visibility = visibility
        if aspectRatio is not None:
            prompt.aspect_ratio = aspectRatio
        
        if image:
            prompt.image_url = await resolve_image_url(image, prompt.image_url)

        db.commit()
        db.refresh(prompt)
        return prompt
    except Exception as e:
        print(f"Error updating prompt: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@app.post("/api/prompts/{prompt_id}/like", response_model=schemas.PromptOut)
def like_prompt(prompt_id: str, liked: bool = Form(...), db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    if liked:
        prompt.likes += 1
    else:
        prompt.likes = max(0, prompt.likes - 1)

    db.commit()
    db.refresh(prompt)
    return prompt

@app.delete("/api/prompts/{prompt_id}")
def delete_prompt(prompt_id: str, db: Session = Depends(get_db)):
    prompt = db.query(models.Prompt).filter(models.Prompt.id == prompt_id).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    db.delete(prompt)
    db.commit()
    return {"status": "deleted", "id": prompt_id}

@app.get("/api/categories", response_model=list[schemas.CategoryOut])
def get_categories(db: Session = Depends(get_db)):
    return db.query(models.Category).order_by(models.Category.name).all()

@app.post("/api/categories", response_model=schemas.CategoryOut)
async def create_category(
    name: str = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    try:
        image_url = await resolve_image_url(image) if image else None
        db_category = models.Category(name=name, image_url=image_url)
        db.add(db_category)
        db.commit()
        db.refresh(db_category)
        return db_category
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail="Category already exists or invalid data")

@app.put("/api/categories/{category_id}", response_model=schemas.CategoryOut)
async def update_category(
    category_id: int,
    name: str = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    category.name = name
    if image:
        category.image_url = await resolve_image_url(image)
    
    db.commit()
    db.refresh(category)
    return category

@app.delete("/api/categories/{category_id}")
def delete_category(category_id: int, db: Session = Depends(get_db)):
    category = db.query(models.Category).filter(models.Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    db.delete(category)
    db.commit()
    return {"status": "deleted", "id": category_id}

@app.get("/api/feedback", response_model=list[schemas.FeedbackOut])
def get_feedbacks(db: Session = Depends(get_db)):
    return db.query(models.Feedback).order_by(models.Feedback.created_at.desc()).all()

@app.post("/api/feedback", response_model=schemas.FeedbackOut)
def create_feedback(feedback: schemas.FeedbackCreate, db: Session = Depends(get_db)):
    db_feedback = models.Feedback(
        user=feedback.user,
        email=feedback.email,
        subject=feedback.subject,
        message=feedback.message
    )
    db.add(db_feedback)
    db.commit()
    db.refresh(db_feedback)
    return db_feedback

@app.delete("/api/feedback/{feedback_id}")
def delete_feedback(feedback_id: int, db: Session = Depends(get_db)):
    feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    db.delete(feedback)
    db.commit()
    return {"status": "deleted", "id": feedback_id}

# --- BANNERS ---
@app.get("/api/banners", response_model=list[schemas.BannerOut])
def get_banners(active_only: bool = False, db: Session = Depends(get_db)):
    query = db.query(models.Banner)
    if active_only:
        query = query.filter(models.Banner.is_active == True)
    return query.order_by(models.Banner.created_at.desc()).all()

@app.post("/api/banners", response_model=schemas.BannerOut)
async def create_banner(
    tag_text: str = Form(...),
    tag_icon: str = Form(None),
    title: str = Form(...),
    subtitle: str = Form(...),
    button_text: str = Form(...),
    button_link: str = Form(...),
    bg_gradient: str = Form(...),
    is_active: bool = Form(True),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    image_url = await resolve_image_url(image)
    
    db_banner = models.Banner(
        tag_text=tag_text,
        tag_icon=tag_icon,
        title=title,
        subtitle=subtitle,
        button_text=button_text,
        button_link=button_link,
        bg_gradient=bg_gradient,
        is_active=is_active,
        image_url=image_url
    )
    db.add(db_banner)
    db.commit()
    db.refresh(db_banner)
    return db_banner

@app.put("/api/banners/{banner_id}", response_model=schemas.BannerOut)
async def update_banner(
    banner_id: int,
    tag_text: str = Form(None),
    tag_icon: str = Form(None),
    title: str = Form(None),
    subtitle: str = Form(None),
    button_text: str = Form(None),
    button_link: str = Form(None),
    bg_gradient: str = Form(None),
    is_active: bool = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    banner = db.query(models.Banner).filter(models.Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    if tag_text is not None: banner.tag_text = tag_text
    if tag_icon is not None: banner.tag_icon = tag_icon
    if title is not None: banner.title = title
    if subtitle is not None: banner.subtitle = subtitle
    if button_text is not None: banner.button_text = button_text
    if button_link is not None: banner.button_link = button_link
    if bg_gradient is not None: banner.bg_gradient = bg_gradient
    if is_active is not None: banner.is_active = is_active
    
    if image:
        banner.image_url = await resolve_image_url(image)
        
    db.commit()
    db.refresh(banner)
    return banner

@app.delete("/api/banners/{banner_id}")
def delete_banner(banner_id: int, db: Session = Depends(get_db)):
    banner = db.query(models.Banner).filter(models.Banner.id == banner_id).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner not found")
    
    db.delete(banner)
    db.commit()
    return {"status": "deleted", "id": banner_id}
