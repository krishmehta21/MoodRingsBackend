
import requests
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8001"

def test_patterns():
    print("--- Pattern Detection E2E Test ---")
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    
    # 1. Link users
    print("Linking users...")
    res = requests.post(f"{BASE_URL}/auth/generate-code?user_id={user_a}").json()
    code = res['invite_code']
    requests.post(f"{BASE_URL}/auth/link", json={"invite_code": code, "user_id": user_b})
    
    # 2. Populate logs for the last 7 days (Sundays are low)
    print("Populating 7 days of logs...")
    today = datetime.now()
    for i in range(7):
        log_date = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        weekday = (today - timedelta(days=i)).weekday()
        
        # Sundays = 6. Let's make it tough for both.
        score = 2 if weekday == 6 else 8
        
        requests.post(f"{BASE_URL}/logs", json={
            "user_id": user_a, "score": score, "logged_at": log_date, "emotion_tags": ["Test"]
        })
        requests.post(f"{BASE_URL}/logs", json={
            "user_id": user_b, "score": score, "logged_at": log_date, "emotion_tags": ["Test"]
        })
        
    # 3. Hit patterns endpoint
    print("Fetching patterns...")
    res_p = requests.get(f"{BASE_URL}/insights/patterns?user_id={user_a}").json()
    print(f"Patterns Response: {res_p}")
    
    if len(res_p) > 0:
        print("✅ SUCCESS: Patterns detected.")
    else:
        print("❌ FAIL: No patterns detected.")

if __name__ == "__main__":
    test_patterns()
