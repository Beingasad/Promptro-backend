import sys
import os
import urllib.request
import urllib.error
import json
import sqlite3
from pathlib import Path

# Add parent directory to path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"

LOCAL_URL = "http://127.0.0.1:8000"
TEST_EMAIL = "test_forgot_pwd@promptro.in"

# 1. Initialize Firebase Admin in script if not already initialized
if not firebase_admin._apps:
    firebase_key_path = BASE_DIR / "backend" / "firebase-service-account.json"
    if firebase_key_path.exists():
        cred = credentials.Certificate(str(firebase_key_path))
        firebase_admin.initialize_app(cred)
        print("Firebase Admin SDK initialized in test script!")
    else:
        print("Error: firebase-service-account.json not found. Cannot run integration test.")
        exit(1)

def api_request(path, method="GET", payload=None):
    url = f"{LOCAL_URL}{path}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status, json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        try:
            return e.code, json.loads(body)
        except:
            return e.code, body
    except Exception as e:
        return 0, str(e)

print("=======================================================")
print("  STARTING FORGOT PASSWORD OTP-BASED INTEGRATION TEST")
print("=======================================================")

# Step 1: Clean up and recreate test user in Firebase Auth and SQLite
print("\nStep 1: Preparing clean environment for test user...")
try:
    existing_fb_user = firebase_auth.get_user_by_email(TEST_EMAIL)
    firebase_auth.delete_user(existing_fb_user.uid)
    print(f"Deleted existing Firebase user: {TEST_EMAIL}")
except firebase_auth.UserNotFoundError:
    pass

# Delete from SQLite user_profiles
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("DELETE FROM user_profiles WHERE email = ?", (TEST_EMAIL,))
cur.execute("DELETE FROM password_reset_otps WHERE email = ?", (TEST_EMAIL,))
conn.commit()
conn.close()

# Create Firebase User
fb_user = firebase_auth.create_user(
    email=TEST_EMAIL,
    password="oldpassword123",
    display_name="Forgot Pwd Test"
)
print(f"Created Firebase user: {fb_user.uid} with email {TEST_EMAIL}")

# Create Profile in SQLite
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute(
    """
    INSERT INTO user_profiles (firebase_uid, first_name, last_name, email, provider, terms_accepted, email_verified)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
    (fb_user.uid, "Forgot", "Test", TEST_EMAIL, "email", 1, 1)
)
conn.commit()
conn.close()
print("Created SQLite user profile record.")

# Step 2: Send OTP for Forgot Password
print("\nStep 2: Triggering Forgot Password Send OTP...")
status, body = api_request("/api/auth/forgot-password/send-otp", method="POST", payload={"email": TEST_EMAIL})
print(f"Status: {status}, Response: {body}")
if status != 200:
    print("[ERROR] Failed to trigger send-otp!")
    exit(1)

# Step 3: Fetch OTP from SQLite password_reset_otps table
print("\nStep 3: Fetching OTP from SQLite password_reset_otps table...")
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute(
    "SELECT otp_code FROM password_reset_otps WHERE email = ? AND verified = 0 ORDER BY created_at DESC LIMIT 1",
    (TEST_EMAIL,)
)
row = cur.fetchone()
conn.close()

if not row:
    print("[ERROR] OTP record not found in password_reset_otps table!")
    exit(1)

otp_code = row[0]
print(f"Retrieved OTP code: {otp_code}")

# Step 4: Verify OTP
print(f"\nStep 4: Verifying OTP ({otp_code}) via API...")
status, body = api_request("/api/auth/forgot-password/verify-otp", method="POST", payload={
    "email": TEST_EMAIL,
    "otp": otp_code
})
print(f"Status: {status}, Response: {body}")
if status != 200 or body.get("status") != "verified":
    print("[ERROR] OTP Verification failed!")
    exit(1)

# Step 5: Reset Password with incorrect OTP (Should Fail)
print("\nStep 5: Resetting password with invalid OTP (should fail)...")
status, body = api_request("/api/auth/forgot-password/reset-password", method="POST", payload={
    "email": TEST_EMAIL,
    "otp": "000000",
    "new_password": "newpassword123"
})
print(f"Status: {status}, Response: {body}")
if status == 200:
    print("[ERROR] Password reset succeeded with invalid OTP! Security issue!")
    exit(1)
print("Invalid OTP check passed! (failed as expected)")

# Step 6: Reset Password with correct OTP (Should Succeed)
print("\nStep 6: Resetting password with correct OTP...")
status, body = api_request("/api/auth/forgot-password/reset-password", method="POST", payload={
    "email": TEST_EMAIL,
    "otp": otp_code,
    "new_password": "newpassword123"
})
print(f"Status: {status}, Response: {body}")
if status != 200 or body.get("status") != "success":
    print("[ERROR] Password reset failed!")
    exit(1)
print("Password reset successful!")

# Step 7: Clean up test records
print("\nStep 7: Cleaning up test records...")
try:
    firebase_auth.delete_user(fb_user.uid)
    print("Deleted test user from Firebase Auth.")
except Exception as e:
    print(f"Warning: Failed to delete Firebase user: {e}")

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("DELETE FROM user_profiles WHERE email = ?", (TEST_EMAIL,))
cur.execute("DELETE FROM password_reset_otps WHERE email = ?", (TEST_EMAIL,))
conn.commit()
conn.close()
print("Deleted test user profile and OTPs from SQLite.")

print("\n=======================================================")
print("  SUCCESS: FORGOT PASSWORD FLOW TEST PASSED COMPLETELY!")
print("=======================================================")
