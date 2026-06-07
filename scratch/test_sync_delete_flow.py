import urllib.request
import urllib.error
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"

LOCAL_URL = "http://127.0.0.1:8000"
TEST_EMAIL = "sync_delete_test@promptro.in"
TEST_UID = "sync_delete_firebase_uid_9999"

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

def check_db_exists(uid):
    if not db_path.exists():
        return False
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id FROM user_profiles WHERE firebase_uid = ?", (uid,))
    row = cur.fetchone()
    conn.close()
    return row is not None

print("=======================================================")
print("  STARTING SYNC & DELETE FLOW VERIFICATION TEST")
print("=======================================================")

# Step 1: Pre-cleanup if exists
print("\nStep 1: Making sure test profile is clean before starting...")
status, body = api_request(f"/api/admin/users/{TEST_UID}", method="DELETE")
if status == 200:
    print("Found and deleted existing test profile.")
else:
    print("Test profile is already clean.")

# Step 2: Register user profile
print("\nStep 2: Registering profile in database...")
status, body = api_request("/api/auth/register-profile", method="POST", payload={
    "firebase_uid": TEST_UID,
    "first_name": "SyncTest",
    "last_name": "User",
    "gender": "Other",
    "email": TEST_EMAIL,
    "provider": "email",
    "terms_accepted": True
})
print(f"Status: {status}, Response: {body}")
assert status == 200, "Failed to register profile"

# Step 3: Check database has user_profiles entry
print("\nStep 3: Checking SQLite DB directly...")
db_exists = check_db_exists(TEST_UID)
print(f"User profile exists in DB: {db_exists}")
assert db_exists is True, "User profile should exist in DB"

# Step 4: Verify email_verified is false initially
status, profile = api_request(f"/api/auth/profile/{TEST_UID}")
print(f"Initial profile: {profile}")
assert profile["email_verified"] is False, "email_verified should be False initially"

# Step 5: Test PATCH to verify-email (to simulate the auto-sync)
print("\nStep 5: Testing patch to verify-email...")
status, body = api_request(f"/api/auth/profile/{TEST_UID}/verify-email", method="PATCH")
print(f"Status: {status}, Response: {body}")
assert status == 200 and body.get("email_verified") is True

# Step 6: Verify email_verified is now True
status, profile = api_request(f"/api/auth/profile/{TEST_UID}")
print(f"Profile after verification: {profile}")
assert profile["email_verified"] is True, "email_verified should now be True"

# Step 7: Delete user (simulates account deletion)
print("\nStep 7: Testing database deletion API...")
status, body = api_request(f"/api/admin/users/{TEST_UID}", method="DELETE")
print(f"Status: {status}, Response: {body}")
assert status == 200, "Failed to delete user profile from DB"

# Step 8: Verify DB profile is removed
print("\nStep 8: Checking SQLite DB again...")
db_exists = check_db_exists(TEST_UID)
print(f"User profile exists in DB after delete: {db_exists}")
assert db_exists is False, "User profile should be deleted from DB"

# Step 9: Verify profile get API returns 404
status, body = api_request(f"/api/auth/profile/{TEST_UID}")
print(f"Profile GET status after deletion: {status}")
assert status == 404, f"Expected 404, got {status}"

# Step 10: Re-register profile with same email (simulates sign-up again after deletion)
print("\nStep 10: Registering profile again (simulating re-signup)...")
status, body = api_request("/api/auth/register-profile", method="POST", payload={
    "firebase_uid": TEST_UID,
    "first_name": "SyncTest",
    "last_name": "User",
    "gender": "Other",
    "email": TEST_EMAIL,
    "provider": "email",
    "terms_accepted": True
})
print(f"Status: {status}, Response: {body}")
assert status == 200, "Failed to register profile after delete"

# Cleanup
print("\nCleaning up...")
status, body = api_request(f"/api/admin/users/{TEST_UID}", method="DELETE")
print(f"Cleanup Status: {status}")

print("\n=======================================================")
print("  SUCCESS: SYNC & DELETE FLOW TESTS PASSED!")
print("=======================================================")
