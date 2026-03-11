from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
import uuid
import time

import models
import database
from crypto_utils import encrypt_text, decrypt_text
from pydantic import BaseModel

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    analyzer = SentimentIntensityAnalyzer()
except ImportError:
    analyzer = None

from services.ml.predictor import generate_and_save_risk_score

router = APIRouter(prefix="/logs", tags=["Logs"])

class MoodLogCreate(BaseModel):
    user_id: str
    score: int
    emotion_tags: Optional[List[str]] = []
    journal_text: Optional[str] = None
    calendar_stress: Optional[float] = None
    logged_at: Optional[str] = None

class MoodLogEdit(BaseModel):
    score: Optional[int] = None
    emotion_tags: Optional[List[str]] = None
    journal_text: Optional[str] = None

def analyze_and_update_sentiment(log_id: uuid.UUID, text: str):
    if not text or not analyzer:
        return
    sentiment_dict = analyzer.polarity_scores(text)
    compound_score = sentiment_dict.get('compound', 0.0)
    db = database.SessionLocal()
    try:
        log = db.query(models.MoodLog).filter(models.MoodLog.id == log_id).first()
        if log:
            log.sentiment_score = compound_score
            db.commit()
    finally:
        db.close()

def run_mood_post_processing(log_id: uuid.UUID, user_id: uuid.UUID, partner_id: Optional[uuid.UUID], journal_text: Optional[str]):
    """Consolidated background task for NLP, ML, and other heavy operations."""
    db = database.SessionLocal()
    try:
        # 1. NLP Sentiment
        if journal_text:
            analyze_and_update_sentiment(log_id, journal_text)

        # 2. ML & Risk Prediction
        if partner_id:
            generate_and_save_risk_score(str(user_id), str(partner_id))
            
        # 3. Push notifications (Placeholder for future expansion)
        # logger.info(f"Background processing complete for log {log_id}")
    except Exception:
        pass # Background tasks must be robust
    finally:
        db.close()

@router.post("")
def create_mood_log(
    log_in: MoodLogCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db)
):
    uid = uuid.UUID(log_in.user_id)
    
    # 1. Validate User and get partner_id (Synchronous)
    user_info = db.query(models.User.partner_id).filter(models.User.id == uid).first()
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found.")
    partner_id = user_info.partner_id

    # 2. Encryption (Fast)
    encrypted_journal = encrypt_text(log_in.journal_text) if log_in.journal_text else None
    
    if log_in.logged_at:
        try:
            dt = datetime.fromisoformat(log_in.logged_at)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = dt
        except ValueError:
            now = datetime.now(timezone.utc)
    else:
        now = datetime.now(timezone.utc)

    # 3. Create and save the raw log row
    new_log = models.MoodLog(
        id=uuid.uuid4(), # Client-side ID generation for zero-roundtrip retrieval
        user_id=uid,
        logged_at=now,
        score=log_in.score,
        emotion_tags=log_in.emotion_tags,
        journal_text=encrypted_journal,
        calendar_stress=log_in.calendar_stress
    )
    log_id = new_log.id

    db.add(new_log)
    db.commit()

    # 4. Hand off all heavy work to background task
    background_tasks.add_task(
        run_mood_post_processing, 
        log_id, 
        uid, 
        partner_id,
        log_in.journal_text
    )

    # 5. Return immediately
    return {"message": "Log created successfully", "log_id": str(log_id)}

@router.get("/me")
def get_my_logs(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    logs = db.query(models.MoodLog)\
        .filter(models.MoodLog.user_id == uid)\
        .order_by(models.MoodLog.logged_at.desc())\
        .all()

    results = []
    for log in logs:
        decrypted_journal = decrypt_text(log.journal_text) if log.journal_text else None
        results.append({
            "id": str(log.id),
            "user_id": str(log.user_id),
            "logged_at": log.logged_at.isoformat() if log.logged_at else None,
            "score": log.score,
            "emotion_tags": log.emotion_tags,
            "journal_text": decrypted_journal,
            "sentiment_score": log.sentiment_score,
            "calendar_stress": log.calendar_stress,
            "created_at": log.created_at.isoformat() if log.created_at else None,
        })
    return results

@router.get("/couple")
def get_couple_logs(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    my_logs = get_my_logs(user_id, db)

    partner_logs_result = []
    if user.partner_id:
        partner_logs_query = db.query(models.MoodLog)\
            .filter(models.MoodLog.user_id == user.partner_id)\
            .with_entities(
                models.MoodLog.id,
                models.MoodLog.user_id,
                models.MoodLog.logged_at,
                models.MoodLog.score,
                models.MoodLog.emotion_tags,
                models.MoodLog.sentiment_score,
                models.MoodLog.calendar_stress
            )\
            .order_by(models.MoodLog.logged_at.desc())\
            .all()

        for p_log in partner_logs_query:
            partner_logs_result.append({
                "id": str(p_log.id),
                "user_id": str(p_log.user_id),
                "logged_at": p_log.logged_at.isoformat() if p_log.logged_at else None,
                "score": p_log.score,
                "emotion_tags": p_log.emotion_tags,
                "sentiment_score": p_log.sentiment_score,
                "calendar_stress": p_log.calendar_stress,
            })

    return {"me": my_logs, "partner": partner_logs_result}

@router.patch("/{log_id}")
def edit_mood_log(
    log_id: str,
    edit_in: MoodLogEdit,
    user_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(database.get_db)
):
    lid = uuid.UUID(log_id)
    uid = uuid.UUID(user_id)

    log = db.query(models.MoodLog).filter(
        models.MoodLog.id == lid,
        models.MoodLog.user_id == uid
    ).first()

    if not log:
        raise HTTPException(status_code=404, detail="Log not found or not yours.")

    if edit_in.score is not None:
        log.score = edit_in.score
    if edit_in.emotion_tags is not None:
        log.emotion_tags = edit_in.emotion_tags
    if edit_in.journal_text is not None:
        log.journal_text = encrypt_text(edit_in.journal_text)
        background_tasks.add_task(analyze_and_update_sentiment, log.id, edit_in.journal_text)

    db.commit()
    return {"message": "Log edited successfully."}

@router.delete("/{log_id}")
def delete_mood_log(log_id: str, user_id: str, db: Session = Depends(database.get_db)):
    lid = uuid.UUID(log_id)
    uid = uuid.UUID(user_id)

    log = db.query(models.MoodLog).filter(
        models.MoodLog.id == lid,
        models.MoodLog.user_id == uid
    ).first()

    if not log:
        raise HTTPException(status_code=404, detail="Log not found or not yours.")

    db.delete(log)
    db.commit()
    return {"message": "Log deleted."}