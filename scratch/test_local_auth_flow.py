import urllib.request
import urllib.error
import json
import sqlite3
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"

LOCAL_URL = "http://127.0.0.1:8000"
TEST_EMAIL = "test_local_flow@promptro.in"
TEST_UID = "test_local_firebase_uid_12345"

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
print("  STARTING LOCAL AUTHENTICATION AND OTP FLOW TEST")
print("=======================================================")

# Step 1: Send OTP
print("\nStep 1: Sending OTP request to local backend...")
status, body = api_request("/api/auth/send-otp", method="POST", payload={"email": TEST_EMAIL})
print(f"Status: {status}, Response: {body}")
if status != 200:
    print("[ERROR] Failed to send OTP request. Aborting.")
    exit(1)

# Step 2: Fetch OTP from local SQLite database
print("\nStep 2: Fetching OTP code from local SQLite database...")
if not db_path.exists():
    print(f"[ERROR] Database not found at {db_path}!")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute(
    "SELECT otp_code FROM otp_verifications WHERE email = ? AND verified = 0 ORDER BY created_at DESC LIMIT 1",
    (TEST_EMAIL,)
)
row = cur.fetchone()
conn.close()

if not row:
    print("[ERROR] Could not find OTP record in SQLite database!")
    exit(1)

otp_code = row[0]
print(f"Successfully retrieved OTP from DB: {otp_code}")

# Step 3: Verify OTP
print(f"\nStep 3: Verifying OTP ({otp_code}) via API...")
status, body = api_request("/api/auth/verify-otp", method="POST", payload={
    "email": TEST_EMAIL,
    "otp": otp_code
})
print(f"Status: {status}, Response: {body}")
if status != 200 or body.get("status") != "verified":
    print("[ERROR] OTP Verification failed!")
    exit(1)

# Step 4: Register Profile
print("\nStep 4: Registering user profile via API...")
status, body = api_request("/api/auth/register-profile", method="POST", payload={
    "firebase_uid": TEST_UID,
    "first_name": "John",
    "last_name": "Doe",
    "gender": "Male",
    "email": TEST_EMAIL,
    "provider": "email",
    "terms_accepted": True
})
print(f"Status: {status}, Response: {body}")
if status != 200:
    print("[ERROR] Profile registration failed!")
    exit(1)

# Step 5: Get Profile and check fields
print("\nStep 5: Retrieving profile via API...")
status, profile = api_request(f"/api/auth/profile/{TEST_UID}")
print(f"Status: {status}, Response: {profile}")
if status != 200:
    print("[ERROR] Could not retrieve user profile!")
    exit(1)

# Check all fields
print("\nVerifying user profile fields correctness:")
assert profile["first_name"] == "John", f"Expected 'John', got {profile['first_name']}"
assert profile["last_name"] == "Doe", f"Expected 'Doe', got {profile['last_name']}"
assert profile["email"] == TEST_EMAIL, f"Expected {TEST_EMAIL}, got {profile['email']}"
assert profile["email_verified"] is False, f"Expected email_verified to be False, got {profile['email_verified']}"
assert profile["terms_accepted"] is True, f"Expected terms_accepted to be True, got {profile['terms_accepted']}"
print("[SUCCESS] All user profile fields are correct!")

# Step 6: Verify User Email
print("\nStep 6: Verifying email via API...")
status, body = api_request(f"/api/auth/profile/{TEST_UID}/verify-email", method="PATCH")
print(f"Status: {status}, Response: {body}")
if status != 200 or body.get("email_verified") is not True:
    print("[ERROR] Email verification API failed!")
    exit(1)

# Step 7: Get Profile again and verify email_verified is True
print("\nStep 7: Checking profile again to verify email_verified field is updated...")
status, profile = api_request(f"/api/auth/profile/{TEST_UID}")
print(f"Status: {status}, Response: {profile}")
assert profile["email_verified"] is True, f"Expected email_verified to be True, got {profile['email_verified']}"
print("[SUCCESS] Email verified field is updated successfully in DB!")

# Step 8: Cleanup - Delete Admin User
print("\nStep 8: Cleaning up test user profile via Admin API...")
status, body = api_request(f"/api/admin/users/{TEST_UID}", method="DELETE")
print(f"Status: {status}, Response: {body}")
if status != 200:
    print("[ERROR] Cleanup failed!")
    exit(1)

print("\n=======================================================")
print("  SUCCESS: ALL TESTS PASSED SUCCESSFULLY! AUTH & OTP FLOW OK!")
print("=======================================================")
