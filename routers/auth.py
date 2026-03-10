from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import models, database
from supabase_client import supabase
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
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

class AuthRequest(BaseModel):
    email: str
    password: str

class ProfileUpdateRequest(BaseModel):
    user_id: str
    display_name: str
    age: int | None = None
    relationship_type: str | None = None
    together_duration: str | None = None
    anniversary_date: str | None = None
    timezone: str | None = None


@router.patch("/profile")
def update_profile(req: ProfileUpdateRequest, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(req.user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.display_name = req.display_name
    user.age = req.age
    user.relationship_type = req.relationship_type
    user.together_duration = req.together_duration
    user.anniversary_date = req.anniversary_date
    user.timezone = req.timezone

    if req.display_name and len(req.display_name.strip()) > 0:
        user.profile_complete = True
    else:
        raise HTTPException(status_code=400, detail="Display name is required")

    db.commit()
    db.refresh(user)

    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "profile_complete": user.profile_complete
    }


@router.post("/register")
def register(req: AuthRequest, db: Session = Depends(database.get_db)):
    auth_resp = supabase.auth.sign_up({"email": req.email, "password": req.password})

    if not auth_resp.user:
        raise HTTPException(status_code=400, detail="Registration failed with Supabase.")

    uid = uuid.UUID(auth_resp.user.id)

    # Try finding by ID first, then by email (handles re-registration after delete)
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        user = db.query(models.User).filter(models.User.email == req.email).first()
        if user:
            # Orphaned row from a previous account — update the ID to match new Supabase auth
            user.id = uid
            user.profile_complete = False
            user.display_name = None
            user.partner_id = None
            user.invite_code = None
            user.invite_code_expires_at = None
            db.commit()
            db.refresh(user)
        else:
            # Truly new user
            user = models.User(id=uid, email=req.email)
            db.add(user)
            db.commit()
            db.refresh(user)

    return {
        "access_token": auth_resp.session.access_token if auth_resp.session else None,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "partner_id": str(user.partner_id) if user.partner_id else None,
            "profile_complete": user.profile_complete
        }
    }


@router.post("/login")
def login(req: AuthRequest, db: Session = Depends(database.get_db)):
    # Step 1: Supabase auth
    try:
        auth_resp = supabase.auth.sign_in_with_password({"email": req.email, "password": req.password})
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Supabase auth failed: {str(e)}")

    if not auth_resp.session:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    # Step 2: DB lookup with safe upsert
    try:
        uid = uuid.UUID(auth_resp.user.id)
        user = db.query(models.User).filter(models.User.id == uid).first()

        if not user:
            # Check by email before inserting (prevents UniqueViolation)
            user = db.query(models.User).filter(models.User.email == req.email).first()
            if user:
                user.id = uid
                db.commit()
                db.refresh(user)
            else:
                user = models.User(id=uid, email=req.email)
                db.add(user)
                db.commit()
                db.refresh(user)

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    return {
        "access_token": auth_resp.session.access_token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "partner_id": str(user.partner_id) if user.partner_id else None,
            "profile_complete": user.profile_complete,
            "display_name": user.display_name,
        }
    }


@router.get("/me")
def get_me(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    partner_display_name = None
    if user.partner_id:
        partner = db.query(models.User).filter(models.User.id == user.partner_id).first()
        if partner:
            partner_display_name = partner.display_name

    profile_complete = bool(
        user.profile_complete and
        user.display_name and
        len(user.display_name.strip()) > 0
    )

    return {
        "id": str(user.id),
        "email": user.email,
        "partner_id": str(user.partner_id) if user.partner_id else None,
        "invite_code": user.invite_code,
        "created_at": user.created_at,
        "display_name": user.display_name,
        "age": user.age,
        "relationship_type": user.relationship_type,
        "together_duration": user.together_duration,
        "anniversary_date": user.anniversary_date,
        "timezone": user.timezone,
        "profile_complete": profile_complete,
        "partner_display_name": partner_display_name
    }


@router.post("/generate-code")
def generate_invite_code(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if user.partner_id:
        return {"message": "You are already linked to a partner."}

    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

    user.invite_code = code
    user.invite_code_expires_at = expires_at
    db.commit()

    return {"invite_code": code, "expires_at": expires_at.isoformat()}


@router.post("/link")
def link_partner(req: LinkPartnerRequest, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(req.user_id)
    partner = db.query(models.User).filter(models.User.invite_code == req.invite_code).first()

    if not partner:
        raise HTTPException(status_code=404, detail="Invalid invite code.")

    if partner.invite_code_expires_at and partner.invite_code_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invite code has expired.")

    if partner.id == uid:
        raise HTTPException(status_code=400, detail="Cannot link to yourself.")

    current_user = db.query(models.User).filter(models.User.id == uid).first()

    if not current_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if current_user.partner_id or partner.partner_id:
        raise HTTPException(status_code=400, detail="One or both users are already linked.")

    current_user.partner_id = partner.id
    partner.partner_id = current_user.id
    partner.invite_code = None
    partner.invite_code_expires_at = None
    db.commit()

    return {
        "message": "Partner successfully linked!",
        "partner": {
            "id": str(partner.id),
            "display_name": partner.display_name,
            "email": partner.email
        }
    }


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


@router.delete("/me")
def delete_account(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    # Unlink partner first
    if user.partner_id:
        partner = db.query(models.User).filter(models.User.id == user.partner_id).first()
        if partner:
            partner.partner_id = None

    # Delete all mood logs
    db.query(models.MoodLog).filter(models.MoodLog.user_id == uid).delete(synchronize_session=False)

    # Delete Postgres row
    db.delete(user)
    db.commit()

    # Delete from Supabase Auth — THIS was the missing step causing re-registration to fail
    try:
        supabase.auth.admin.delete_user(str(uid))
    except Exception as e:
        # Log but don't fail — Postgres row is already gone
        print(f"Warning: could not delete Supabase Auth user {uid}: {e}")

    return {"message": "Account successfully deleted."}