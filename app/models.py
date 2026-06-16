from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON
from sqlalchemy.sql import func
from app.database import Base

class Prompt(Base):
    __tablename__ = "prompts"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, index=True)
    image_url = Column(String)
    prompt_text = Column(Text)
    negative_prompt = Column(Text, nullable=True)
    category = Column(String, index=True)
    tags = Column(JSON, nullable=True)
    model = Column(String)
    likes = Column(Integer, default=0)
    views = Column(Integer, default=0)
    featured = Column(Boolean, default=False)
    trending = Column(Boolean, default=False)
    visibility = Column(String, default="Public")
    aspect_ratio = Column(String, nullable=True)
    images = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class SavedPrompt(Base):
    __tablename__ = "saved_prompts"

    id = Column(String, primary_key=True, index=True)
    prompt_id = Column(String, index=True)
    user_id = Column(String, index=True, default="local_user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class UserActivity(Base):
    __tablename__ = "user_activities"

    user_id = Column(String, primary_key=True, index=True)
    saved_prompts = Column(JSON, nullable=True, default=[])
    liked_prompts = Column(JSON, nullable=True, default=[])
    recent_prompts = Column(JSON, nullable=True, default=[])
    collections = Column(JSON, nullable=True, default=[])
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Feedback(Base):
    __tablename__ = "feedbacks"

    id = Column(Integer, primary_key=True, index=True)
    user = Column(String, default="Guest")
    email = Column(String, default="N/A")
    subject = Column(String, default="General Feedback")
    message = Column(Text)
    status = Column(String, default="unread")
    reply_text = Column(Text, nullable=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Banner(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, index=True)
    tag_text = Column(String)
    tag_icon = Column(String, nullable=True)
    title = Column(String)
    subtitle = Column(Text)
    button_text = Column(String)
    button_link = Column(String)
    image_url = Column(String)
    bg_gradient = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String)
    type = Column(String, default="info")
    link = Column(String, default="/explore")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PageVisit(Base):
    __tablename__ = "page_visits"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String, index=True)
    path = Column(String, index=True)
    referrer = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class IpLocationCache(Base):
    __tablename__ = "ip_location_cache"

    ip_address = Column(String, primary_key=True, index=True)
    country_name = Column(String, nullable=False)
    country_code = Column(String, nullable=True)


class UserConsent(Base):
    __tablename__ = "user_consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)  # Firebase UID
    email = Column(String, nullable=True)
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    privacy_accepted_at = Column(DateTime(timezone=True), nullable=True)
    cookie_consent_status = Column(String, default="pending")  # "accepted" / "rejected" / "pending"
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class OTPVerification(Base):
    __tablename__ = "otp_verifications"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    otp_code = Column(String)
    expires_at = Column(DateTime(timezone=True))
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PasswordResetOTP(Base):
    __tablename__ = "password_reset_otps"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    otp_code = Column(String)
    expires_at = Column(DateTime(timezone=True))
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String, unique=True, index=True)
    username = Column(String, unique=True, nullable=True, index=True)
    first_name = Column(String)
    last_name = Column(String, nullable=True)
    gender = Column(String, nullable=True)
    email = Column(String)
    provider = Column(String, default="email")  # "email" or "google"
    terms_accepted = Column(Boolean, default=False)
    terms_accepted_at = Column(DateTime(timezone=True), nullable=True)
    email_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, index=True)
    token = Column(String, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True))
    verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
