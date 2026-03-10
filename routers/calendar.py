from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import models, database

router = APIRouter(prefix="/calendar", tags=["Calendar"])

class CalendarConnectRequest(BaseModel):
    user_id: str
    access_token: str
    refresh_token: str = None

@router.post("/connect")
def connect_calendar(req: CalendarConnectRequest, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(req.user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    user.google_access_token = req.access_token
    if req.refresh_token:
        user.google_refresh_token = req.refresh_token
    
    db.commit()
    return {"message": "Google Calendar connected successfully."}

@router.get("/status")
def get_calendar_status(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    return {
        "connected": user.google_access_token is not None,
        "email": user.email # Or other info if available
    }

@router.post("/disconnect")
def disconnect_calendar(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    user.google_access_token = None
    user.google_refresh_token = None
    db.commit()
    return {"message": "Google Calendar disconnected."}
