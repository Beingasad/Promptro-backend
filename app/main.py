from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import Response, PlainTextResponse
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
    try:
        from app.database import SessionLocal
        db_session = SessionLocal()
        write_static_seo_files(db_session)
        db_session.close()
    except Exception as e:
        print(f"Error generating static SEO files on startup: {e}")
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

def compress_image_to_500kb(image_bytes: bytes, filename: str) -> bytes:
    import io
    from PIL import Image
    
    # Target size is 500 KB (512,000 bytes)
    target_size_bytes = 500 * 1024
    
    # If already smaller, don't touch it
    if len(image_bytes) <= target_size_bytes:
        return image_bytes
        
    print(f"IMAGE_COMPRESSION: Original size: {len(image_bytes) / 1024:.2f} KB. Compressing to < 500 KB using high-fidelity WebP/JPEG...")
    
    try:
        img = Image.open(io.BytesIO(image_bytes))
    except Exception as e:
        print(f"IMAGE_COMPRESSION_ERROR: Could not open image: {e}")
        return image_bytes

    save_format = "WEBP"
    
    # Step 1: Save as WebP and dynamically adjust quality from 90 down to 60
    # WebP quality 60-90 is extremely high-fidelity and retains pristine sharp edges
    for q in [90, 85, 80, 75, 70, 65, 60]:
        output = io.BytesIO()
        img.save(output, format=save_format, quality=q, optimize=True)
        size = output.tell()
        if size <= target_size_bytes:
            print(f"IMAGE_COMPRESSION_SUCCESS: WebP (Quality: {q}, Size: {size / 1024:.2f} KB) with zero visual quality loss.")
            return output.getvalue()
            
    # Step 2: If quality 60 WebP is still over 500KB, it's a massive high-res image (e.g., 4000px+).
    # We will resize it in steps down to a maximum of 1600px width/height (which is perfect for retina screens and displays)
    # using high-quality LANCZOS resampling.
    max_dim = max(img.width, img.height)
    if max_dim > 1600:
        scale = 1600.0 / max_dim
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        try:
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except AttributeError:
            resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
            
        for q in [85, 80, 75, 70, 65, 60]:
            output = io.BytesIO()
            resized_img.save(output, format=save_format, quality=q, optimize=True)
            size = output.tell()
            if size <= target_size_bytes:
                print(f"IMAGE_COMPRESSION_SUCCESS: Resized to {new_width}x{new_height} WebP (Quality: {q}, Size: {size / 1024:.2f} KB)")
                return output.getvalue()
                
        # If still too large, let's keep the resized image as our working image
        img = resized_img

    # Step 3: Progressive downscaling down to 800px if still not under 500KB
    scale = 0.85
    while scale >= 0.3:
        new_width = int(img.width * scale)
        new_height = int(img.height * scale)
        if new_width < 800 or new_height < 800:
            break
            
        try:
            resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        except AttributeError:
            resized_img = img.resize((new_width, new_height), Image.ANTIALIAS)
            
        for q in [80, 70, 60, 50]:
            output = io.BytesIO()
            resized_img.save(output, format=save_format, quality=q, optimize=True)
            size = output.tell()
            if size <= target_size_bytes:
                print(f"IMAGE_COMPRESSION_SUCCESS: Downscaled to {new_width}x{new_height} WebP (Quality: {q}, Size: {size / 1024:.2f} KB)")
                return output.getvalue()
        scale -= 0.15

    # Step 4: Emergency Fallback - JPEG lossy compression
    print("IMAGE_COMPRESSION_FALLBACK: WebP failed to reach 500KB. Using JPEG...")
    work_img = img
    if work_img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", work_img.size, (255, 255, 255))
        background.paste(work_img, mask=work_img.split()[3])
        work_img = background
    elif work_img.mode != "RGB":
        work_img = work_img.convert("RGB")
        
    for q in [80, 70, 60, 50, 40, 30]:
        output = io.BytesIO()
        work_img.save(output, format="JPEG", quality=q, optimize=True)
        size = output.tell()
        if size <= target_size_bytes:
            print(f"IMAGE_COMPRESSION_SUCCESS: JPEG fallback (Quality: {q}, Size: {size / 1024:.2f} KB)")
            return output.getvalue()
            
    # Step 5: Emergency force fit
    print("IMAGE_COMPRESSION_WARNING: Forcing save at quality 30 JPEG.")
    output = io.BytesIO()
    work_img.save(output, format="JPEG", quality=30, optimize=True)
    return output.getvalue()

async def resolve_image_url(image: UploadFile | None, fallback_url: str = ""):
    if not image or not image.filename:
        return fallback_url

    # Read the content and compress to 500KB maximum
    try:
        original_content = await image.read()
        if not original_content:
            return fallback_url
        content = compress_image_to_500kb(original_content, image.filename)
    except Exception as e:
        print(f"IMAGE_COMPRESSION_FAILED: Error during image compression: {e}. Using original content.")
        # Fallback to original content
        content = original_content

    # Check Cloudinary configuration
    cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
    cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
    cloudinary_url = os.getenv("CLOUDINARY_URL")

    is_cloudinary_configured = False
    if cloudinary_cloud_name and cloudinary_api_key and cloudinary_api_secret:
        is_cloudinary_configured = True
    elif cloudinary_url:
        is_cloudinary_configured = True

    # In production (Render), we MUST use Cloudinary.
    is_production = os.getenv("RENDER") is not None

    if is_production and not is_cloudinary_configured:
        raise HTTPException(
            status_code=500,
            detail="CRITICAL CONFIGURATION ERROR: Cloudinary is NOT configured in production environment! Image upload failed."
        )

    if is_cloudinary_configured:
        try:
            # Upload to Cloudinary with a specific folder
            result = cloudinary.uploader.upload(content, folder="promptro_prompts")
            url = result.get("secure_url")
            if url:
                # Force absolute HTTPS Cloudinary URL
                if not url.startswith("https://"):
                    url = url.replace("http://", "https://")
                
                # Print saved image_url after successful upload
                print(f"CLOUDINARY_UPLOAD_SUCCESS: Successfully uploaded prompt image to Cloudinary. URL: {url}")
                return url
            else:
                raise ValueError("Cloudinary upload succeeded but returned no secure_url")
        except Exception as e:
            # If Cloudinary upload fails, raise error instead of silently saving local image
            print(f"CLOUDINARY_UPLOAD_FAILED: Error during Cloudinary upload: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Production image upload to Cloudinary failed: {str(e)}"
            )
    else:
        print("WARNING: Cloudinary not configured. Using local storage (ephemeral).")

    # Local development fallback (strictly prohibited in production)
    try:
        extension = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{extension}"
        upload_path = UPLOAD_DIR / filename
        
        upload_path.write_bytes(content)
        
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip('/')
        if not backend_url.startswith('http') and backend_url:
             backend_url = f"https://{backend_url}"
             
        final_url = f"{backend_url}/uploads/{filename}"
        print(f"LOCAL_UPLOAD_SUCCESS: Local storage URL generated: {final_url}")
        return final_url
    except Exception as e:
        print(f"ERROR: Local upload failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Local image upload failed: {str(e)}"
        )

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Promptro API is running"}

@app.get("/api/prompts", response_model=list[schemas.PromptOut])
def get_prompts(skip: int = 0, limit: int = None, category: str = None, db: Session = Depends(get_db)):
    query = db.query(models.Prompt)
    if category and category != "All":
        query = query.filter(models.Prompt.category == category)
    
    query = query.order_by(models.Prompt.created_at.desc()).offset(skip)
    if limit is not None:
        query = query.limit(limit)
        
    prompts = query.all()
    return prompts

@app.get("/api/prompts/count")
def get_prompts_count(db: Session = Depends(get_db)):
    return {"count": db.query(models.Prompt).count()}

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
    image_url: str = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db)
):
    try:
        is_featured = featured.lower() == "true"
        is_trending = trending.lower() == "true"
        
        final_image_url = image_url or "https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?q=80&w=1000&auto=format&fit=crop"
        
        if image and image.filename:
            final_image_url = await resolve_image_url(image, final_image_url)

        tag_list = [tag.strip() for tag in tags.split(",")] if tags else []

        db_prompt = models.Prompt(
            id=str(uuid.uuid4()),
            title=title,
            prompt_text=prompt_text,
            negative_prompt=negative_prompt,
            category=category,
            model=model,
            tags=tag_list,
            image_url=final_image_url,
            aspect_ratio=aspectRatio,
            featured=is_featured,
            trending=is_trending,
            visibility=visibility
        )
        db.add(db_prompt)
        db.commit()
        db.refresh(db_prompt)
        print(f"DEBUG: Saved prompt to DB with image_url: {db_prompt.image_url}")
        
        # Update static SEO files
        try:
            write_static_seo_files(db)
        except Exception as e:
            print(f"Error updating static SEO files: {e}")
            
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
    image_url: str = Form(None),
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
        
        if image and image.filename:
            prompt.image_url = await resolve_image_url(image, prompt.image_url)
        elif image_url:
            prompt.image_url = image_url

        db.commit()
        db.refresh(prompt)
        print(f"DEBUG: Updated prompt in DB with image_url: {prompt.image_url}")
        
        # Update static SEO files
        try:
            write_static_seo_files(db)
        except Exception as e:
            print(f"Error updating static SEO files: {e}")
            
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
    
    # Update static SEO files
    try:
        write_static_seo_files(db)
    except Exception as e:
        print(f"Error updating static SEO files: {e}")
        
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
    except HTTPException as he:
        db.rollback()
        raise he
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

@app.get("/api/notifications")
async def get_notifications(db: Session = Depends(get_db)):
    notifications = []
    
    # 1. Fetch manual persistent admin notifications from the database
    try:
        manual_notifs = db.query(models.Notification).order_by(models.Notification.created_at.desc()).all()
        for m in manual_notifs:
            notifications.append({
                "id": f"manual-{m.id}",
                "text": m.text,
                "type": m.type,
                "link": m.link
            })
    except Exception as e:
        print("Error fetching manual notifications:", e)
    
    # 2. Check for featured prompts
    featured = db.query(models.Prompt).filter(models.Prompt.featured == True).order_by(models.Prompt.created_at.desc()).first()
    if featured:
        notifications.append({
            "id": f"featured-{featured.id}",
            "text": f"Featured: {featured.title} is trending!",
            "type": "trending",
            "link": f"/prompt/{featured.id}"
        })

    # 3. Check for latest prompts
    latest = db.query(models.Prompt).order_by(models.Prompt.created_at.desc()).first()
    if latest:
        notifications.append({
            "id": f"latest-{latest.id}",
            "text": f"New Drop: {latest.title} added to {latest.category}",
            "type": "update",
            "link": f"/prompt/{latest.id}"
        })

    # 4. Showcase Creator Feature Announcement
    notifications.append({
        "id": "showcase-feature-announcement",
        "text": "✨ Showcase Creator is live! Build beautiful story posters from your saved prompts.",
        "type": "new-feature",
        "link": "#showcase"
    })

    # 5. Random system/style tip
    tips = [
        "Pro Tip: Try 'Cinematic' style for realistic portraits",
        "Your saved board is synced across devices",
        "Explore 3D CGI category for modern character designs",
        "Join our community to share your own prompts"
    ]
    import random
    notifications.append({
        "id": "tip-1",
        "text": random.choice(tips),
        "type": "tip",
        "link": "/explore"
    })

    return notifications

@app.get("/api/notifications-admin")
def get_admin_notifications(db: Session = Depends(get_db)):
    return db.query(models.Notification).order_by(models.Notification.created_at.desc()).all()

@app.post("/api/notifications", response_model=schemas.NotificationOut)
def create_notification(notification: schemas.NotificationCreate, db: Session = Depends(get_db)):
    db_notification = models.Notification(
        text=notification.text,
        type=notification.type,
        link=notification.link
    )
    db.add(db_notification)
    db.commit()
    db.refresh(db_notification)
    return db_notification

@app.delete("/api/notifications/{notification_id}")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    db_notif = db.query(models.Notification).filter(models.Notification.id == notification_id).first()
    if not db_notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    db.delete(db_notif)
    db.commit()
    return {"status": "deleted", "id": notification_id}

@app.get("/api/users/{user_id}/activity", response_model=schemas.UserActivityOut)
def get_user_activity(user_id: str, db: Session = Depends(get_db)):
    activity = db.query(models.UserActivity).filter(models.UserActivity.user_id == user_id).first()
    if not activity:
        import datetime
        return {
            "user_id": user_id,
            "saved_prompts": [],
            "liked_prompts": [],
            "recent_prompts": [],
            "updated_at": datetime.datetime.utcnow()
        }
    return activity

@app.post("/api/users/{user_id}/activity", response_model=schemas.UserActivityOut)
def save_user_activity(
    user_id: str,
    activity_data: schemas.UserActivityCreate,
    db: Session = Depends(get_db)
):
    activity = db.query(models.UserActivity).filter(models.UserActivity.user_id == user_id).first()
    if not activity:
        activity = models.UserActivity(
            user_id=user_id,
            saved_prompts=activity_data.saved_prompts,
            liked_prompts=activity_data.liked_prompts,
            recent_prompts=activity_data.recent_prompts
        )
        db.add(activity)
    else:
        activity.saved_prompts = activity_data.saved_prompts
        activity.liked_prompts = activity_data.liked_prompts
        activity.recent_prompts = activity_data.recent_prompts
        import datetime
        activity.updated_at = datetime.datetime.utcnow()
        
    db.commit()
    db.refresh(activity)
    return activity

# --- SEO ENDPOINTS ---

def generate_sitemap_xml(db: Session) -> str:
    from datetime import datetime
    
    # Base URLs
    urls = [
        {"loc": "https://promptro.in/", "priority": "1.0", "changefreq": "daily"},
        {"loc": "https://promptro.in/explore", "priority": "0.8", "changefreq": "daily"},
        {"loc": "https://promptro.in/categories", "priority": "0.8", "changefreq": "weekly"}
    ]
    
    # Public Prompts (including older ones where visibility might be NULL)
    from sqlalchemy import or_
    prompts = db.query(models.Prompt).filter(
        or_(models.Prompt.visibility == "Public", models.Prompt.visibility.is_(None))
    ).all()
    for prompt in prompts:
        lastmod = prompt.created_at.strftime("%Y-%m-%d") if prompt.created_at else datetime.utcnow().strftime("%Y-%m-%d")
        urls.append({
            "loc": f"https://promptro.in/prompt/{prompt.id}",
            "priority": "0.7",
            "changefreq": "monthly",
            "lastmod": lastmod
        })
        
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml += '  <url>\n'
        xml += f'    <loc>{u["loc"]}</loc>\n'
        if "lastmod" in u:
            xml += f'    <lastmod>{u["lastmod"]}</lastmod>\n'
        xml += f'    <changefreq>{u["changefreq"]}</changefreq>\n'
        xml += f'    <priority>{u["priority"]}</priority>\n'
        xml += '  </url>\n'
    xml += '</urlset>'
    
    return xml

def generate_robots_txt() -> str:
    return (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin\n"
        "Disallow: /auth\n"
        "Disallow: /saved\n"
        "Disallow: /asad87\n\n"
        "Sitemap: https://promptro.in/sitemap.xml\n"
    )

def write_static_seo_files(db: Session):
    try:
        sitemap_content = generate_sitemap_xml(db)
        robots_content = generate_robots_txt()
        
        frontend_public_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "public"
        frontend_public_dir.mkdir(parents=True, exist_ok=True)
        
        sitemap_path = frontend_public_dir / "sitemap.xml"
        robots_path = frontend_public_dir / "robots.txt"
        
        sitemap_path.write_text(sitemap_content, encoding="utf-8")
        robots_path.write_text(robots_content, encoding="utf-8")
        print(f"Successfully generated static SEO files at {frontend_public_dir}")
    except Exception as e:
        print(f"Error writing static SEO files: {e}")

@app.get("/sitemap.xml")
def sitemap_xml(db: Session = Depends(get_db)):
    xml_content = generate_sitemap_xml(db)
    return Response(content=xml_content, media_type="application/xml")

@app.get("/robots.txt")
def robots_txt():
    txt_content = generate_robots_txt()
    return PlainTextResponse(content=txt_content)

def resolve_and_cache_ip(ip: str):
    import urllib.request
    import json
    from app.database import SessionLocal
    from app import models

    # Check if the IP is local or private
    is_local = False
    if ip in ("127.0.0.1", "::1", "localhost"):
        is_local = True
    elif ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.16.") or ip.startswith("172.31."):
        is_local = True

    country_name = "India" if is_local else None
    country_code = "IN" if is_local else None

    # Open a new database session
    db = SessionLocal()
    try:
        # Check if already cached
        cached = db.query(models.IpLocationCache).filter(models.IpLocationCache.ip_address == ip).first()
        if cached:
            return

        if not is_local:
            try:
                url = f"http://ip-api.com/json/{ip}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=3) as response:
                    data = json.loads(response.read().decode())
                    if data.get("status") == "success":
                        country_name = data.get("country")
                        country_code = data.get("countryCode")
            except Exception as e:
                print(f"Error fetching IP location for {ip}: {e}")

        # Fallback to "India" if we failed to fetch it, to ensure we have a valid entry
        if not country_name:
            country_name = "India"
            country_code = "IN"

        # Save to cache
        new_cache = models.IpLocationCache(
            ip_address=ip,
            country_name=country_name,
            country_code=country_code
        )
        db.add(new_cache)
        db.commit()
    except Exception as e:
        print(f"Failed to resolve and cache IP {ip}: {e}")
    finally:
        db.close()

@app.post("/api/analytics/track")
def track_page_visit(visit_data: schemas.PageVisitCreate, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "127.0.0.1"
    user_agent = request.headers.get("user-agent")
    db_visit = models.PageVisit(
        ip_address=ip,
        path=visit_data.path,
        referrer=visit_data.referrer,
        user_agent=user_agent
    )
    db.add(db_visit)
    db.commit()
    
    # Resolve IP in background to prevent blocking
    background_tasks.add_task(resolve_and_cache_ip, ip)
    
    return {"status": "success"}

@app.get("/api/analytics/summary", response_model=schemas.AnalyticsSummary)
def get_analytics_summary(db: Session = Depends(get_db)):
    from datetime import datetime, time, timedelta
    from sqlalchemy import func
    
    total_visits = db.query(models.PageVisit).count()
    unique_visitors = db.query(models.PageVisit.ip_address).distinct().count()
    
    # Current week (Mon to Sun) counts
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    daily_counts = []
    for i in range(7):
        target_day = start_of_week + timedelta(days=i)
        start_dt = datetime.combine(target_day, time.min)
        end_dt = datetime.combine(target_day, time.max)
        count = db.query(models.PageVisit).filter(models.PageVisit.created_at >= start_dt, models.PageVisit.created_at <= end_dt).count()
        daily_counts.append(count)
        
    # Traffic sources
    direct_count = 0
    organic_count = 0
    social_count = 0
    referral_count = 0
    
    visits = db.query(models.PageVisit).all()
    total = len(visits)
    if total > 0:
        for v in visits:
            ref = (v.referrer or "").lower()
            if not ref:
                direct_count += 1
            elif any(domain in ref for domain in ["google.", "bing.", "yahoo.", "baidu.", "duckduckgo."]):
                organic_count += 1
            elif any(domain in ref for domain in ["instagram.com", "facebook.com", "twitter.com", "linkedin.com", "t.co", "youtube.com"]):
                social_count += 1
            else:
                referral_count += 1
                
        direct_pct = round((direct_count / total) * 100)
        organic_pct = round((organic_count / total) * 100)
        social_pct = round((social_count / total) * 100)
        referral_pct = round((referral_count / total) * 100)
    else:
        direct_pct = 100
        organic_pct = 0
        social_pct = 0
        referral_pct = 0
        
    traffic_sources = [
        {"label": "Direct", "value": f"{direct_pct}%", "color": "bg-primary"},
        {"label": "Organic Search", "value": f"{organic_pct}%", "color": "bg-blue-400"},
        {"label": "Social", "value": f"{social_pct}%", "color": "bg-pink-500"},
        {"label": "Referral", "value": f"{referral_pct}%", "color": "bg-amber-500"}
    ]
    
    # Calculate top location dynamically
    top_location_str = "India (100%)"
    if total_visits > 0:
        resolved_visits = db.query(models.PageVisit.id).join(
            models.IpLocationCache,
            models.PageVisit.ip_address == models.IpLocationCache.ip_address
        ).count()
        
        top_loc_query = db.query(
            models.IpLocationCache.country_name,
            func.count(models.PageVisit.id).label("visit_count")
        ).join(
            models.IpLocationCache,
            models.PageVisit.ip_address == models.IpLocationCache.ip_address
        ).group_by(
            models.IpLocationCache.country_name
        ).order_by(
            func.count(models.PageVisit.id).desc()
        ).first()
        
        if top_loc_query and resolved_visits > 0:
            country_name, visit_count = top_loc_query
            pct = round((visit_count / resolved_visits) * 100)
            top_location_str = f"{country_name} ({pct}%)"
        else:
            top_location_str = "India (100%)"
    else:
        top_location_str = "Unknown (0%)"
        
    return {
        "totalVisits": total_visits,
        "uniqueVisitors": unique_visitors,
        "dailyVisits": daily_counts,
        "trafficSources": traffic_sources,
        "topLocation": top_location_str
    }

