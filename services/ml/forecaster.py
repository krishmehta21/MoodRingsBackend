import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
import logging

import models

logger = logging.getLogger(__name__)

@dataclass
class ForecastResult:
    user_id: str
    trend: str                    # "improving" | "declining" | "stable"
    slope_7d: float               # linear regression slope per day
    predicted_score_24h: float    
    predicted_score_48h: float
    confidence: float             # 0.0-1.0 based on data quantity
    pattern_detected: Optional[str]  # e.g. "low_on_mondays"
    should_notify_partner: bool

def calculate_trend(scores: List[float]) -> float:
    """Uses numpy linear regression (np.polyfit) on the last 7 scores."""
    if len(scores) < 2:
        return 0.0
    
    # x = [0, 1, 2, ...] based on the length of scores provided
    # The requirement says "on the last 7 scores"
    x = np.arange(len(scores))
    y = np.array(scores)
    
    # polyfit returns [slope, intercept]
    slope, _ = np.polyfit(x, y, 1)
    return float(slope)

def detect_weekly_pattern(logs: List[models.MoodLog]) -> Optional[str]:
    """
    Only runs if user has 21+ days of data.
    Group scores by day of week.
    If any day's average is 1.5+ points below overall average -> return "low_on_{dayname}s"
    """
    if len(logs) < 21:
        return None
    
    # day_of_week -> list of scores
    day_map = {i: [] for i in range(7)}
    all_scores = []
    for log in logs:
        dow = log.logged_at.weekday()
        day_map[dow].append(log.score)
        all_scores.append(log.score)
    
    overall_avg = np.mean(all_scores)
    
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    
    for dow, scores in day_map.items():
        if not scores:
            continue
        day_avg = np.mean(scores)
        if day_avg <= overall_avg - 1.5:
            return f"low_on_{day_names[dow]}s"
            
    return None

def predict_scores(scores: List[float], slope: float) -> Tuple[float, float]:
    """
    Simple linear projection from last known score.
    predicted_24h = last_score + slope
    predicted_48h = last_score + (slope * 2)
    Clamp both to range [1.0, 10.0]
    """
    last_score = scores[-1] if scores else 5.0
    
    pred_24h = last_score + slope
    pred_48h = last_score + (slope * 2)
    
    pred_24h = max(1.0, min(10.0, pred_24h))
    pred_48h = max(1.0, min(10.0, pred_48h))
    
    return float(pred_24h), float(pred_48h)

def run_mood_forecast(user_id: str, db: Session) -> ForecastResult:
    """
    Fetch last 21 days of logs for user.
    If fewer than 7 logs -> return ForecastResult with should_notify_partner=False, confidence=0.0
    """
    now = datetime.now(timezone.utc)
    twenty_one_days_ago = now - timedelta(days=21)
    
    logs = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == user_id,
        models.MoodLog.logged_at >= twenty_one_days_ago
    ).order_by(models.MoodLog.logged_at.asc()).all()
    
    num_logs = len(logs)
    
    if num_logs < 7:
        return ForecastResult(
            user_id=user_id,
            trend="stable",
            slope_7d=0.0,
            predicted_score_24h=5.0,
            predicted_score_48h=5.0,
            confidence=0.0,
            pattern_detected=None,
            should_notify_partner=False
        )
    
    # Confidence calculation
    if num_logs >= 21: confidence = 1.0
    elif num_logs >= 15: confidence = 0.8
    elif num_logs >= 11: confidence = 0.6
    else: confidence = 0.4
    
    # Pattern detection
    pattern = detect_weekly_pattern(logs)
    
    # Calculate trend (slope) on last 7 logs if available, or all logs if < 7?
    # Spec says "on the last 7 scores" in Phase 3.
    recent_scores = [log.score for log in logs[-7:]]
    slope = calculate_trend(recent_scores)
    
    # Trend label
    if slope > 0.1: # Small threshold for stable
        trend = "improving"
    elif slope < -0.1:
        trend = "declining"
    else:
        trend = "stable"
        
    # Predictions
    pred_24h, pred_48h = predict_scores(recent_scores, slope)
    
    # should_notify_partner logic
    # - slope_7d < -0.3
    # - predicted_score_24h < 5.5
    # - confidence >= 0.4
    should_notify = (
        slope < -0.3 and
        pred_24h < 5.5 and
        confidence >= 0.4
    )
    
    return ForecastResult(
        user_id=str(user_id),
        trend=trend,
        slope_7d=round(slope, 3),
        predicted_score_24h=round(pred_24h, 2),
        predicted_score_48h=round(pred_48h, 2),
        confidence=confidence,
        pattern_detected=pattern,
        should_notify_partner=should_notify
    )
