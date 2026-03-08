import requests
import time
import uuid
import sys
from datetime import datetime

BASE_URL = "http://localhost:8001"

def run_verification():
    print("1. Creating test users and linking...")
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())

    # Create & Get code for User A
    res_a = requests.post(f"{BASE_URL}/auth/generate-code?user_id={user_a_id}").json()
    code = res_a.get("invite_code")
    
    # Link B to A
    res_link = requests.post(f"{BASE_URL}/auth/link", json={"invite_code": code, "user_id": user_b_id})
    if res_link.status_code != 200:
        print("❌ Failed to link users.", res_link.text)
        sys.exit(1)
    print(f"✅ Users linked: A({user_a_id}) <-> B({user_b_id})")

    today_str = datetime.now().strftime("%Y-%m-%d")

    print("\n2. Submitting mood logs for both users...")
    log_a = {
        "user_id": user_a_id,
        "logged_at": today_str,
        "score": 8,
        "emotion_tags": ["Happy", "Calm"],
        "journal_text": "I had a really wonderful day today!"
    }
    
    log_b = {
        "user_id": user_b_id,
        "logged_at": today_str,
        "score": 4,
        "emotion_tags": ["Stressed", "Tired"],
        "journal_text": "Work was extremely overwhelming, I need some rest."
    }

    res_log_a = requests.post(f"{BASE_URL}/logs", json=log_a)
    res_log_b = requests.post(f"{BASE_URL}/logs", json=log_b)

    if res_log_a.status_code != 200 or res_log_b.status_code != 200:
        print("❌ Failed to create mood logs.")
        print(res_log_a.text)
        print(res_log_b.text)
        sys.exit(1)
        
    print("✅ Mood logs submitted successfully.")

    print("\n3. Testing 409 UNIQUE constraint on POST /logs...")
    res_log_a_dup = requests.post(f"{BASE_URL}/logs", json=log_a)
    if res_log_a_dup.status_code == 409 and "You have already logged today" in res_log_a_dup.text:
        print("✅ Correctly rejected duplicate log with 409.")
    else:
        print(f"❌ Failed to reject duplicate log. Status: {res_log_a_dup.status_code}, Text: {res_log_a_dup.text}")
        sys.exit(1)

    print("\n4. Testing Privacy Boundary on GET /logs/couple as User A...")
    res_couple = requests.get(f"{BASE_URL}/logs/couple?user_id={user_a_id}")
    if res_couple.status_code != 200:
        print("❌ Failed to fetch couple logs.", res_couple.text)
        sys.exit(1)
        
    data = res_couple.json()
    partner_logs = data.get("partner", [])
    
    if len(partner_logs) == 0:
        print("❌ Partner logs are unexpectedly empty.")
        sys.exit(1)
        
    p_log = partner_logs[0]
    print(f"Partner Log JSON Response:\n{p_log}")
    
    if "journal_text" in p_log:
        print("❌ SECURITY FAILURE: journal_text field is present in partner logs!")
        sys.exit(1)
    else:
        print("✅ SUCCESS: journal_text is completely absent from partner's record.")

    my_logs = data.get("me", [])
    if my_logs and "journal_text" in my_logs[0]:
        print("✅ SUCCESS: Own journal_text is correctly present and decrypted!")
    else:
        print("❌ FAILURE: Own journal_text is missing or corrupted!")
        sys.exit(1)
        
    print("\nAll Backend Phase 2 scenarios passed!")

if __name__ == "__main__":
    time.sleep(2)
    run_verification()
