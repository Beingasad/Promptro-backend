import sys
import os
sys.path.append(os.path.abspath("."))
import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from pathlib import Path

firebase_key_path = Path("firebase-service-account.json").resolve()
if not firebase_admin._apps:
    cred = credentials.Certificate(str(firebase_key_path))
    firebase_admin.initialize_app(cred)

print("Listing Firebase users...")
page = firebase_auth.list_users()
for user in page.users:
    print(f"UID: {user.uid}, Email: {user.email}, Provider: {[p.provider_id for p in user.provider_data]}")
