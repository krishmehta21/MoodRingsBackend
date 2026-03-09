from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date, timezone
import uuid
import models, database

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def to_date(val) -> date:
    if isinstance(val, datetime):
        return val.date()
    return val


def calculate_streak(db: Session, user_id: uuid.UUID, today: date) -> int:
    logs = db.query(models.MoodLog.logged_at).filter(
        models.MoodLog.user_id == user_id,
    ).order_by(models.MoodLog.logged_at.desc()).all()

    if not logs:
        return 0

    seen_dates = []
    for log in logs:
        d = to_date(log.logged_at)
        if d not in seen_dates:
            seen_dates.append(d)

    if seen_dates and seen_dates[0] < today - timedelta(days=1):
        return 0

    streak = 0
    current_check_date = today
    for d in seen_dates:
        if d == current_check_date:
            streak += 1
            current_check_date -= timedelta(days=1)
        elif d < current_check_date:
            break

    return streak


def calculate_sentiment_trend(db: Session, user_id: uuid.UUID, today: date) -> float:
    last_7_start = today - timedelta(days=6)
    prev_7_start = today - timedelta(days=13)

    last_7_avg = db.query(func.avg(models.MoodLog.sentiment_score)).filter(
        models.MoodLog.user_id == user_id,
        func.date(models.MoodLog.logged_at) >= last_7_start,
        func.date(models.MoodLog.logged_at) <= today,
        models.MoodLog.sentiment_score.isnot(None)
    ).scalar()

    prev_7_avg = db.query(func.avg(models.MoodLog.sentiment_score)).filter(
        models.MoodLog.user_id == user_id,
        func.date(models.MoodLog.logged_at) >= prev_7_start,
        func.date(models.MoodLog.logged_at) < last_7_start,
        models.MoodLog.sentiment_score.isnot(None)
    ).scalar()

    last_7 = float(last_7_avg) if last_7_avg is not None else 0.0
    prev_7 = float(prev_7_avg) if prev_7_avg is not None else 0.0
    return round(last_7 - prev_7, 3)


def get_response_lag_hours(db: Session, couple_user_ids: list, today: date):
    logs = db.query(models.MoodLog).filter(
        models.MoodLog.user_id.in_(couple_user_ids),
        func.date(models.MoodLog.logged_at) == today
    ).all()

    if len(logs) >= 2:
        try:
            diff_seconds = abs((logs[0].created_at - logs[1].created_at).total_seconds())
            return round(diff_seconds / 3600.0, 2)
        except Exception:
            return None
    return None


def get_risk_tier(p_stress: float):
    if p_stress > 0.85:
        return "priority_alert", "#C4764A", "Needs attention"
    elif p_stress > 0.70:
        return "active_suggestion", "#C4A35A", "Some tension detected"
    elif p_stress > 0.50:
        return "soft_nudge", "#C4A35A", "Some tension detected"
    else:
        return None, "#7AAB8A", "Feeling connected"


SUGGESTION_COPY = {
    "priority_alert": {
        "title": "Priority Connection Moment",
        "description": "One of you is experiencing significant stress. Consider reaching out with extra care and support."
    },
    "active_suggestion": {
        "title": "Check In Together",
        "description": "There's noticeable stress in your relationship. A moment of connection could help."
    },
    "soft_nudge": {
        "title": "Connection Moment",
        "description": "Take a minute to share one thing you appreciate about each other today."
    }
}

DEFAULT_SUGGESTION = {
    "title": "Connection Moment",
    "description": "Take a minute to share one thing you appreciate about each other today."
}


@router.get("")
def get_dashboard(user_id: str, db: Session = Depends(database.get_db)):
    try:
        uid = uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format.")

    try:
        user = db.query(models.User).filter(models.User.id == uid).first()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching user: {str(e)}")

    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    partner_id = user.partner_id
    today = datetime.now(timezone.utc).date()
    seven_days_ago = today - timedelta(days=6)

    # --- My data ---
    try:
        my_logs_7d = db.query(
            models.MoodLog.logged_at,
            models.MoodLog.score
        ).filter(
            models.MoodLog.user_id == uid,
            func.date(models.MoodLog.logged_at) >= seven_days_ago,
            func.date(models.MoodLog.logged_at) <= today
        ).order_by(models.MoodLog.logged_at.asc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching logs: {str(e)}")

    my_scores = [{"date": to_date(row.logged_at).isoformat(), "score": row.score} for row in my_logs_7d]
    my_logged_today = any(to_date(row.logged_at) == today for row in my_logs_7d)
    my_streak = calculate_streak(db, uid, today)
    my_sentiment_trend = calculate_sentiment_trend(db, uid, today)

    my_latest_today = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == uid,
        func.date(models.MoodLog.logged_at) == today
    ).order_by(models.MoodLog.logged_at.desc()).first()

    dashboard_data = {
        "risk_score": 0.0,
        "risk_color": "#7AAB8A",
        "risk_label": "Feeling connected",
        "features_snapshot": {},
        "response_lag_hours": None,
        "me": {
            "today_logged": my_logged_today,
            "today_score": my_latest_today.score if my_latest_today else None,
            "streak": my_streak,
            "sentiment_trend": my_sentiment_trend,
            "last_7_days": my_scores
        },
        "partner": None,
        "suggestion": DEFAULT_SUGGESTION
    }

    if not partner_id:
        return dashboard_data

    # --- Partner data ---
    try:
        partner_logs_7d = db.query(
            models.MoodLog.logged_at,
            models.MoodLog.score
        ).filter(
            models.MoodLog.user_id == partner_id,
            func.date(models.MoodLog.logged_at) >= seven_days_ago,
            func.date(models.MoodLog.logged_at) <= today
        ).order_by(models.MoodLog.logged_at.asc()).all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error fetching partner logs: {str(e)}")

    partner_scores = [{"date": to_date(row.logged_at).isoformat(), "score": row.score} for row in partner_logs_7d]
    partner_logged_today = any(to_date(row.logged_at) == today for row in partner_logs_7d)
    partner_streak = calculate_streak(db, partner_id, today)
    partner_sentiment_trend = calculate_sentiment_trend(db, partner_id, today)

    partner_latest_today = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == partner_id,
        func.date(models.MoodLog.logged_at) == today
    ).order_by(models.MoodLog.logged_at.desc()).first()

    dashboard_data["response_lag_hours"] = get_response_lag_hours(db, [uid, partner_id], today)

    # --- Risk score ---
    try:
        sorted_ids = sorted([str(uid), str(partner_id)])
        couple_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{sorted_ids[0]}_{sorted_ids[1]}")
        latest_risk = db.query(models.RiskScore).filter(
            models.RiskScore.couple_id == couple_uuid
        ).order_by(models.RiskScore.scored_at.desc()).first()
    except Exception as e:
        latest_risk = None

    if latest_risk:
        tier, color, label = get_risk_tier(latest_risk.p_stress)
        dashboard_data["risk_score"] = latest_risk.p_stress
        dashboard_data["risk_color"] = color
        dashboard_data["risk_label"] = label
        dashboard_data["features_snapshot"] = latest_risk.features_snapshot or {}

        if tier:
            dashboard_data["suggestion"] = SUGGESTION_COPY[tier]

    dashboard_data["partner"] = {
        "today_logged": partner_logged_today,
        "today_score": partner_latest_today.score if partner_latest_today else None,
        "streak": partner_streak,
        "sentiment_trend": partner_sentiment_trend,
        "last_7_days": partner_scores
    }

    return dashboard_data