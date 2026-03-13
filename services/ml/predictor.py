import os
import pickle
import numpy as np
import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, datetime, timedelta, timezone
import uuid

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
import models
from services.calendar import get_calendar_stress_score
from routers.dashboard import get_response_lag_hours

logger = logging.getLogger(__name__)

MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'models'))
# ML Coefficients (Extracted from scikit-learn model)
# X = [mood_delta_7d, sentiment_trend, response_lag_hours, calendar_stress, streak_broken, volatility_score, low_score_overlap]
COEFFICIENTS = np.array([0.00096745, -0.41263829, 0.30631761, 0.07787253, 0.37404774, 0.21200456, 1.21966469])
INTERCEPT = 0.05208952
SCALER_MEAN = np.array([-0.01438288, -0.03609721, 6.21069746, 0.49647649, 0.516, 1.96767181, 1.476])
SCALER_SCALE = np.array([2.98389571, 0.57041564, 3.56274709, 0.2867227, 0.49974393, 0.85874371, 1.13023183])

def _execute_prediction(features_array: np.ndarray) -> float:
    """Uses hardcoded coefficients to return the probability of stress event (Sigmoid)."""
    try:
        # Scale features manually: (X - mean) / scale
        scaled = (features_array - SCALER_MEAN) / SCALER_SCALE
        
        # Logistic Regression: z = w1*x1 + w2*x2 + ... + b
        z = np.dot(COEFFICIENTS, scaled) + INTERCEPT
        
        # Sigmoid: 1 / (1 + exp(-z))
        prob = 1 / (1 + np.exp(-z))
        return round(float(prob), 3)
    except Exception as e:
        logger.error(f"Manual prediction failed: {e}")
        return 0.0


def compute_features(db: Session, user_id: str, partner_id: str, access_token: Optional[str] = None) -> (dict, float):
    """
    Computes all 7 features:
    - mood_delta_7d: mean of partner's last 7 scores minus mean of user's last 7 scores
    - sentiment_trend: 14-day rolling mean of user's sentiment_score from mood_logs 
      (Using (last_7_avg) - (prev_7_avg) as implemented in dashboard service style for trend)
    - response_lag_hours: already built in dashboard service (reuse it)
    - calendar_stress: call get_calendar_stress_score() from calendar.py
    - streak_broken: True if either partner has a gap in the last 7 days of logs
    - volatility_score: standard deviation of user's scores over last 14 days
    - low_score_overlap: count of days where BOTH partners scored below 4 in the last 7 days
    """
    now = datetime.now(timezone.utc)
    today = now.date()
    
    # Features dict to return (for SNAPSHOT saving)
    features = {}

    # 1. mood_delta_7d
    seven_days_ago = today - timedelta(days=6)
    
    user_scores = db.query(models.MoodLog.score).filter(
        models.MoodLog.user_id == user_id,
        func.date(models.MoodLog.logged_at) >= seven_days_ago
    ).all()
    
    partner_scores = db.query(models.MoodLog.score).filter(
        models.MoodLog.user_id == partner_id,
        func.date(models.MoodLog.logged_at) >= seven_days_ago
    ).all()
    
    user_scores_list = [s[0] for s in user_scores]
    partner_scores_list = [s[0] for s in partner_scores]
    
    u_mean = np.mean(user_scores_list) if user_scores_list else 5.0
    p_mean = np.mean(partner_scores_list) if partner_scores_list else 5.0
    
    # We use Absolute Delta since the requirement says "mood_delta_7d = mean(p) - mean(u)"
    # But for stress, usually mismatch is what matters, or we just pass the raw diff.
    mood_delta_7d = p_mean - u_mean
    features['mood_delta_7d'] = round(float(mood_delta_7d), 3)


    # 2. sentiment_trend
    # Using the same logic: Last 7 days avg - Prev 7 days avg
    prev_7_start = today - timedelta(days=13)
    
    last_7_s = db.query(func.avg(models.MoodLog.sentiment_score)).filter(
        models.MoodLog.user_id == user_id,
        func.date(models.MoodLog.logged_at) >= seven_days_ago,
        models.MoodLog.sentiment_score.isnot(None)
    ).scalar() or 0.0
    
    prev_7_s = db.query(func.avg(models.MoodLog.sentiment_score)).filter(
        models.MoodLog.user_id == user_id,
        func.date(models.MoodLog.logged_at) >= prev_7_start,
        func.date(models.MoodLog.logged_at) < seven_days_ago,
        models.MoodLog.sentiment_score.isnot(None)
    ).scalar() or 0.0
    
    sentiment_trend = last_7_s - prev_7_s
    features['sentiment_trend'] = round(float(sentiment_trend), 3)


    # 3. response_lag_hours
    lag = get_response_lag_hours(db, [user_id, partner_id], today)
    features['response_lag_hours'] = lag if lag is not None else 0.0


    # 4. calendar_stress
    cal_stress = get_calendar_stress_score(access_token)
    features['calendar_stress'] = cal_stress


    # 5. streak_broken
    # Streak broken if either partner missed a day in the last 7 days window (meaning logged < 7 times)
    u_count = len(user_scores_list)
    p_count = len(partner_scores_list)
    streak_broken = int(u_count < 7 or p_count < 7)
    features['streak_broken'] = streak_broken


    # 6. volatility_score
    # standard deviation of user's scores over last 14 days
    user_14d_scores = db.query(models.MoodLog.score).filter(
        models.MoodLog.user_id == user_id,
        func.date(models.MoodLog.logged_at) >= prev_7_start
    ).all()
    user_14d_list = [s[0] for s in user_14d_scores]
    volatility = np.std(user_14d_list) if len(user_14d_list) > 1 else 0.0
    features['volatility_score'] = round(float(volatility), 3)

    
    # 7. low_score_overlap
    # count of days where BOTH partners scored below 4 in the last 7 days
    # Let's fetch the actual dates
    u_low_dates = set([d[0].date() for d in db.query(models.MoodLog.logged_at).filter(
        models.MoodLog.user_id == user_id,
        func.date(models.MoodLog.logged_at) >= seven_days_ago,
        models.MoodLog.score < 4
    ).all() if d[0]])
    
    p_low_dates = set([d[0].date() for d in db.query(models.MoodLog.logged_at).filter(
        models.MoodLog.user_id == partner_id,
        func.date(models.MoodLog.logged_at) >= seven_days_ago,
        models.MoodLog.score < 4
    ).all() if d[0]])
    
    overlap = len(u_low_dates.intersection(p_low_dates))
    features['low_score_overlap'] = overlap

    # Build the feature vector in order
    X = np.array([
        features['mood_delta_7d'],
        features['sentiment_trend'],
        features['response_lag_hours'],
        features['calendar_stress'],
        features['streak_broken'],
        features['volatility_score'],
        features['low_score_overlap']
    ])
    
    p_stress = _execute_prediction(X)

    return features, p_stress

def generate_and_save_risk_score(user_id: str, partner_id: str, access_token: Optional[str] = None):
    # Execute in a new session since it's a background task
    import database
    db = database.SessionLocal()
    try:
        # Sort UUIDs for a consistent couple_id
        sorted_ids = sorted([str(user_id), str(partner_id)])
        couple_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"{sorted_ids[0]}_{sorted_ids[1]}")
        
        # Determine if we should use the user's token or partner's token (or both?)
        # For simple v1, we use the token of the user who just logged.
        curr_user = db.query(models.User).filter(models.User.id == user_id).first()
        token = curr_user.google_access_token if curr_user else None
        
        features, p_stress = compute_features(db, user_id, partner_id, token)
        
        suggestion = False
        if p_stress > 0.70:
            suggestion = True
            
        new_risk = models.RiskScore(
            couple_id=couple_uuid,
            p_stress=p_stress,
            features_snapshot=features,
            suggestion_triggered=suggestion
        )
        db.add(new_risk)
        
        if suggestion:
            from services.suggestions import select_best_suggestion
            u_score_log = db.query(models.MoodLog.score).filter(models.MoodLog.user_id == user_id).order_by(models.MoodLog.logged_at.desc()).first()
            p_score_log = db.query(models.MoodLog.score).filter(models.MoodLog.user_id == partner_id).order_by(models.MoodLog.logged_at.desc()).first()
            u_score = u_score_log[0] if u_score_log else 5
            p_score = p_score_log[0] if p_score_log else 5
            
            sugg_data = select_best_suggestion(p_stress, u_score, p_score)
            new_suggestion = models.Suggestion(
                couple_id=couple_uuid,
                tier=sugg_data["tier"],
                message=sugg_data["message"],
                actions=sugg_data["actions"]
            )
            db.add(new_suggestion)
            
        db.commit()
    except Exception as e:
        logger.error(f"Error saving risk score: {e}")
        db.rollback()
    finally:
        db.close()

