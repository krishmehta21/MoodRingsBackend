import requests
import time
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://127.0.0.1:8000"

def run_verification():
    print("1. Creating test users and linking...")
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())

    # Generate invite code for user A and link user B
    res_a = requests.post(f"{BASE_URL}/auth/generate-code?user_id={user_a_id}").json()
    code = res_a.get("invite_code")
    requests.post(f"{BASE_URL}/auth/link", json={"invite_code": code, "user_id": user_b_id})

    # Create 7 days of logs with strong divergence and overlapping low days
    print("\n2. Submitting divergent mood logs over 7 days to trigger high stress...")
    for i in range(7, 0, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        
        # Days 3, 2, 1: both partners low (2) to increase low_score_overlap
        if i <= 3:
            a_score = 2
            b_score = 2
        else:
            # Remaining days: user A high (9), user B low (2)
            a_score = 9
            b_score = 2
            
        requests.post(f"{BASE_URL}/logs", json={
            "user_id": user_a_id,
            "logged_at": day,
            "score": a_score,
            "emotion_tags": ["Happy" if a_score > 5 else "Sad"],
            "journal_text": "Feeling great today." if a_score > 5 else "Feeling terrible today."
        })
        
        # User B: skip day 5 to break streak
        if i != 5:
            requests.post(f"{BASE_URL}/logs", json={
                "user_id": user_b_id,
                "logged_at": day,
                "score": b_score,
                "emotion_tags": ["Sad"],
                "journal_text": "Having a rough day."
            })
        time.sleep(0.1)

    today_str = datetime.now().strftime("%Y-%m-%d")
    requests.post(f"{BASE_URL}/logs", json={
        "user_id": user_a_id, "logged_at": today_str, "score": 2,
        "emotion_tags": ["Tired"], "journal_text": "Feeling a bit down today."
    })
    requests.post(f"{BASE_URL}/logs", json={
        "user_id": user_b_id, "logged_at": today_str, "score": 2,
        "emotion_tags": ["Exhausted"], "journal_text": "Very stressed today."
    })

    print("\n3. Waiting 5 seconds for ML prediction and suggestion generation...")
    time.sleep(5)

    print("\n4. Checking risk score...")
    res_risk = requests.get(f"{BASE_URL}/risk/current?user_id={user_a_id}")
    print("Risk response:", res_risk.json())

    print("\n5. Fetching suggestion...")
    res_sug = requests.get(f"{BASE_URL}/suggestions?user_id={user_a_id}")
    print("Suggestion response:", res_sug.json())
    sug = res_sug.json()
    if sug:
        sug_id = sug.get("id")
        print(f"\n6. Marking suggestion {sug_id} as acted...")
        res_act = requests.post(f"{BASE_URL}/suggestions/{sug_id}/acted", json={"user_id": user_a_id})
        print("Acted response:", res_act.json())
    else:
        print("No suggestion returned.")

    print("\n7. Insights correlation...")
    res_corr = requests.get(f"{BASE_URL}/insights/correlation?user_id={user_a_id}")
    print("Correlation response:", res_corr.json())

    print("\n8. Insights patterns...")
    res_pat = requests.get(f"{BASE_URL}/insights/patterns?user_id={user_a_id}")
    print("Patterns response:", res_pat.json())

    # Debug: query logs directly from DB
    res_me = requests.get(f"{BASE_URL}/logs/me?user_id={user_a_id}")
    res_partner = requests.get(f"{BASE_URL}/logs/couple?user_id={user_a_id}")
    print("\nDEBUG:")
    print("My Logs:", [ {"date": l["logged_at"], "score": l["score"]} for l in res_me.json() ])
    partner_only = [l for l in res_partner.json() if l["user_id"] == user_b_id]
    print("Partner Logs:", [ {"date": l["logged_at"], "score": l["score"]} for l in partner_only ])

if __name__ == "__main__":
    run_verification()
