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

email = "aiaia07518@gmail.com"
try:
    print(f"Attempting to generate reset link for: {email}...")
    link = firebase_auth.generate_password_reset_link(email)
    print("Link generated successfully:", link)
except Exception as e:
    print("Error details:")
    print(type(e), str(e))
