import requests
import time
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"

def prep_demo():
    print("Prepping Demo User...")
    user_id = str(uuid.uuid4())
    partner_id = str(uuid.uuid4())

    # 1. Generate invite code for Demo User and link partner
    res_a = requests.post(f"{BASE_URL}/auth/generate-code?user_id={user_id}").json()
    code = res_a.get("invite_code")
    requests.post(f"{BASE_URL}/auth/link", json={"invite_code": code, "user_id": partner_id})
    
    print(f"DEMO_USER_ID: {user_id}")
    print(f"PARTNER_ID: {partner_id}")

    # 2. Add some logs to trigger high stress for User A
    print("Generating stressed history...")
    for i in range(10, 1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        requests.post(f"{BASE_URL}/logs", json={
            "user_id": user_id,
            "logged_at": day,
            "score": 3, # low mood
            "emotion_tags": ["Stressed", "Tired"],
            "journal_text": "Work is piling up. Feeling overwhelmed."
        })
        requests.post(f"{BASE_URL}/logs", json={
            "user_id": partner_id,
            "logged_at": day,
            "score": 8, # high mood (divergent)
            "emotion_tags": ["Happy"],
            "journal_text": "Had a great day."
        })

    # Today logs
    today = datetime.now().strftime("%Y-%m-%d")
    requests.post(f"{BASE_URL}/logs", json={
        "user_id": user_id, "logged_at": today, "score": 2,
        "emotion_tags": ["Anxious"], "journal_text": "Very stressed right now."
    })
    
    # Trigger risk calculation
    print("Calculating risk...")
    time.sleep(2)
    res_risk = requests.get(f"{BASE_URL}/risk/current?user_id={user_id}").json()
    print(f"Stress Probability: {res_risk.get('p_stress', 'N/A')}")
    
    # Force a suggestion for the demo
    print("Forcing suggestion...")
    res_sug = requests.get(f"{BASE_URL}/suggestions?user_id={user_id}").json()
    print(f"Suggestion: {res_sug.get('message', 'None')}")

if __name__ == "__main__":
    prep_demo()
