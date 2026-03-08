import requests
import time
import uuid
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001"

def run_verification():
    print("1. Creating test users and linking...")
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())

    # Generate invite code for user A and link user B
    res_a = requests.post(f"{BASE_URL}/auth/generate-code?user_id={user_a_id}").json()
    code = res_a.get("invite_code")
    requests.post(f"{BASE_URL}/auth/link", json={"invite_code": code, "user_id": user_b_id})

    # Create 7 days of divergent logs
    print("\n2. Submitting divergent mood logs over 7 days to trigger high stress...")
    for i in range(7, 0, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        # User A high scores (8-9)
        a_score = 9 if i % 2 == 0 else 8
        requests.post(f"{BASE_URL}/logs", json={
            "user_id": user_a_id,
            "logged_at": day,
            "score": a_score,
            "emotion_tags": ["Happy"],
            "journal_text": "Feeling great today."
        })
        # User B low scores (2-3). Introduce a missing day for broken streak at day 4.
        if i != 4:  # skip day 4 for user B to break streak
            b_score = 2 if i % 2 == 0 else 3
            requests.post(f"{BASE_URL}/logs", json={
                "user_id": user_b_id,
                "logged_at": day,
                "score": b_score,
                "emotion_tags": ["Sad"],
                "journal_text": "Having a rough day."
            })
        time.sleep(0.2)

    # Today logs (both low to ensure recent stress)
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

if __name__ == "__main__":
    run_verification()
