import os
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()

resend_api_key = os.getenv("RESEND_API_KEY")
print("RESEND_API_KEY:", resend_api_key)

url = "https://api.resend.com/emails"
headers = {
    "Authorization": f"Bearer {resend_api_key}",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

recipient = "asadansari07518@gmail.com"
print(f"Sending test email to: {recipient}...")

payload = {
    "from": "Promptro <onboarding@resend.dev>",
    "to": [recipient],
    "subject": "Resend API Test Connection",
    "text": "Hello! If you are reading this, your Resend API integration is working perfectly."
}

req = urllib.request.Request(
    url, 
    data=json.dumps(payload).encode('utf-8'), 
    headers=headers, 
    method='POST'
)
try:
    with urllib.request.urlopen(req, timeout=10) as response:
        res_body = response.read().decode('utf-8')
        print("\nSUCCESS: Test email sent via Resend!")
        print("Response:", res_body)
except urllib.error.HTTPError as e:
    print("\nHTTP Error:", e.code, e.reason)
    print("Body:", e.read().decode('utf-8'))
except Exception as e:
    print("\nError:", e)
