from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import models

async def is_on_cooldown(
    subject_id: str, 
    recipient_id: str, 
    db: Session,
    hours: int = 48
) -> bool:
    """
    Checks if a nudge has been sent from subject to recipient in the last X hours.
    """
    threshold_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    
    last_nudge = db.query(models.PartnerNudge).filter(
        models.PartnerNudge.subject_id == subject_id,
        models.PartnerNudge.recipient_id == recipient_id,
        models.PartnerNudge.created_at >= threshold_time
    ).order_by(models.PartnerNudge.created_at.desc()).first()
    
    return last_nudge is not None
