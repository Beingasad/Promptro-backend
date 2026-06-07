import urllib.request
import urllib.error
import json
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
db_path = BASE_DIR / "promptro.db"
LOCAL_URL = "http://127.0.0.1:8000"

TEST_UID_1 = "test_update_uid_1"
TEST_UID_2 = "test_update_uid_2"
TEST_EMAIL_1 = "test_update_1@promptro.in"
TEST_EMAIL_2 = "test_update_2@promptro.in"

def api_request(path, method="GET", payload=None):
    url = f"{LOCAL_URL}{path}"
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
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
print("  TESTING PROFILE UPDATE PUT ROUTE & USERNAME UNIQUE")
print("=======================================================")

# Ensure local test database cleanup first
def db_cleanup():
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("DELETE FROM user_profiles WHERE firebase_uid IN (?, ?)", (TEST_UID_1, TEST_UID_2))
        conn.commit()
        conn.close()

db_cleanup()

# Step 1: Register Test User 1
print("\nStep 1: Registering Test User 1...")
status, body = api_request("/api/auth/register-profile", method="POST", payload={
    "firebase_uid": TEST_UID_1,
    "first_name": "InitialName",
    "last_name": "InitialLast",
    "email": TEST_EMAIL_1,
    "provider": "email",
    "terms_accepted": True
})
print(f"Status: {status}, Response: {body}")
assert status == 200, "Registration failed"

# Step 2: Register Test User 2
print("\nStep 2: Registering Test User 2...")
status, body = api_request("/api/auth/register-profile", method="POST", payload={
    "firebase_uid": TEST_UID_2,
    "first_name": "SecondName",
    "last_name": "SecondLast",
    "email": TEST_EMAIL_2,
    "provider": "email",
    "terms_accepted": True
})
print(f"Status: {status}, Response: {body}")
assert status == 200, "Registration failed"

# Step 3: Update Profile of User 1 (Setting first name, last name, username, gender)
print("\nStep 3: Updating Profile of User 1...")
status, profile = api_request(f"/api/auth/profile/{TEST_UID_1}", method="PUT", payload={
    "first_name": "UpdatedFirst",
    "last_name": "UpdatedLast",
    "username": "superstar_dev",
    "gender": "Male"
})
print(f"Status: {status}, Response: {profile}")
assert status == 200, "Profile update failed"
assert profile["first_name"] == "UpdatedFirst"
assert profile["last_name"] == "UpdatedLast"
assert profile["username"] == "superstar_dev"
assert profile["gender"] == "Male"
print("[SUCCESS] Profile fields updated successfully.")

# Step 4: Verify username uniqueness check (Update User 2 to use the same username)
print("\nStep 4: Attempting to update User 2 to the same username 'superstar_dev'...")
status, body = api_request(f"/api/auth/profile/{TEST_UID_2}", method="PUT", payload={
    "first_name": "SecondName",
    "username": "superstar_dev"
})
print(f"Status: {status}, Response: {body}")
assert status == 400, f"Expected 400 Bad Request, got {status}"
assert "Username is already taken" in body.get("detail", ""), "Expected duplicate username error detail"
print("[SUCCESS] Username uniqueness validator works successfully (400 Bad Request returned).")

# Step 5: Update User 2 with a different username
print("\nStep 5: Updating User 2 with a unique username...")
status, profile = api_request(f"/api/auth/profile/{TEST_UID_2}", method="PUT", payload={
    "first_name": "SecondName",
    "username": "unique_ninja_coder"
})
print(f"Status: {status}, Response: {profile}")
assert status == 200, "Profile update failed with unique username"
assert profile["username"] == "unique_ninja_coder"
print("[SUCCESS] Unique username set for User 2.")

# Step 6: Cleanup
print("\nStep 6: Cleaning up test users...")
status1, _ = api_request(f"/api/admin/users/{TEST_UID_1}", method="DELETE")
status2, _ = api_request(f"/api/admin/users/{TEST_UID_2}", method="DELETE")
print(f"Cleanup Statuses: {status1}, {status2}")

print("\n=======================================================")
print("  SUCCESS: ALL PROFILE UPDATE PUT ROUTE TESTS PASSED!")
print("=======================================================")
