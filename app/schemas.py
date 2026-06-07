from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class PromptBase(BaseModel):
    title: str
    prompt_text: str
    negative_prompt: Optional[str] = None
    category: str
    tags: Optional[List[str]] = []
    model: str
    aspect_ratio: Optional[str] = None
    trending: Optional[bool] = False
    visibility: Optional[str] = "Public"

class PromptCreate(PromptBase):
    pass

class PromptUpdate(PromptBase):
    title: Optional[str] = None
    prompt_text: Optional[str] = None
    category: Optional[str] = None
    model: Optional[str] = None
    aspect_ratio: Optional[str] = None

class PromptOut(PromptBase):
    id: str
    image_url: str
    likes: int
    views: int
    featured: bool
    created_at: datetime

    class Config:
        from_attributes = True

class SavedPromptOut(BaseModel):
    id: str
    prompt_id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserActivityBase(BaseModel):
    saved_prompts: Optional[List[dict]] = []
    liked_prompts: Optional[List[str]] = []
    recent_prompts: Optional[List[dict]] = []

class UserActivityCreate(UserActivityBase):
    pass

class UserActivityOut(UserActivityBase):
    user_id: str
    updated_at: datetime

    class Config:
        from_attributes = True

class CategoryBase(BaseModel):
    name: str
    image_url: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryOut(CategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class FeedbackCreate(BaseModel):
    user: Optional[str] = "Guest"
    email: Optional[str] = "N/A"
    subject: Optional[str] = "General Feedback"
    message: str

class FeedbackOut(BaseModel):
    id: int
    user: Optional[str] = "Guest"
    email: Optional[str] = "N/A"
    subject: Optional[str] = "General Feedback"
    message: str
    status: str
    reply_text: Optional[str] = None
    replied_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class FeedbackStatusUpdate(BaseModel):
    status: str  # "unread" / "read" / "replied" / "resolved"

class FeedbackReply(BaseModel):
    reply_text: str

class BannerBase(BaseModel):
    tag_text: str
    tag_icon: Optional[str] = None
    title: str
    subtitle: str
    button_text: str
    button_link: str
    image_url: Optional[str] = None
    bg_gradient: str
    is_active: bool = True

class BannerCreate(BannerBase):
    pass

class BannerUpdate(BaseModel):
    tag_text: Optional[str] = None
    tag_icon: Optional[str] = None
    title: Optional[str] = None
    subtitle: Optional[str] = None
    button_text: Optional[str] = None
    button_link: Optional[str] = None
    image_url: Optional[str] = None
    bg_gradient: Optional[str] = None
    is_active: Optional[bool] = None

class BannerOut(BannerBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationCreate(BaseModel):
    text: str
    type: Optional[str] = "info"
    link: Optional[str] = "/explore"

class NotificationOut(NotificationCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

class PageVisitCreate(BaseModel):
    path: str
    referrer: Optional[str] = None

class AnalyticsSummary(BaseModel):
    totalVisits: int
    uniqueVisitors: int
    dailyVisits: List[int]
    trafficSources: List[dict]
    topLocation: Optional[str] = None


class ConsentAccept(BaseModel):
    user_id: str
    email: Optional[str] = None


class CookieConsentUpdate(BaseModel):
    user_id: Optional[str] = None
    status: str  # "accepted" / "rejected"


class ConsentStatusOut(BaseModel):
    user_id: str
    terms_accepted: bool
    terms_accepted_at: Optional[datetime] = None
    privacy_accepted_at: Optional[datetime] = None
    cookie_consent_status: str

    class Config:
        from_attributes = True


# --- OTP Auth Schemas ---

class OTPRequest(BaseModel):
    email: str

class OTPVerify(BaseModel):
    email: str
    otp: str

class UserProfileCreate(BaseModel):
    firebase_uid: str
    first_name: str
    last_name: Optional[str] = None
    gender: Optional[str] = None
    username: Optional[str] = None
    email: str
    provider: Optional[str] = "email"
    terms_accepted: bool = False

class UserProfileOut(BaseModel):
    id: int
    firebase_uid: str
    first_name: str
    last_name: Optional[str] = None
    gender: Optional[str] = None
    username: Optional[str] = None
    email: str
    provider: str
    terms_accepted: bool
    terms_accepted_at: Optional[datetime] = None
    email_verified: bool
    created_at: datetime

    class Config:
        from_attributes = True

class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    gender: Optional[str] = None
    username: Optional[str] = None

class VerificationRequest(BaseModel):
    email: str
    firebase_uid: str


class ConfirmVerificationRequest(BaseModel):
    token: str


class PasswordReset(BaseModel):
    email: str
    otp: str
    new_password: str
