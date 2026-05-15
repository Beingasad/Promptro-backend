import requests
import os
BASE_URL = os.getenv("API_BASE_URL", "https://promptro-backend.onrender.com")

def seed_banners():
    print("Seeding Banners...")
    
    banners = [
        {
            "tag_text": "+ NEW UPDATE",
            "tag_icon": "✨",
            "title": "Cinematic Style Pack Added!",
            "subtitle": "Create stunning cinematic images with new prompts.",
            "button_text": "Explore Now >",
            "button_link": "/explore?q=cinematic",
            "bg_gradient": "from-[#e0e7ff] to-[#ede9fe]",
            "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=400&h=400&fit=crop",
            "is_active": True
        },
        {
            "tag_text": "🔥 TRENDING THIS WEEK",
            "tag_icon": "🔥",
            "title": "Most Loved Prompts ❤️",
            "subtitle": "Discover the top performing prompts loved by creators.",
            "button_text": "View Now >",
            "button_link": "/explore?filter=Trending",
            "bg_gradient": "from-[#ffedd5] to-[#fce7f3]",
            "image_url": "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?w=400&h=400&fit=crop",
            "is_active": True
        }
    ]
    
    for banner in banners:
        try:
            # We use data= because we're sending form data as expected by the backend
            response = requests.post(f"{BASE_URL}/api/banners", data=banner)
            if response.status_code == 200:
                print(f"Created banner: {banner['title']}")
            else:
                print(f"Failed to create banner: {response.text}")
        except Exception as e:
            print(f"Error creating banner: {e}")

if __name__ == "__main__":
    seed_banners()
