import requests
import os
BASE_URL = os.getenv("API_BASE_URL", "https://promptro-backend.onrender.com")

def test_banners():
    print("Testing Banners API...")
    
    # 1. Create a banner
    banner_data = {
        "tag_text": "NEW UPDATE",
        "tag_icon": "Sparkles",
        "title": "Cinematic Style Pack Added!",
        "subtitle": "Create stunning cinematic images with new prompts.",
        "button_text": "Explore Now >",
        "button_link": "/categories/cinematic",
        "bg_gradient": "from-[#e0e7ff] to-[#ede9fe]",
        "is_active": True
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/banners", data=banner_data)
        if response.status_code == 200:
            print("Successfully created banner!")
            banner_id = response.json()['id']
        else:
            print(f"Failed to create banner: {response.text}")
            return
            
        # 2. Get all banners
        response = requests.get(f"{BASE_URL}/api/banners")
        if response.status_code == 200:
            banners = response.data = response.json()
            print(f"Retrieved {len(banners)} banners.")
        else:
            print(f"Failed to retrieve banners: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_banners()
