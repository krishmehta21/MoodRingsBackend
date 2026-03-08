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

    res_a = requests.post(f"{BASE_URL}/auth/generate-code?user_id={user_a_id}").json()
    code = res_a.get("invite_code")
    requests.post(f"{BASE_URL}/auth/link", json={"invite_code": code, "user_id": user_b_id})

    today_str = datetime.now().strftime("%Y-%m-%d")

    print("\n2. Submitting mood logs for both users...")
    requests.post(f"{BASE_URL}/logs", json={
        "user_id": user_a_id, "logged_at": today_str, "score": 8, "emotion_tags": ["Happy"]
    })
    
    # Slight delay to ensure response_lag_hours captures a difference
    time.sleep(2)
    
    requests.post(f"{BASE_URL}/logs", json={
        "user_id": user_b_id, "logged_at": today_str, "score": 4, "emotion_tags": ["Stressed"]
    })

    print("\n3. Testing GET /dashboard endpoint...")
    res_dash = requests.get(f"{BASE_URL}/dashboard?user_id={user_a_id}")
    if res_dash.status_code != 200:
        print("❌ Failed to fetch dashboard.", res_dash.text)
        sys.exit(1)
        
    data = res_dash.json()
    
    print(f"Dashboard JSON Response:\n{data}")
    
    if "risk_score" not in data or data["risk_score"] != 0.0:
        print("❌ ML Risk score placeholder is missing or not 0.0")
        sys.exit(1)
        
    if "response_lag_hours" not in data or data["response_lag_hours"] is None:
        print("❌ response_lag_hours calculation is missing.")
        sys.exit(1)
        
    me = data.get("me", {})
    partner = data.get("partner", {})
    
    if not me.get("today_logged") or not partner.get("today_logged"):
        print("❌ today_logged status is incorrect.")
        sys.exit(1)
        
    if me.get("streak") != 1 or partner.get("streak") != 1:
        print("❌ Streak calculation is incorrect (expected 1).")
        sys.exit(1)
        
    print("✅ SUCCESS: GET /dashboard endpoint returns the correct unified payload for Phase 3 UI wiring.")

if __name__ == "__main__":
    time.sleep(2)
    run_verification()
