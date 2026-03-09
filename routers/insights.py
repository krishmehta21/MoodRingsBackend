from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
import uuid
import numpy as np
import models, database

router = APIRouter(
    prefix="/insights",
    tags=["Insights"]
)

@router.get("/correlation")
def get_correlation(user_id: str, period: int = Query(30), db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not user or not user.partner_id:
        return {"score": 0.0, "period": period, "interpretation": "Not enough data."}
        
    start_date = datetime.now(timezone.utc).date() - timedelta(days=period)
    
    my_logs = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == uid,
        models.MoodLog.logged_at >= start_date
    ).all()
    
    partner_logs = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == user.partner_id,
        models.MoodLog.logged_at >= start_date
    ).all()
    
    my_dict = {log.logged_at: log.score for log in my_logs}
    p_dict = {log.logged_at: log.score for log in partner_logs}
    
    common_dates = sorted(list(set(my_dict.keys()).intersection(set(p_dict.keys()))))
    
    if len(common_dates) < 3:
        return {"score": 0.0, "period": period, "interpretation": "Not enough overlapping days to calculate sync."}
        
    x = [my_dict[d] for d in common_dates]
    y = [p_dict[d] for d in common_dates]
    
    correlation = np.corrcoef(x, y)[0, 1]
    
    if np.isnan(correlation):
        correlation = 0.0
    else:
        correlation = round(float(correlation), 2)
        
    if correlation >= 0.8:
        interpretation = "Your moods have been really in sync lately"
    elif correlation >= 0.4:
        interpretation = "You've been broadly moving together"
    elif correlation >= 0.0:
        interpretation = "Your moods haven't been tracking each other much this month"
    elif correlation >= -0.39:
        interpretation = "You've been trending in opposite directions recently"
    else:
        interpretation = "You've been experiencing opposite moods — one up when the other is down"
        
    return {
        "score": correlation,
        "period": period,
        "interpretation": interpretation
    }

@router.get("/patterns")
def get_patterns(user_id: str, db: Session = Depends(database.get_db)):
    uid = uuid.UUID(user_id)
    user = db.query(models.User).filter(models.User.id == uid).first()
    
    if not user or not user.partner_id:
        return []
        
    period = 90
    start_date = datetime.now(timezone.utc).date() - timedelta(days=period)
    
    my_logs = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == uid,
        models.MoodLog.logged_at >= start_date
    ).all()
    
    partner_logs = db.query(models.MoodLog).filter(
        models.MoodLog.user_id == user.partner_id,
        models.MoodLog.logged_at >= start_date
    ).all()
    
    patterns = []
    
    # 1. Lowest scoring day of week for user
    if my_logs:
        day_scores = {i: [] for i in range(7)}
        for log in my_logs:
            day_scores[log.logged_at.weekday()].append(log.score)
            
        avg_scores = {day: np.mean(scores) for day, scores in day_scores.items() if scores}
        if avg_scores:
            lowest_day = min(avg_scores, key=avg_scores.get)
            days = ["Mondays", "Tuesdays", "Wednesdays", "Thursdays", "Fridays", "Saturdays", "Sundays"]
            if avg_scores[lowest_day] < 5:
                patterns.append({
                    "type": "day_of_week",
                    "observation": f"{days[lowest_day]} tend to be the toughest day of the week for you. Be extra gentle with yourself."
                })
                
    # 2. Simultaneous low patterns
    my_dict = {log.logged_at: log.score for log in my_logs}
    p_dict = {log.logged_at: log.score for log in partner_logs}
    common_dates = sorted(list(set(my_dict.keys()).intersection(set(p_dict.keys()))))
    
    low_streak_count = 0
    longest_low_streak = 0
    for d in common_dates:
        if my_dict[d] < 5 and p_dict[d] < 5:
            low_streak_count += 1
            longest_low_streak = max(longest_low_streak, low_streak_count)
        else:
            low_streak_count = 0
            
    if longest_low_streak >= 2:
        patterns.append({
            "type": "simultaneous_low",
            "observation": f"You both experienced a sustained period of low mood recently ({longest_low_streak} days). Remember that you are a team."
        })
        
    return patterns
