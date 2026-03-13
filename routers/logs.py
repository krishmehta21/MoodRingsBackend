from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone, timedelta
import uuid
import time

import models
import database
from crypto_utils import encrypt_text, decrypt_text
from pydantic import BaseModel

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    vader_analyzer = SentimentIntensityAnalyzer()
except ImportError:
    vader_analyzer = None

def analyze_sentiment(text: str) -> float:
    """Uses VADER for lightweight sentiment analysis."""
    if vader_analyzer:
        try:
            return vader_analyzer.polarity_scores(text)['compound']
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"VADER analysis failed: {e}")
    return 0.0

# ML imports moved inside background task to speed up startup
from services.push_notifications import send_nudge_notification
import json
import random
import os

ROUTER_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(ROUTER_DIR)
SUGGESTIONS_JSON_PATH = os.path.join(BACKEND_DIR, "data", "partner_nudge_suggestions.json")

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
    if not text:
        return
    
    compound_score = analyze_sentiment(text)
    
    db = database.SessionLocal()
    try:
        log = db.query(models.MoodLog).filter(models.MoodLog.id == log_id).first()
        if log:
            log.sentiment_score = compound_score
            db.commit()
    finally:
        db.close()

def select_partner_nudge(forecast: "ForecastResult", partner_recent_score: float, time_of_day: str):
    """Selects a nudge from the JSON dataset based on context and time of day."""
    from services.nudge_selector import select_partner_nudge as selector_fn
    return selector_fn(forecast, partner_recent_score, time_of_day)

def get_time_of_day() -> str:
    hour = datetime.now().hour
    if 5 <= hour < 12: return "morning"
    if 12 <= hour < 17: return "afternoon"
    if 17 <= hour < 22: return "evening"
    return "any"

def save_partner_nudge(db: Session, recipient_id: uuid.UUID, subject_id: uuid.UUID, nudge: dict, forecast: "ForecastResult"):
    """Saves the nudge to the partner_nudges table and returns the object."""
    new_nudge = models.PartnerNudge(
        recipient_id=recipient_id,
        subject_id=subject_id,
        nudge_id=nudge["id"],
        message=nudge["message_to_partner"],
        category=nudge.get("category", "General"),
        forecast_slope=forecast.slope_7d,
        predicted_score=forecast.predicted_score_24h,
        confidence=forecast.confidence
    )
    db.add(new_nudge)
    db.commit()
    db.refresh(new_nudge)
    return new_nudge

async def run_mood_post_processing(log_id: uuid.UUID, user_id: uuid.UUID, partner_id: Optional[uuid.UUID], journal_text: Optional[str]):    
    """Consolidated background task for NLP, ML, and other heavy operations."""
    db = database.SessionLocal()
    try:
        from services.ml.predictor import generate_and_save_risk_score
        from services.ml.forecaster import run_mood_forecast

        # 1. NLP Sentiment
        if journal_text:
            analyze_and_update_sentiment(log_id, journal_text)

        # 2. ML & Risk Prediction
        if partner_id:
            generate_and_save_risk_score(str(user_id), str(partner_id))
            
            # 3. Proactive Partner Nudges
            from services.nudge_cooldown import is_on_cooldown
            on_cooldown = await is_on_cooldown(str(user_id), str(partner_id), db)
            if not on_cooldown:
                forecast = run_mood_forecast(str(user_id), db)
                if forecast.should_notify_partner:
                    # Get partner's most recent score for "both_declining" check
                    p_recent = db.query(models.MoodLog.score).filter(
                        models.MoodLog.user_id == partner_id
                    ).order_by(models.MoodLog.logged_at.desc()).first()
                    p_score = p_recent[0] if p_recent else 5

                    nudge_data = select_partner_nudge(forecast, p_score, get_time_of_day())
                    if nudge_data:
                        saved_nudge = save_partner_nudge(db, partner_id, user_id, nudge_data, forecast)
                        
                        # Send push notification to recipient
                        try:
                            # Use use_id as recipient here (partner_id in this context is the one receiving the nudge)
                            recipient = db.query(models.User).filter(models.User.id == partner_id).first()
                            if recipient and recipient.expo_push_token:
                                subject = db.query(models.User).filter(models.User.id == user_id).first()
                                subject_name = subject.display_name if subject else "Your partner"
                                
                                await send_nudge_notification(
                                    recipient_token=recipient.expo_push_token,
                                    subject_name=subject_name,
                                    nudge_message=nudge_data["message_to_partner"],
                                    nudge_id=str(saved_nudge.id)
                                )
                        except Exception as e:
                            import logging
                            logging.getLogger(__name__).error(f"Failed to send nudge push notification: {e}")

        # 4. Push notifications (Placeholder for future expansion)
        # logger.info(f"Background processing complete for log {log_id}")
    except Exception as e:
        # Background tasks must be robust but logged
        import logging
        logging.getLogger(__name__).error(f"Error in mood post-processing: {e}")
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

    # Grouping by date in Python for better control over field aggregation
    grouped_results = {}
    
    for log in logs:
        d = log.logged_at.date().isoformat()
        if d not in grouped_results:
            grouped_results[d] = {
                "id": str(log.id), # Keep latest ID for editing
                "user_id": str(log.user_id),
                "logged_at": log.logged_at.isoformat(),
                "scores": [log.score],
                "sentiment_scores": [log.sentiment_score] if log.sentiment_score is not None else [],
                "calendar_stresses": [log.calendar_stress] if log.calendar_stress is not None else [],
                "all_tags": set(log.emotion_tags or []),
                "journals": [decrypt_text(log.journal_text)] if log.journal_text else [],
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
        else:
            grouped_results[d]["scores"].append(log.score)
            if log.sentiment_score is not None:
                grouped_results[d]["sentiment_scores"].append(log.sentiment_score)
            if log.calendar_stress is not None:
                grouped_results[d]["calendar_stresses"].append(log.calendar_stress)
            if log.emotion_tags:
                grouped_results[d]["all_tags"].update(log.emotion_tags)
            if log.journal_text:
                grouped_results[d]["journals"].append(decrypt_text(log.journal_text))

    final_results = []
    for d_iso in sorted(grouped_results.keys(), reverse=True):
        data = grouped_results[d_iso]
        
        # Average Score
        avg_score = round(sum(data["scores"]) / len(data["scores"]), 1)
        
        # Average Sentiment
        avg_sent = None
        if data["sentiment_scores"]:
            avg_sent = round(sum(data["sentiment_scores"]) / len(data["sentiment_scores"]), 3)
            
        # Average Stress
        avg_stress = None
        if data["calendar_stresses"]:
            avg_stress = round(sum(data["calendar_stresses"]) / len(data["calendar_stresses"]), 2)
            
        final_results.append({
            "id": data["id"],
            "user_id": data["user_id"],
            "logged_at": data["logged_at"],
            "score": avg_score,
            "emotion_tags": sorted(list(data["all_tags"])),
            "journal_text": "\n\n".join(data["journals"]) if data["journals"] else None,
            "sentiment_score": avg_sent,
            "calendar_stress": avg_stress,
            "created_at": data["created_at"],
            "is_aggregated": len(data["scores"]) > 1
        })

    return final_results

@router.get("/couple")
def get_couple_logs(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    my_logs = get_my_logs(user_id, db)

    partner_logs_result = []
    if user.partner_id:
        p_logs = db.query(models.MoodLog)\
            .filter(models.MoodLog.user_id == user.partner_id)\
            .order_by(models.MoodLog.logged_at.desc())\
            .all()

        p_grouped = {}
        for log in p_logs:
            d = log.logged_at.date().isoformat()
            if d not in p_grouped:
                p_grouped[d] = {
                    "id": str(log.id),
                    "user_id": str(log.user_id),
                    "logged_at": log.logged_at.isoformat(),
                    "scores": [log.score],
                    "all_tags": set(log.emotion_tags or []),
                    "sentiment_scores": [log.sentiment_score] if log.sentiment_score is not None else [],
                    "calendar_stresses": [log.calendar_stress] if log.calendar_stress is not None else []
                }
            else:
                p_grouped[d]["scores"].append(log.score)
                if log.emotion_tags:
                    p_grouped[d]["all_tags"].update(log.emotion_tags)
                if log.sentiment_score is not None:
                    p_grouped[d]["sentiment_scores"].append(log.sentiment_score)
                if log.calendar_stress is not None:
                    p_grouped[d]["calendar_stresses"].append(log.calendar_stress)

        for d_iso in sorted(p_grouped.keys(), reverse=True):
            data = p_grouped[d_iso]
            avg_score = round(sum(data["scores"]) / len(data["scores"]), 1)
            
            avg_sent = None
            if data["sentiment_scores"]:
                avg_sent = round(sum(data["sentiment_scores"]) / len(data["sentiment_scores"]), 3)
            
            avg_stress = None
            if data["calendar_stresses"]:
                avg_stress = round(sum(data["calendar_stresses"]) / len(data["calendar_stresses"]), 2)

            partner_logs_result.append({
                "id": data["id"],
                "user_id": data["user_id"],
                "logged_at": data["logged_at"],
                "score": avg_score,
                "emotion_tags": sorted(list(data["all_tags"])),
                "sentiment_score": avg_sent,
                "calendar_stress": avg_stress,
                "is_aggregated": len(data["scores"]) > 1
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
    
@router.get("/history")
def get_mood_history(user_id: str, days: int = 7, db: Session = Depends(database.get_db)):
    """
    Returns daily average mood scores for the last X days.
    Structure: {'me': [...], 'partner': [...]}
    """
    from sqlalchemy import func as sa_func
    from datetime import time as dt_time  # datetime.time, NOT the time module

    days = min(days, 30)
    try:
        uid = uuid.UUID(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user_id")

    user = db.query(models.User).filter(models.User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    end_date = datetime.now(timezone.utc).date()
    start_date = end_date - timedelta(days=days - 1)

    # Build a timezone-aware start datetime — was broken before (time.min = time module, not datetime.time)
    start_dt = datetime.combine(start_date, dt_time.min).replace(tzinfo=timezone.utc)

    def get_user_history_list(uid_to_query):
        if uid_to_query is None:
            return []

        logs = (
            db.query(
                sa_func.date(models.MoodLog.logged_at).label("day"),
                sa_func.avg(models.MoodLog.score).label("avg_score"),
            )
            .filter(
                models.MoodLog.user_id == uid_to_query,
                models.MoodLog.logged_at >= start_dt,
            )
            .group_by(sa_func.date(models.MoodLog.logged_at))
            .order_by("day")
            .all()
        )

        history_map = {
            str(row.day): round(float(row.avg_score), 2) for row in logs
        }

        # Fill every day in the range — days with no log get score: null
        results = []
        curr = start_date
        while curr <= end_date:
            d_iso = curr.isoformat()
            results.append({
                "date": d_iso,
                "score": history_map.get(d_iso),  # None if no log that day
            })
            curr += timedelta(days=1)
        return results

    return {
        "me": get_user_history_list(uid),
        "partner": get_user_history_list(user.partner_id) if user.partner_id else [],
    }