import requests

url = "http://127.0.0.1:8000/api/prompts"
files = {
    'image': ('test.jpg', b'fake image data', 'image/jpeg')
}
data = {
    'title': 'Test Title',
    'prompt_text': 'Test Prompt',
    'category': 'Sci-Fi',
    'model': 'Midjourney',
    'tags': 'tag1, tag2',
    'featured': 'true'
}

response = requests.post(url, data=data, files=files)
print(f"Status Code: {response.status_code}")
print(f"Response: {response.text}")
