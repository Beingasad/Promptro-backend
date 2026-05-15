import requests
import os
BASE_URL = os.getenv("API_BASE_URL", "https://promptro-backend.onrender.com")

def update_banners_with_real_images():
    print("Fetching top prompts for banners...")
    try:
        response = requests.get(f"{BASE_URL}/api/prompts")
        if response.status_code != 200:
            print("Failed to fetch prompts")
            return
        
        # Sort by popularity (likes + views)
        prompts = sorted(response.json(), key=lambda x: x.get('likes', 0) + x.get('views', 0), reverse=True)
        
        if not prompts:
            print("No prompts found to use for banners.")
            return

        # Get top 2 images
        image1 = prompts[0]['image_url']
        image2 = prompts[1]['image_url'] if len(prompts) > 1 else image1
        
        # Clean up old banners
        old_banners = requests.get(f"{BASE_URL}/api/banners").json()
        for b in old_banners:
            requests.delete(f"{BASE_URL}/api/banners/{b['id']}")
            
        new_banners = [
            {
                "tag_text": "TRENDING THIS WEEK",
                "tag_icon": "🔥",
                "title": "Most Loved Prompts",
                "subtitle": "Discover the top performing prompts loved by creators.",
                "button_text": "View Now >",
                "button_link": "/explore?filter=Trending",
                "bg_gradient": "from-[#ffedd5] to-[#fee2e2]",
                "image_url": image1,
                "is_active": True
            },
            {
                "tag_text": "NEW UPDATE",
                "tag_icon": "✨",
                "title": "Cinematic Style Pack Added!",
                "subtitle": "Create stunning cinematic images with new prompts.",
                "button_text": "Explore Now >",
                "button_link": "/explore?q=cinematic",
                "bg_gradient": "from-[#e0e7ff] to-[#f5f3ff]",
                "image_url": image2,
                "is_active": True
            }
        ]
        
        for banner in new_banners:
            requests.post(f"{BASE_URL}/api/banners", data=banner)
            
        print(f"Successfully updated banners with images: {image1} and {image2}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_banners_with_real_images()
