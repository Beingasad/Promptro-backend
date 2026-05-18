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

class FeedbackOut(FeedbackCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

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
