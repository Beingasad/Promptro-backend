from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Request, BackgroundTasks
from fastapi.responses import Response, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
import uuid
import cloudinary
import cloudinary.uploader
import os
import json
import base64
from pathlib import Path
from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env")
load_dotenv()

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

# Initialize Firebase Admin SDK
def _get_firebase_credential():
    firebase_key_path = BACKEND_DIR / "firebase-service-account.json"
    if firebase_key_path.exists():
        return credentials.Certificate(str(firebase_key_path)), f"file:{firebase_key_path}"

    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    if service_account_json:
        return credentials.Certificate(json.loads(service_account_json)), "env:FIREBASE_SERVICE_ACCOUNT_JSON"

    service_account_b64 = os.getenv("FIREBASE_SERVICE_ACCOUNT_B64")
    if service_account_b64:
        decoded = base64.b64decode(service_account_b64).decode("utf-8")
        return credentials.Certificate(json.loads(decoded)), "env:FIREBASE_SERVICE_ACCOUNT_B64"

    project_id = os.getenv("FIREBASE_PROJECT_ID")
    client_email = os.getenv("FIREBASE_CLIENT_EMAIL")
    private_key = os.getenv("FIREBASE_PRIVATE_KEY")
    if project_id and client_email and private_key:
        private_key = private_key.strip().strip('"').replace("\\n", "\n")
        return credentials.Certificate({
            "type": "service_account",
            "project_id": project_id,
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID", ""),
            "private_key": private_key,
            "client_email": client_email,
            "client_id": os.getenv("FIREBASE_CLIENT_ID", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL", ""),
            "universe_domain": "googleapis.com",
        }), "env:FIREBASE_*"

    return None, None


try:
    if not firebase_admin._apps:
        cred, cred_source = _get_firebase_credential()
        if cred:
            firebase_admin.initialize_app(cred)
            print(f"Firebase Admin SDK initialized successfully from {cred_source}!")
        else:
            print(
                "Firebase Admin SDK not initialized. Provide backend/firebase-service-account.json, "
                "FIREBASE_SERVICE_ACCOUNT_JSON, FIREBASE_SERVICE_ACCOUNT_B64, or FIREBASE_PROJECT_ID/"
                "FIREBASE_CLIENT_EMAIL/FIREBASE_PRIVATE_KEY."
            )
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")

from app import models, schemas
from app.database import engine, get_db

models.Base.metadata.create_all(bind=engine)

def ensure_runtime_schema():
    try:
        with engine.begin() as conn:
            if engine.dialect.name == "sqlite":
                columns = {
                    row[1]
                    for row in conn.execute(text("PRAGMA table_info(user_profiles)")).fetchall()
                }
                if "username" not in columns:
                    conn.execute(text("ALTER TABLE user_profiles ADD COLUMN username VARCHAR"))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_profiles_username "
                    "ON user_profiles (username)"
                ))

                # Check user_activities for collections column
                activity_cols = {
                    row[1]
                    for row in conn.execute(text("PRAGMA table_info(user_activities)")).fetchall()
                }
                if "collections" not in activity_cols:
                    conn.execute(text("ALTER TABLE user_activities ADD COLUMN collections JSON"))
            else:
                conn.execute(text("ALTER TABLE user_profiles ADD COLUMN IF NOT EXISTS username VARCHAR"))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_user_profiles_username "
                    "ON user_profiles (username)"
                ))
                
                try:
                    conn.execute(text("ALTER TABLE user_activities ADD COLUMN IF NOT EXISTS collections JSON"))
                except Exception as ex:
                    print(f"Failed to add collections column in non-sqlite DB (might already exist): {ex}")
    except Exception as e:
        print(f"Runtime schema check failed: {e}")

ensure_runtime_schema()
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
            models.Prompt(id=str(uuid.uuid4()), title="Cyberpunk Cityscape", category="Sci-Fi", model="Midjourney v6", image_url="https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?q=80&w=1000&auto=format&fit=crop", prompt_text="A highly detailed cyberpunk cityscape at night...", likes=1205, views=4500, aspect_ratio="3 / 2"),
            models.Prompt(id=str(uuid.uuid4()), title="Ethereal Forest Spirit", category="Fantasy", model="DALL-E 3", image_url="https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=800&auto=format&fit=crop", prompt_text="Ethereal glowing spirit in a dark mystical forest...", likes=840, views=3200, aspect_ratio="800 / 1210"),
            models.Prompt(id=str(uuid.uuid4()), title="Minimalist Architecture", category="Architecture", model="SDXL", image_url="https://images.unsplash.com/photo-1600585154340-be6161a56a0c?q=80&w=1200&auto=format&fit=crop", prompt_text="Clean minimalist concrete architecture...", likes=532, views=2100, aspect_ratio="1200 / 800"),
            models.Prompt(id=str(uuid.uuid4()), title="Neon Samurai", category="Anime", model="Niji Journey", image_url="https://images.unsplash.com/photo-1533613220915-609f661a6fe1?q=80&w=900&auto=format&fit=crop", prompt_text="A neon lit samurai standing in the rain...", likes=2100, views=8900, aspect_ratio="900 / 1125"),
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
    "http://localhost:5174",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
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

    # Read the uploaded content
    try:
        original_content = await image.read()
        if not original_content:
            return fallback_url
        print(f"IMAGE_UPLOAD: Received '{image.filename}' ({len(original_content) / 1024:.1f} KB)")
    except Exception as e:
        print(f"IMAGE_READ_FAILED: {e}")
        return fallback_url

    # Check Cloudinary configuration
    cloudinary_cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    cloudinary_api_key = os.getenv("CLOUDINARY_API_KEY")
    cloudinary_api_secret = os.getenv("CLOUDINARY_API_SECRET")
    cloudinary_url = os.getenv("CLOUDINARY_URL")

    is_cloudinary_configured = bool(
        (cloudinary_cloud_name and cloudinary_api_key and cloudinary_api_secret)
        or cloudinary_url
    )

    is_production = os.getenv("RENDER") is not None

    if is_production and not is_cloudinary_configured:
        raise HTTPException(
            status_code=500,
            detail="CRITICAL CONFIGURATION ERROR: Cloudinary is NOT configured in production environment!"
        )

    if is_cloudinary_configured:
        import asyncio
        import io

        def compress_and_upload():
            # Compress only if image is over 500KB
            content = compress_image_to_500kb(original_content, image.filename)
            print(f"IMAGE_AFTER_COMPRESS: {len(content) / 1024:.1f} KB — uploading to Cloudinary...")
            result = cloudinary.uploader.upload(content, folder="promptro_prompts", resource_type="image")
            return result.get("secure_url")

        try:
            loop = asyncio.get_event_loop()
            url = await loop.run_in_executor(None, compress_and_upload)
            if url:
                url = url if url.startswith("https://") else url.replace("http://", "https://")
                print(f"CLOUDINARY_UPLOAD_SUCCESS: {url}")
                return url
            else:
                raise ValueError("Cloudinary returned no secure_url")
        except Exception as e:
            print(f"CLOUDINARY_UPLOAD_FAILED: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Image upload to Cloudinary failed: {str(e)}"
            )
    else:
        print("WARNING: Cloudinary not configured. Using local storage.")

    # Local development fallback
    try:
        content = compress_image_to_500kb(original_content, image.filename)
        extension = Path(image.filename).suffix or ".jpg"
        filename = f"{uuid.uuid4()}{extension}"
        upload_path = UPLOAD_DIR / filename
        upload_path.write_bytes(content)
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip('/')
        if not backend_url.startswith('http') and backend_url:
            backend_url = f"https://{backend_url}"
        final_url = f"{backend_url}/uploads/{filename}"
        print(f"LOCAL_UPLOAD_SUCCESS: {final_url}")
        return final_url
    except Exception as e:
        print(f"ERROR: Local upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"Local image upload failed: {str(e)}")

def send_email_background(to_email: str, subject: str, body: str, html: str = None):
    print(f"\n==================================================")
    print(f"[DEBUG EMAIL] Sending to: {to_email}")
    print(f"[DEBUG EMAIL] Subject: {subject}")
    if body:
        print(f"[DEBUG EMAIL] Plain body length: {len(body)}")
    if html:
        print(f"[DEBUG EMAIL] HTML length: {len(html)}")
    print(f"==================================================\n")
    resend_api_key = os.getenv("RESEND_API_KEY")
    if resend_api_key:
        import urllib.request
        import urllib.error
        import json

        print("Using Resend API to send email...")
        sender_email = os.getenv("SMTP_USER", "otp@promptro.in")
        if not sender_email or "gmail.com" in sender_email or "onboarding@resend.dev" in sender_email:
            sender_email = "otp@promptro.in"

        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        payload = {
            "from": f"Promptro <{sender_email}>",
            "to": [to_email],
            "subject": subject,
        }
        if html:
            payload["html"] = html
            if body:
                payload["text"] = body
        else:
            payload["text"] = body
        
        try:
            req = urllib.request.Request(
                url, 
                data=json.dumps(payload).encode('utf-8'), 
                headers=headers, 
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res_body = response.read().decode('utf-8')
                print(f"Email sent successfully via Resend to {to_email}: {res_body}")
                return {"provider": "resend", "response": res_body}
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8", errors="replace")
            print(f"Failed to send email via Resend to {to_email}: {e.code} {e.reason} {error_body}")
            raise RuntimeError(f"Resend email failed: {e.code} {error_body}") from e
        except Exception as e:
            print(f"Failed to send email via Resend to {to_email}: {e}")
            raise RuntimeError(f"Resend email failed: {e}") from e

    # Fallback to local SMTP
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = os.getenv("SMTP_USER", "support.promptro@gmail.com")
    sender_password = os.getenv("SMTP_PASSWORD")
    
    if not sender_password:
        print("SMTP_PASSWORD is not set. Cannot send email.")
        raise RuntimeError("SMTP_PASSWORD is not set. Cannot send email.")

    try:
        msg = MIMEMultipart()
        msg['From'] = f"Promptro Support <{sender_email}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if html:
            msg.attach(MIMEText(html, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            
        print(f"Email sent successfully to {to_email}")
        return {"provider": "smtp"}
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        raise RuntimeError(f"SMTP email failed: {e}") from e

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Promptro API is running"}

@app.head("/")
def head_root():
    return Response(status_code=200)

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

@app.patch("/api/feedback/{feedback_id}/status", response_model=schemas.FeedbackOut)
def update_feedback_status(feedback_id: int, body: schemas.FeedbackStatusUpdate, db: Session = Depends(get_db)):
    feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    feedback.status = body.status
    db.commit()
    db.refresh(feedback)
    return feedback

@app.post("/api/feedback/{feedback_id}/reply", response_model=schemas.FeedbackOut)
def reply_to_feedback(feedback_id: int, body: schemas.FeedbackReply, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    feedback = db.query(models.Feedback).filter(models.Feedback.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    feedback.reply_text = body.reply_text
    feedback.replied_at = func.now()
    feedback.status = "replied"
    db.commit()
    db.refresh(feedback)
    
    if feedback.email and feedback.email != "N/A" and "@" in feedback.email:
        email_subject = f"Re: {feedback.subject or 'Promptro Support Inquiry'}"
        email_body = (
            f"Hello {feedback.user or 'Customer'},\n\n"
            f"{body.reply_text}\n\n"
            f"Best regards,\n"
            f"Promptro Support Team\n"
            f"support.promptro@gmail.com"
        )
        background_tasks.add_task(send_email_background, feedback.email, email_subject, email_body)
        
    return feedback

@app.get("/api/feedback/stats")
def get_feedback_stats(db: Session = Depends(get_db)):
    total = db.query(models.Feedback).count()
    unread = db.query(models.Feedback).filter(models.Feedback.status == "unread").count()
    read_count = db.query(models.Feedback).filter(models.Feedback.status == "read").count()
    replied = db.query(models.Feedback).filter(models.Feedback.status == "replied").count()
    resolved = db.query(models.Feedback).filter(models.Feedback.status == "resolved").count()
    open_tickets = unread + read_count
    response_rate = round((replied + resolved) / total * 100, 1) if total > 0 else 0
    return {
        "total": total,
        "unread": unread,
        "read": read_count,
        "replied": replied,
        "resolved": resolved,
        "open_tickets": open_tickets,
        "response_rate": response_rate
    }

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
    from datetime import datetime, timedelta
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    
    # 1. Fetch manual persistent admin notifications from the database (only last 3 days)
    try:
        manual_notifs = db.query(models.Notification).filter(
            models.Notification.created_at >= three_days_ago
        ).order_by(models.Notification.created_at.desc()).all()
        for m in manual_notifs:
            notifications.append({
                "id": f"manual-{m.id}",
                "text": m.text,
                "type": m.type,
                "link": m.link
            })
    except Exception as e:
        print("Error fetching manual notifications:", e)
    
    # 2. Check for featured prompts (only last 3 days)
    featured = db.query(models.Prompt).filter(
        models.Prompt.featured == True,
        models.Prompt.created_at >= three_days_ago
    ).order_by(models.Prompt.created_at.desc()).first()
    if featured:
        notifications.append({
            "id": f"featured-{featured.id}",
            "text": f"Featured: {featured.title} is trending!",
            "type": "trending",
            "link": f"/prompt/{featured.id}"
        })

    # 3. Check for latest prompts (only last 3 days)
    latest = db.query(models.Prompt).filter(
        models.Prompt.created_at >= three_days_ago
    ).order_by(models.Prompt.created_at.desc()).first()
    if latest:
        # Avoid duplicates if latest is same as featured
        if not featured or latest.id != featured.id:
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

    # 5. Major Update Announcement v1.1.0
    notifications.append({
        "id": "release-v1.1.0",
        "text": "🚀 Release v1.1.0: Private Collections boards, Premium Cover layouts, responsive mobile zoom cropping & Auto profile completion are live!",
        "type": "new-feature",
        "link": "/collections"
    })

    # 6. Random system/style tip
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
            "collections": [],
            "updated_at": datetime.datetime.utcnow()
        }
    return activity

@app.get("/api/collections/{collection_id}")
def get_public_collection(collection_id: str, db: Session = Depends(get_db)):
    activities = db.query(models.UserActivity).filter(models.UserActivity.collections.isnot(None)).all()
    for act in activities:
        collections = act.collections
        if isinstance(collections, list):
            for col in collections:
                if col.get("id") == collection_id:
                    return col
    raise HTTPException(status_code=404, detail="Collection not found")

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
            recent_prompts=activity_data.recent_prompts,
            collections=activity_data.collections
        )
        db.add(activity)
    else:
        activity.saved_prompts = activity_data.saved_prompts
        activity.liked_prompts = activity_data.liked_prompts
        activity.recent_prompts = activity_data.recent_prompts
        activity.collections = activity_data.collections
        import datetime
        activity.updated_at = datetime.datetime.utcnow()
        
    db.commit()
    db.refresh(activity)
    return activity

# --- SEO ENDPOINTS ---

def generate_sitemap_xml(db: Session) -> str:
    from datetime import datetime
    
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    # Base URLs
    urls = [
        {"loc": "https://promptro.in/", "priority": "1.0", "changefreq": "daily", "lastmod": today},
        {"loc": "https://promptro.in/explore", "priority": "0.8", "changefreq": "daily", "lastmod": today},
        {"loc": "https://promptro.in/categories", "priority": "0.8", "changefreq": "weekly", "lastmod": today},
        # Blog
        {"loc": "https://promptro.in/blog", "priority": "0.8", "changefreq": "weekly", "lastmod": today},
        {"loc": "https://promptro.in/blog/what-is-an-ai-image-prompt", "priority": "0.7", "changefreq": "monthly", "lastmod": today},
        {"loc": "https://promptro.in/blog/best-midjourney-prompts-2026", "priority": "0.7", "changefreq": "monthly", "lastmod": today},
        {"loc": "https://promptro.in/blog/how-to-use-negative-prompts", "priority": "0.7", "changefreq": "monthly", "lastmod": today},
        # Trust Pages
        {"loc": "https://promptro.in/about", "priority": "0.6", "changefreq": "monthly", "lastmod": today},
        {"loc": "https://promptro.in/contact", "priority": "0.5", "changefreq": "monthly", "lastmod": today},
        {"loc": "https://promptro.in/privacy-policy", "priority": "0.5", "changefreq": "monthly", "lastmod": today},
        {"loc": "https://promptro.in/terms", "priority": "0.5", "changefreq": "monthly", "lastmod": today},
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


@app.get("/api/consent/{user_id}", response_model=schemas.ConsentStatusOut)
def get_user_consent(user_id: str, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(models.UserProfile.firebase_uid == user_id).first()
    consent = db.query(models.UserConsent).filter(models.UserConsent.user_id == user_id).first()
    
    terms_accepted = False
    terms_accepted_at = None
    privacy_accepted_at = None
    cookie_consent_status = "pending"
    email = None
    
    if profile:
        terms_accepted = profile.terms_accepted
        terms_accepted_at = profile.terms_accepted_at
        privacy_accepted_at = profile.terms_accepted_at
        email = profile.email
        
    if consent:
        if consent.terms_accepted:
            terms_accepted = True
            terms_accepted_at = consent.terms_accepted_at
        privacy_accepted_at = consent.privacy_accepted_at or terms_accepted_at
        cookie_consent_status = consent.cookie_consent_status
        if not email:
            email = consent.email
            
    return {
        "id": consent.id if consent else 0,
        "user_id": user_id,
        "email": email,
        "terms_accepted": terms_accepted,
        "terms_accepted_at": terms_accepted_at,
        "privacy_accepted_at": privacy_accepted_at,
        "cookie_consent_status": cookie_consent_status
    }


@app.post("/api/consent/accept", response_model=schemas.ConsentStatusOut)
def accept_user_consent(consent_data: schemas.ConsentAccept, db: Session = Depends(get_db)):
    from datetime import datetime
    consent = db.query(models.UserConsent).filter(models.UserConsent.user_id == consent_data.user_id).first()
    now = datetime.utcnow()
    if not consent:
        consent = models.UserConsent(
            user_id=consent_data.user_id,
            email=consent_data.email,
            terms_accepted=True,
            terms_accepted_at=now,
            privacy_accepted_at=now,
            cookie_consent_status="pending"
        )
        db.add(consent)
    else:
        consent.terms_accepted = True
        consent.terms_accepted_at = now
        consent.privacy_accepted_at = now
        if consent_data.email:
            consent.email = consent_data.email
            
    # Update user profile as well
    profile = db.query(models.UserProfile).filter(models.UserProfile.firebase_uid == consent_data.user_id).first()
    if profile:
        profile.terms_accepted = True
        profile.terms_accepted_at = now
        
    db.commit()
    db.refresh(consent)
    return {
        "id": consent.id,
        "user_id": consent.user_id,
        "email": consent.email,
        "terms_accepted": consent.terms_accepted,
        "terms_accepted_at": consent.terms_accepted_at,
        "privacy_accepted_at": consent.privacy_accepted_at,
        "cookie_consent_status": consent.cookie_consent_status
    }


@app.post("/api/consent/cookie")
def update_cookie_consent(cookie_data: schemas.CookieConsentUpdate, db: Session = Depends(get_db)):
    if not cookie_data.user_id:
        return {"status": "success", "message": "Cookie consent saved in localStorage"}
    
    consent = db.query(models.UserConsent).filter(models.UserConsent.user_id == cookie_data.user_id).first()
    if not consent:
        consent = models.UserConsent(
            user_id=cookie_data.user_id,
            terms_accepted=False,
            cookie_consent_status=cookie_data.status
        )
        db.add(consent)
    else:
        consent.cookie_consent_status = cookie_data.status
    db.commit()
    return {"status": "success", "cookie_consent_status": cookie_data.status}


# --- OTP AUTH ENDPOINTS ---

@app.post("/api/auth/send-otp")
def send_otp(body: schemas.OTPRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    import random
    from datetime import datetime, timedelta

    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # Check if user already exists
    existing_user = db.query(models.UserProfile).filter(models.UserProfile.email == email).first()
    if not existing_user:
        # Fallback to UserConsent for legacy users
        consent = db.query(models.UserConsent).filter(models.UserConsent.email == email).first()
        if consent:
            raise HTTPException(status_code=400, detail="An account already exists with this email.")
    else:
        if existing_user.provider == "google":
            raise HTTPException(status_code=400, detail="This email is registered with Google. Please log in using Google.")
        else:
            raise HTTPException(status_code=400, detail="An account already exists with this email.")

    # Rate limit: prevent resend within 60 seconds
    recent = db.query(models.OTPVerification).filter(
        models.OTPVerification.email == email,
        models.OTPVerification.verified == False,
        models.OTPVerification.created_at >= datetime.utcnow() - timedelta(seconds=60)
    ).first()
    if recent:
        raise HTTPException(status_code=429, detail="Please wait before requesting a new OTP")

    # Generate 6-digit OTP
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # Store OTP
    otp_record = models.OTPVerification(
        email=email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    db.add(otp_record)
    db.commit()

    # Send OTP email before returning success so delivery/config errors are visible to the UI.
    email_subject = "Your Promptro Verification Code"
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Verify Your Promptro Account</title>
  <style>
    body {{
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f6f5fa;
      color: #171421;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: 40px auto;
      background: #ffffff;
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.05);
      border: 1px solid #e9e2f3;
    }}
    .header {{
      background: linear-gradient(135deg, #8b5cf6 0%, #ff6a3d 100%);
      padding: 40px 20px;
      text-align: center;
    }}
    .header h1 {{
      color: #ffffff;
      margin: 0;
      font-size: 28px;
      font-weight: 900;
      letter-spacing: -0.03em;
    }}
    .content {{
      padding: 40px 30px;
      text-align: center;
    }}
    .content h1 {{
      font-size: 24px;
      font-weight: 800;
      margin-bottom: 16px;
      color: #171421;
    }}
    .content p {{
      font-size: 14px;
      line-height: 1.6;
      color: #5f5774;
      margin-bottom: 30px;
    }}
    .otp-code {{
      display: inline-block;
      font-size: 32px;
      font-weight: 900;
      color: #8b5cf6;
      letter-spacing: 0.15em;
      padding: 12px 36px;
      background-color: #f3edff;
      border-radius: 16px;
      margin: 20px 0;
      border: 1px dashed #c0a3ff;
    }}
    .footer {{
      background-color: #faf9fc;
      padding: 24px;
      text-align: center;
      font-size: 11px;
      color: #978eaa;
      border-top: 1px solid #e9e2f3;
    }}
    .footer a {{
      color: #8b5cf6;
      text-decoration: none;
      font-weight: bold;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Promptro</h1>
    </div>
    <div class="content">
      <h1>Verify Your Email Address</h1>
      <p>Hello,</p>
      <p>Thank you for registering with Promptro! Use the verification code below to complete your sign-up process. This code is valid for <strong>5 minutes</strong>.</p>
      <div class="otp-code">{otp_code}</div>
      <p>If you did not request this verification code, you can safely ignore this email.</p>
    </div>
    <div class="footer">
      <p>&copy; 2026 Promptro. All rights reserved.</p>
    </div>
  </div>
</body>
</html>
"""
    body_text = f"Hello,\n\nYour Promptro verification code is: {otp_code}\n\nThis code will expire in 5 minutes.\nIf you did not request this code, please ignore this email.\n\nBest regards,\nPromptro Team"
    try:
        send_email_background(email, email_subject, body_text, html_content)
    except Exception as e:
        db.delete(otp_record)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Failed to send OTP email: {str(e)}")

    return {"status": "sent", "message": "OTP sent to your email"}


@app.post("/api/auth/verify-otp")
def verify_otp(body: schemas.OTPVerify, db: Session = Depends(get_db)):
    from datetime import datetime

    email = body.email.strip().lower()
    otp = body.otp.strip()

    if not otp or len(otp) != 6:
        raise HTTPException(status_code=400, detail="Invalid OTP format")

    # Find the latest unverified OTP for this email
    otp_record = db.query(models.OTPVerification).filter(
        models.OTPVerification.email == email,
        models.OTPVerification.otp_code == otp,
        models.OTPVerification.verified == False
    ).order_by(models.OTPVerification.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP. Please check and try again.")

    # Check expiry
    if datetime.utcnow() > otp_record.expires_at.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # Mark as verified
    otp_record.verified = True
    db.commit()

    return {"status": "verified", "message": "Email verified successfully"}


@app.post("/api/auth/register-profile", response_model=schemas.UserProfileOut)
def register_profile(body: schemas.UserProfileCreate, db: Session = Depends(get_db)):
    from datetime import datetime

    # Check if profile already exists
    existing = db.query(models.UserProfile).filter(
        models.UserProfile.firebase_uid == body.firebase_uid
    ).first()
    if existing:
        return existing

    now = datetime.utcnow()
    profile = models.UserProfile(
        firebase_uid=body.firebase_uid,
        first_name=body.first_name,
        last_name=body.last_name,
        gender=body.gender,
        email=body.email.strip().lower(),
        provider=body.provider or "email",
        terms_accepted=body.terms_accepted,
        terms_accepted_at=now if body.terms_accepted else None,
        email_verified=True if body.provider == "google" else False
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@app.get("/api/auth/profile/{firebase_uid}", response_model=schemas.UserProfileOut)
def get_user_profile(firebase_uid: str, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.firebase_uid == firebase_uid
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.put("/api/auth/profile/{firebase_uid}", response_model=schemas.UserProfileOut)
def update_user_profile(firebase_uid: str, body: schemas.UserProfileUpdate, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.firebase_uid == firebase_uid
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    if body.username is not None:
        username_clean = body.username.strip()
        if username_clean:
            # Check if this username is already taken by another user
            if username_clean != profile.username:
                existing = db.query(models.UserProfile).filter(
                    models.UserProfile.username == username_clean
                ).first()
                if existing:
                    raise HTTPException(status_code=400, detail="Username is already taken")
            profile.username = username_clean
        else:
            profile.username = None

    if body.first_name is not None:
        first_name_clean = body.first_name.strip()
        if not first_name_clean:
            raise HTTPException(status_code=400, detail="First name cannot be empty")
        profile.first_name = first_name_clean

    if body.last_name is not None:
        profile.last_name = body.last_name.strip() if body.last_name.strip() else None

    if body.gender is not None:
        profile.gender = body.gender.strip() if body.gender.strip() else None

    db.commit()
    db.refresh(profile)
    return profile



@app.patch("/api/auth/profile/{firebase_uid}/verify-email")
def verify_user_email(firebase_uid: str, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.firebase_uid == firebase_uid
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.email_verified = True
    db.commit()
    return {"status": "success", "email_verified": True}


@app.get("/api/auth/check-email")
def check_email(email: str, db: Session = Depends(get_db)):
    email_clean = email.strip().lower()
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.email == email_clean
    ).first()
    if profile:
        return {"exists": True, "provider": profile.provider}
    
    # Fallback to UserConsent for legacy users
    consent = db.query(models.UserConsent).filter(
        models.UserConsent.email == email_clean
    ).first()
    if consent:
        return {"exists": True, "provider": "email"}
        
    return {"exists": False}


# --- ADMIN USER MANAGEMENT ENDPOINTS ---

@app.get("/api/admin/users")
def get_admin_users(db: Session = Depends(get_db)):
    profiles = db.query(models.UserProfile).all()
    result = []
    for p in profiles:
        # Get user activity
        activity = db.query(models.UserActivity).filter(
            models.UserActivity.user_id == p.firebase_uid
        ).first()
        
        # Get user consent
        consent = db.query(models.UserConsent).filter(
            models.UserConsent.user_id == p.firebase_uid
        ).first()
        
        saved_count = len(activity.saved_prompts) if activity and activity.saved_prompts else 0
        liked_count = len(activity.liked_prompts) if activity and activity.liked_prompts else 0
        recent_count = len(activity.recent_prompts) if activity and activity.recent_prompts else 0
        
        result.append({
            "firebase_uid": p.firebase_uid,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "gender": p.gender,
            "email": p.email,
            "provider": p.provider,
            "terms_accepted": p.terms_accepted,
            "terms_accepted_at": p.terms_accepted_at,
            "email_verified": p.email_verified,
            "created_at": p.created_at,
            "activity": {
                "saved_count": saved_count,
                "liked_count": liked_count,
                "recent_count": recent_count,
                "updated_at": activity.updated_at if activity else None
            },
            "consent": {
                "cookie_consent_status": consent.cookie_consent_status if consent else "pending",
                "privacy_accepted_at": consent.privacy_accepted_at if consent else None
            }
        })

    # Include legacy consent-only users without mutating the database during a GET request.
    profile_uids = {p.firebase_uid for p in profiles if p.firebase_uid}
    legacy_consents = db.query(models.UserConsent).all()
    for c in legacy_consents:
        if not c.user_id or c.user_id in profile_uids:
            continue
        # Skip anonymous/guest users without an email
        if not c.email or not c.email.strip():
            continue

        activity = db.query(models.UserActivity).filter(
            models.UserActivity.user_id == c.user_id
        ).first()

        saved_count = len(activity.saved_prompts) if activity and activity.saved_prompts else 0
        liked_count = len(activity.liked_prompts) if activity and activity.liked_prompts else 0
        recent_count = len(activity.recent_prompts) if activity and activity.recent_prompts else 0

        result.append({
            "firebase_uid": c.user_id,
            "first_name": "User",
            "last_name": None,
            "gender": "Not specified",
            "email": c.email,
            "provider": "email",
            "terms_accepted": c.terms_accepted,
            "terms_accepted_at": c.terms_accepted_at,
            "email_verified": False,
            "created_at": c.created_at,
            "activity": {
                "saved_count": saved_count,
                "liked_count": liked_count,
                "recent_count": recent_count,
                "updated_at": activity.updated_at if activity else None
            },
            "consent": {
                "cookie_consent_status": c.cookie_consent_status,
                "privacy_accepted_at": c.privacy_accepted_at
            }
        })

    # Sort users by registration date descending (latest first)
    def get_sort_key(item):
        dt = item.get("created_at")
        if not dt:
            return 0.0
        if hasattr(dt, "timestamp"):
            return dt.timestamp()
        return 0.0

    result.sort(key=get_sort_key, reverse=True)
    return result


@app.delete("/api/admin/users/{firebase_uid}")
def delete_admin_user(firebase_uid: str, db: Session = Depends(get_db)):
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.firebase_uid == firebase_uid
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    user_email = profile.email
    
    # 1. Delete from UserProfile
    db.delete(profile)
    
    # 2. Delete from UserActivity
    db.query(models.UserActivity).filter(
        models.UserActivity.user_id == firebase_uid
    ).delete()
    
    # 3. Delete from UserConsent
    db.query(models.UserConsent).filter(
        models.UserConsent.user_id == firebase_uid
    ).delete()
    
    # 4. Delete from SavedPrompt
    db.query(models.SavedPrompt).filter(
        models.SavedPrompt.user_id == firebase_uid
    ).delete()
    
    # 5. Delete from OTPVerification
    if user_email:
        db.query(models.OTPVerification).filter(
            models.OTPVerification.email == user_email
        ).delete()
        
    db.commit()
    return {"status": "success", "message": f"User {firebase_uid} permanently removed from database."}


@app.post("/api/auth/send-verification")
def send_verification(body: schemas.VerificationRequest, request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    import secrets
    from datetime import datetime, timedelta
    
    email = body.email.strip().lower()
    firebase_uid = body.firebase_uid.strip()
    
    # 1. Check if user profile exists
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.firebase_uid == firebase_uid
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="User profile not found")
        
    # 2. Check if already verified
    if profile.email_verified:
        return {"status": "already_verified", "message": "Email is already verified"}
        
    # 3. Generate secure token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=24)
    
    # 4. Save to DB
    verification_record = models.EmailVerificationToken(
        email=email,
        token=token,
        expires_at=expires_at,
        verified=False
    )
    db.add(verification_record)
    db.commit()
    
    # 5. Build verification link
    # We can detect the origin from request headers (fallback to promptro.in)
    origin = request.headers.get("origin") or "https://promptro.in"
    verification_link = f"{origin}/verify-email?token={token}"
    
    # 6. HTML template
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Verify Your Promptro Account</title>
  <style>
    body {{
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f6f5fa;
      color: #171421;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: 40px auto;
      background: #ffffff;
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.05);
      border: 1px solid #e9e2f3;
    }}
    .header {{
      background: linear-gradient(135deg, #8b5cf6 0%, #ff6a3d 100%);
      padding: 40px 20px;
      text-align: center;
    }}
    .header h1 {{
      color: #ffffff;
      margin: 0;
      font-size: 28px;
      font-weight: 900;
      letter-spacing: -0.03em;
    }}
    .content {{
      padding: 40px 30px;
      text-align: center;
    }}
    .content h1 {{
      font-size: 24px;
      font-weight: 800;
      margin-bottom: 16px;
      color: #171421;
    }}
    .content p {{
      font-size: 14px;
      line-height: 1.6;
      color: #5f5774;
      margin-bottom: 30px;
    }}
    .btn {{
      display: inline-block;
      padding: 14px 36px;
      background: linear-gradient(135deg, #8b5cf6 0%, #ff6a3d 100%);
      color: #ffffff !important;
      text-decoration: none;
      font-weight: bold;
      border-radius: 9999px;
      box-shadow: 0 10px 20px rgba(139, 92, 246, 0.2);
      font-size: 14px;
    }}
    .footer {{
      background-color: #faf9fc;
      padding: 24px;
      text-align: center;
      font-size: 11px;
      color: #978eaa;
      border-top: 1px solid #e9e2f3;
    }}
    .footer a {{
      color: #8b5cf6;
      text-decoration: none;
      font-weight: bold;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Promptro</h1>
    </div>
    <div class="content">
      <h1>Verify Your Email Address</h1>
      <p>Thank you for signing up for Promptro! Please verify your email address to secure your account and unlock all premium features of the Promptro platform.</p>
      <a href="{verification_link}" class="btn">Verify Email Address</a>
      <p style="margin-top: 30px; font-size: 12px; color: #978eaa;">If the button doesn't work, copy and paste this link into your browser:<br>
      <a href="{verification_link}" style="color: #8b5cf6; word-break: break-all;">{verification_link}</a></p>
    </div>
    <div class="footer">
      <p>&copy; 2026 Promptro. All rights reserved.</p>
      <p>If you did not sign up for an account, you can safely ignore this email.</p>
    </div>
  </div>
</body>
</html>
"""
    subject = "Verify your Promptro account"
    body_text = f"Please verify your Promptro account by clicking this link: {verification_link}"
    
    background_tasks.add_task(send_email_background, email, subject, body_text, html_content)
    return {"status": "sent", "message": "Verification email sent"}


@app.post("/api/auth/confirm-verification")
def confirm_verification(body: schemas.ConfirmVerificationRequest, db: Session = Depends(get_db)):
    from datetime import datetime
    
    token = body.token.strip()
    
    # 1. Find the token
    record = db.query(models.EmailVerificationToken).filter(
        models.EmailVerificationToken.token == token,
        models.EmailVerificationToken.verified == False
    ).first()
    
    if not record:
        raise HTTPException(status_code=400, detail="Invalid or already used verification token")
        
    # 2. Check expiry
    if datetime.utcnow() > record.expires_at.replace(tzinfo=None):
         raise HTTPException(status_code=400, detail="Verification token has expired. Please request a new one.")
         
    # 3. Mark token as verified
    record.verified = True
    
    # 4. Find user profile and mark as verified
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.email == record.email
    ).first()
    if profile:
        profile.email_verified = True
        db.commit()
        return {"status": "success", "message": "Email verified successfully"}
    else:
        db.commit()
        raise HTTPException(status_code=404, detail="User profile not found for this email")


@app.post("/api/auth/forgot-password/send-otp")
def forgot_password_send_otp(body: schemas.OTPRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    import random
    from datetime import datetime, timedelta

    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Invalid email address")

    # 1. Verify user profile exists in database
    profile = db.query(models.UserProfile).filter(
        models.UserProfile.email == email
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No account found with this email address.")
    
    if profile.provider == "google":
        raise HTTPException(status_code=400, detail="This account is registered via Google. Please log in using Google.")

    # 2. Cooldown check: prevent resend within 60 seconds
    recent = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == email,
        models.PasswordResetOTP.verified == False,
        models.PasswordResetOTP.created_at >= datetime.utcnow() - timedelta(seconds=60)
    ).first()
    if recent:
        raise HTTPException(status_code=429, detail="Please wait before requesting a new OTP")

    # 3. Generate 6-digit OTP code
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # 4. Store OTP in database
    otp_record = models.PasswordResetOTP(
        email=email,
        otp_code=otp_code,
        expires_at=expires_at,
        verified=False
    )
    db.add(otp_record)
    db.commit()

    # 5. Send OTP Email using Resend
    email_subject = "Your Promptro Password Reset Code"
    html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Reset Your Promptro Password</title>
  <style>
    body {{
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      background-color: #f6f5fa;
      color: #171421;
      margin: 0;
      padding: 0;
    }}
    .container {{
      max-width: 600px;
      margin: 40px auto;
      background: #ffffff;
      border-radius: 24px;
      overflow: hidden;
      box-shadow: 0 10px 30px rgba(0,0,0,0.05);
      border: 1px solid #e9e2f3;
    }}
    .header {{
      background: linear-gradient(135deg, #8b5cf6 0%, #ff6a3d 100%);
      padding: 40px 20px;
      text-align: center;
    }}
    .header h1 {{
      color: #ffffff;
      margin: 0;
      font-size: 28px;
      font-weight: 900;
      letter-spacing: -0.03em;
    }}
    .content {{
      padding: 40px 30px;
      text-align: center;
    }}
    .content h1 {{
      font-size: 24px;
      font-weight: 800;
      margin-bottom: 16px;
      color: #171421;
    }}
    .content p {{
      font-size: 14px;
      line-height: 1.6;
      color: #5f5774;
      margin-bottom: 30px;
    }}
    .otp-code {{
      display: inline-block;
      font-size: 32px;
      font-weight: 900;
      color: #8b5cf6;
      letter-spacing: 0.15em;
      padding: 12px 36px;
      background-color: #f3edff;
      border-radius: 16px;
      margin: 20px 0;
      border: 1px dashed #c0a3ff;
    }}
    .footer {{
      background-color: #faf9fc;
      padding: 24px;
      text-align: center;
      font-size: 11px;
      color: #978eaa;
      border-top: 1px solid #e9e2f3;
    }}
    .footer a {{
      color: #8b5cf6;
      text-decoration: none;
      font-weight: bold;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>Promptro</h1>
    </div>
    <div class="content">
      <h1>Reset Your Password</h1>
      <p>Hello,</p>
      <p>We received a request to reset the password for your Promptro account. Use the verification code below to proceed. This code is valid for <strong>5 minutes</strong>.</p>
      <div class="otp-code">{otp_code}</div>
      <p>If you did not request a password reset, you can safely ignore this email.</p>
    </div>
    <div class="footer">
      <p>&copy; 2026 Promptro. All rights reserved.</p>
    </div>
  </div>
</body>
</html>
"""
    body_text = f"Hello,\n\nYour Promptro password reset verification code is: {otp_code}\n\nThis code will expire in 5 minutes.\nIf you did not request a password reset, please ignore this email.\n\nBest regards,\nPromptro Team"

    try:
        send_email_background(email, email_subject, body_text, html_content)
    except Exception as e:
        db.delete(otp_record)
        db.commit()
        raise HTTPException(status_code=502, detail=f"Failed to send password reset OTP: {str(e)}")

    return {"status": "sent", "message": "OTP sent to your email"}


@app.post("/api/auth/forgot-password/verify-otp")
def forgot_password_verify_otp(body: schemas.OTPVerify, db: Session = Depends(get_db)):
    from datetime import datetime

    email = body.email.strip().lower()
    otp = body.otp.strip()

    if not otp or len(otp) != 6:
        raise HTTPException(status_code=400, detail="Invalid OTP format")

    # Find the latest unverified OTP for this email
    otp_record = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == email,
        models.PasswordResetOTP.otp_code == otp,
        models.PasswordResetOTP.verified == False
    ).order_by(models.PasswordResetOTP.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="Invalid OTP. Please check and try again.")

    # Check expiry
    if datetime.utcnow() > otp_record.expires_at.replace(tzinfo=None):
        raise HTTPException(status_code=400, detail="OTP has expired. Please request a new one.")

    # Mark as verified
    otp_record.verified = True
    db.commit()

    return {"status": "verified", "message": "OTP verified successfully. You can now reset your password."}


@app.post("/api/auth/forgot-password/reset-password")
def forgot_password_reset_password(body: schemas.PasswordReset, db: Session = Depends(get_db)):
    from datetime import datetime, timedelta

    email = body.email.strip().lower()
    otp = body.otp.strip()
    new_password = body.new_password

    if len(new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters long.")

    # Check that there is a verified OTP within the last 15 minutes
    otp_record = db.query(models.PasswordResetOTP).filter(
        models.PasswordResetOTP.email == email,
        models.PasswordResetOTP.otp_code == otp,
        models.PasswordResetOTP.verified == True,
        models.PasswordResetOTP.created_at >= datetime.utcnow() - timedelta(minutes=15)
    ).first()

    if not otp_record:
        raise HTTPException(status_code=400, detail="OTP verification not found or expired. Please verify OTP again.")

    # Firebase update password
    if not firebase_admin._apps:
        raise HTTPException(
            status_code=500,
            detail="Firebase Admin SDK is not configured."
        )

    try:
        firebase_user = firebase_auth.get_user_by_email(email)
        firebase_auth.update_user(firebase_user.uid, password=new_password)
    except firebase_auth.UserNotFoundError:
        raise HTTPException(status_code=404, detail="User not found in authentication system.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset password: {str(e)}")

    # Clean up OTP record
    db.delete(otp_record)
    db.commit()

    return {"status": "success", "message": "Password reset successfully!"}
