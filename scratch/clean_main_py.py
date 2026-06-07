from pathlib import Path

main_py_path = Path(__file__).resolve().parent.parent / "app" / "main.py"
content = main_py_path.read_text(encoding="utf-8")

# Let's find the exact endpoints in order.
# We want to replace the segment from @app.patch("/api/auth/profile/{firebase_uid}/verify-email") (first occurrence)
# down to # --- ADMIN USER MANAGEMENT ENDPOINTS --- with clean implementations.

start_marker = '@app.patch("/api/auth/profile/{firebase_uid}/verify-email")'
end_marker = '# --- ADMIN USER MANAGEMENT ENDPOINTS ---'

start_idx = content.find(start_marker)
end_idx = content.find(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Error: Markers not found. start_idx={start_idx}, end_idx={end_idx}")
    exit(1)

# The correct implementations of verify_user_email and check_email:
replacement_code = """@app.patch("/api/auth/profile/{firebase_uid}/verify-email")
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


"""

new_content = content[:start_idx] + replacement_code + content[end_idx:]
main_py_path.write_text(new_content, encoding="utf-8")
print("Successfully cleaned main.py!")
