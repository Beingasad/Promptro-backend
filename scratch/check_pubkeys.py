import urllib.request
import json

url = "https://www.googleapis.com/robot/v1/metadata/x509/firebase-adminsdk-fbsvc%40promptro-8e986.iam.gserviceaccount.com"
try:
    print("Fetching active public keys from Google...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=5) as response:
        certs = json.loads(response.read().decode())
        print("Active key IDs on Google:")
        for kid in certs.keys():
            print(f"- {kid}")
            
    print("\nOur local private_key_id is:")
    with open("firebase-service-account.json") as f:
        data = json.load(f)
        our_kid = data.get("private_key_id")
        print(f"- {our_kid}")
        
    if our_kid in certs:
        print("\nMatch found! The key is active on Google's servers.")
    else:
        print("\nNo match! The local key ID does NOT match any active key on Google's servers.")
except Exception as e:
    print("Error:", e)
