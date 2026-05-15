import requests

BASE_URL = "http://localhost:8000"

def update_banners():
    print("Updating Banners with better images and layout...")
    
    # First, get existing banners to find their IDs
    response = requests.get(f"{BASE_URL}/api/banners")
    if response.status_code != 200:
        print("Failed to fetch banners")
        return
    
    banners = response.json()
    
    # We'll just delete existing ones and re-create to ensure fresh state
    for b in banners:
        requests.delete(f"{BASE_URL}/api/banners/{b['id']}")
    
    new_banners = [
        {
            "tag_text": "TRENDING THIS WEEK",
            "tag_icon": "🔥",
            "title": "Most Loved Prompts",
            "subtitle": "Discover the top performing prompts loved by creators.",
            "button_text": "View Now >",
            "button_link": "/explore?filter=Trending",
            "bg_gradient": "from-[#ffedd5] to-[#fee2e2]", # Warm orange to soft red
            "image_url": "https://images.unsplash.com/photo-1620641788421-7a1c342ea42e?w=500&h=500&fit=crop",
            "is_active": True
        },
        {
            "tag_text": "NEW UPDATE",
            "tag_icon": "✨",
            "title": "Cinematic Style Pack Added!",
            "subtitle": "Create stunning cinematic images with new prompts.",
            "button_text": "Explore Now >",
            "button_link": "/explore?q=cinematic",
            "bg_gradient": "from-[#e0e7ff] to-[#f5f3ff]", # Soft indigo to light purple
            "image_url": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=500&h=500&fit=crop",
            "is_active": True
        }
    ]
    
    for banner in new_banners:
        requests.post(f"{BASE_URL}/api/banners", data=banner)
    
    print("Successfully updated banners!")

if __name__ == "__main__":
    update_banners()
