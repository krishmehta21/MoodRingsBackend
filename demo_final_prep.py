import uuid
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import sys
import os

# Add parent dir to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import models
import database

def final_prep():
    db = database.SessionLocal()
    # Use the ID we generated earlier or create a new one
    USER_ID = "0218b212-f92f-4180-af76-c9bf091cb21f"
    PARTNER_ID = "023583bd-13f8-477d-bda1-64f3e05a2116"
    
    uid = uuid.UUID(USER_ID)
    pid = uuid.UUID(PARTNER_ID)
    
    sorted_ids = sorted([str(uid), str(pid)])
    couple_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{sorted_ids[0]}_{sorted_ids[1]}")
    
    print(f"Injecting HIGH STRESS for couple {couple_uuid}...")
    
    # 1. Insert Risk Score (High Stress)
    new_risk = models.RiskScore(
        couple_id=couple_uuid,
        p_stress=0.88, # High stress
        features_snapshot={
            "mood_delta_7d": 5.5,
            "sentiment_trend": -0.4,
            "streak_broken": 1,
            "volatility_score": 2.1,
            "low_score_overlap": 2
        },
        suggestion_triggered=True
    )
    db.add(new_risk)
    
    # 2. Insert Suggestion
    new_sug = models.Suggestion(
        couple_id=couple_uuid,
        tier="priority",
        message="You two have been ships passing in the night. Block 30 minutes tonight — no phones, no agenda, just check in.",
        actions=["30 mins no phones", "Direct eye contact"]
    )
    db.add(new_sug)
    
    db.commit()
    print("Demo Data Injected Successfully!")
    db.close()

if __name__ == "__main__":
    final_prep()
