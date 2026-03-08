from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import uuid
import models, database

router = APIRouter(
    prefix="/suggestions",
    tags=["Suggestions"]
)

@router.get("")
def get_current_suggestion(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not user or not user.partner_id:
        return {}
        
    sorted_ids = sorted([str(uid), str(user.partner_id)])
    couple_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{sorted_ids[0]}_{sorted_ids[1]}")
    
    latest_suggestion = db.query(models.Suggestion).filter(
        models.Suggestion.couple_id == couple_uuid,
        models.Suggestion.acted_on == False
    ).order_by(models.Suggestion.created_at.desc()).first()
    
    if not latest_suggestion:
        return {}
        
    return {
        "id": latest_suggestion.id,
        "tier": latest_suggestion.tier,
        "message": latest_suggestion.message,
        "actions": latest_suggestion.actions,
        "created_at": latest_suggestion.created_at
    }

@router.post("/{suggestion_id}/acted")
def mark_suggestion_acted(suggestion_id: str, user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    sid = uuid.UUID(suggestion_id)
    
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user or not user.partner_id:
        raise HTTPException(status_code=403, detail="Not linked to partner.")
        
    sorted_ids = sorted([str(uid), str(user.partner_id)])
    couple_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{sorted_ids[0]}_{sorted_ids[1]}")
    
    suggestion = db.query(models.Suggestion).filter(
        models.Suggestion.id == sid,
        models.Suggestion.couple_id == couple_uuid
    ).first()
    
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found.")
        
    suggestion.acted_on = True
    suggestion.acted_on_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(suggestion)
    
    return {
        "id": suggestion.id,
        "acted_on": suggestion.acted_on,
        "acted_on_at": suggestion.acted_on_at
    }
