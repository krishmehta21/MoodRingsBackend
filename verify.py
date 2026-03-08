import requests
import time
import uuid
import sys

BASE_URL = "http://localhost:8001"

def run_verification():
    print("1. Testing Health Endpoint...")
    try:
        res = requests.get(f"{BASE_URL}/health")
        if res.json() == {"status": "ok"}:
            print("✅ Health check passed!")
        else:
            print("❌ Health check failed:", res.json())
            sys.exit(1)
    except Exception as e:
        print("❌ Could not connect to FastAPI:", e)
        sys.exit(1)

    print("\n2. Creating test users and simulating linking...")
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())

    print(f"User A ID: {user_a_id}")
    print(f"User B ID: {user_b_id}")

    # Generate invite code for User A
    res = requests.post(f"{BASE_URL}/auth/generate-code?user_id={user_a_id}")
    data = res.json()
    code = data.get("invite_code")
    print(f"User A generated invite code: {code}")

    if not code:
        print("❌ Failed to generate invite code:", data)
        sys.exit(1)

    # Link User B to User A using the invite code
    payload = {
        "invite_code": code,
        "user_id": user_b_id
    }
    res = requests.post(f"{BASE_URL}/auth/link", json=payload)
    if res.status_code == 200:
        print("Linking response:", res.json())
        print("✅ Partner linking endpoint successful!")
    else:
        print("❌ Partner linking failed!")
        print("Status Code:", res.status_code)
        print("Response:", res.text)
        sys.exit(1)

    print("\n3. Querying database directly to verify BOTH records show each other's partner_id...")
    # I will query the DB directly here
    import os
    import psycopg2
    # Standard connection from .env
    conn = psycopg2.connect("postgresql://postgres:password@localhost:5432/moodrings")
    cur = conn.cursor()
    
    cur.execute("SELECT id, email, partner_id, invite_code FROM users WHERE id IN (%s, %s)", (user_a_id, user_b_id))
    rows = cur.fetchall()
    
    print("\n--- DATABASE DUMP: USERS TABLE ---")
    print(f"{'ID':<38} | {'Email':<40} | {'Partner ID':<38} | {'Invite Code'}")
    print("-" * 135)
    
    for row in rows:
        print(f"{str(row[0]):<38} | {str(row[1]):<40} | {str(row[2]):<38} | {str(row[3])}")
    
    print("-" * 135)
    
    # Verify logic
    user_a = next(r for r in rows if str(r[0]) == user_a_id)
    user_b = next(r for r in rows if str(r[0]) == user_b_id)
    
    if str(user_a[2]) == user_b_id and str(user_b[2]) == user_a_id:
        print("✅ SUCCESS: Both users are correctly linked via partner_id!")
    else:
        print("❌ FAILURE: Partner IDs do not match!")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    # Wait for server to be ready
    time.sleep(2)
    run_verification()
