from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, database
from supabase_client import supabase
from pydantic import BaseModel
import random
import string
import uuid

router = APIRouter(
    prefix="/auth",
    tags=["Auth"]
)

class LinkPartnerRequest(BaseModel):
    invite_code: str
    user_id: str

@router.get("/me")
def get_me(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    return {
        "id": str(user.id),
        "email": user.email,
        "partner_id": str(user.partner_id) if user.partner_id else None,
        "invite_code": user.invite_code,
        "created_at": user.created_at,
    }

@router.post("/generate-code")
def generate_invite_code(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not user:
        user = models.User(id=uid, email=f"{user_id}@placeholder.com")
        db.add(user)
        db.commit()
    
    if user.partner_id:
        return {"message": "You are already linked to a partner."}
        
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    user.invite_code = code
    db.commit()
    return {"invite_code": code}

@router.post("/link")
def link_partner(req: LinkPartnerRequest, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(req.user_id)
    partner = db.query(models.User).filter(models.User.invite_code == req.invite_code).first()
    
    if not partner:
        raise HTTPException(status_code=404, detail="Invalid invite code.")
        
    if partner.id == uid:
        raise HTTPException(status_code=400, detail="Cannot link to yourself.")
        
    current_user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not current_user:
        current_user = models.User(id=uid, email=f"{req.user_id}@placeholder.com")
        db.add(current_user)
        db.commit()

    if current_user.partner_id or partner.partner_id:
        raise HTTPException(status_code=400, detail="One or both users are already linked.")
        
    current_user.partner_id = partner.id
    partner.partner_id = current_user.id
    partner.invite_code = None
    db.commit()
    
    return {"message": "Partner successfully linked!"}

@router.delete("/unlink")
def unlink_partner(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if not user.partner_id:
        raise HTTPException(status_code=400, detail="You are not linked to a partner.")
    
    partner = db.query(models.User).filter(models.User.id == user.partner_id).first()
    
    user.partner_id = None
    if partner:
        partner.partner_id = None
    
    db.commit()
    return {"message": "Successfully unlinked from partner."}