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

    print("\n2. Submitting mood logs for BOTH users to trigger ML prediction...")
    requests.post(f"{BASE_URL}/logs", json={
        "user_id": user_a_id, "logged_at": today_str, "score": 2, "emotion_tags": ["Sad"], "journal_text": "A terrible day."
    })
    
    # Slight delay to ensure response_lag is captured and background task finishes
    time.sleep(2)
    
    requests.post(f"{BASE_URL}/logs", json={
        "user_id": user_b_id, "logged_at": today_str, "score": 3, "emotion_tags": ["Stressed"], "journal_text": "I feel completely overwhelmed."
    })

    # Wait for the background ML task to complete
    print("\n3. Waiting 3 seconds for ML prediction background task...")
    time.sleep(3)

    print("\n4. Testing GET /risk/current endpoint...")
    res_risk = requests.get(f"{BASE_URL}/risk/current?user_id={user_a_id}")
    if res_risk.status_code != 200:
        print("❌ Failed to fetch risk score.", res_risk.text)
        sys.exit(1)
        
    risk_data = res_risk.json()
    print(f"Risk JSON Response:\n{risk_data}")
    
    if "p_stress" not in risk_data:
        print("❌ ML p_stress property is missing!")
        sys.exit(1)
        
    print(f"Computed Risk Score (p_stress): {risk_data['p_stress']}")
    print(f"Features Snapshot: {risk_data['features_snapshot']}")
    print(f"Suggestion Triggered: {risk_data['suggestion_triggered']}")
    print(f"Suggestion Tier: {risk_data['suggestion_tier']}")
    
    print("\n5. Testing GET /dashboard integration...")
    res_dash = requests.get(f"{BASE_URL}/dashboard?user_id={user_a_id}")
    dash_data = res_dash.json()
    if "risk_score" not in dash_data or dash_data["risk_score"] == 0.0:
        print("❌ Dashboard risk score missing or still using placeholder 0.0")
        sys.exit(1)
        
    if "features_snapshot" not in dash_data:
        print("❌ Dashboard feature snapshot missing!")
        sys.exit(1)
        
    print("✅ SUCCESS: ML Predictor is correctly generating features, predicting risk, and integrating with dashboard endpoints.")

if __name__ == "__main__":
    time.sleep(2)
    run_verification()
