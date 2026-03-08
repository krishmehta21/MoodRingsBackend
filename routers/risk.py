from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import models, database

router = APIRouter(
    prefix="/risk",
    tags=["Risk"]
)

@router.get("/current")
def get_current_risk(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    if not user.partner_id:
        return {"message": "User is not linked to a partner."}
        
    sorted_ids = sorted([str(uid), str(user.partner_id)])
    couple_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{sorted_ids[0]}_{sorted_ids[1]}")
    
    latest_risk = db.query(models.RiskScore).filter(
        models.RiskScore.couple_id == couple_uuid
    ).order_by(models.RiskScore.scored_at.desc()).first()
    
    if not latest_risk:
        return {"message": "No risk score computed yet."}
        
    tier = None
    if latest_risk.p_stress > 0.85:
        tier = "priority_alert"
    elif latest_risk.p_stress > 0.70:
        tier = "active_suggestion"
    elif latest_risk.p_stress > 0.50:
        tier = "soft_nudge"
        
    return {
        "couple_id": latest_risk.couple_id,
        "scored_at": latest_risk.scored_at,
        "p_stress": latest_risk.p_stress,
        "features_snapshot": latest_risk.features_snapshot,
        "suggestion_triggered": latest_risk.suggestion_triggered,
        "suggestion_tier": tier
    }
