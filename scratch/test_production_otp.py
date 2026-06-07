import urllib.request
import json

url = "https://promptro-backend.onrender.com/api/auth/send-otp"
payload = {
    "email": "testsignup123@gmail.com"
}
headers = {
    "Content-Type": "application/json"
}

req = urllib.request.Request(
    url, 
    data=json.dumps(payload).encode('utf-8'), 
    headers=headers, 
    method='POST'
)

print(f"Sending request to: {url}...")
try:
    with urllib.request.urlopen(req, timeout=15) as response:
        print("Success!")
        print("Status Code:", response.status)
        print("Body:", response.read().decode('utf-8'))
except urllib.error.HTTPError as e:
    print("HTTP Error:", e.code, e.reason)
    print("Body:", e.read().decode('utf-8'))
except Exception as e:
    print("Error:", e)
