from sqlalchemy.orm import Session
from datetime import datetime, timezone, time
import pytz
import random
import models
from services.push_notifications import send_mood_reminder_notification

def check_and_send_reminders(db: Session):
    """
    Checks all users and sends a mood reminder if:
    1. They haven't logged today in their timezone.
    2. It's between 8 AM and 11 PM in their timezone.
    3. We add a random jitter so everyone doesn't get it at the same minute.
    """
    users = db.query(models.User).filter(models.User.expo_push_token.isnot(None), models.User.profile_complete == True).all()
    
    for user in users:
        # Determine local time
        user_tz_str = user.timezone or "UTC"
        try:
            user_tz = pytz.timezone(user_tz_str)
        except:
            user_tz = pytz.UTC
            
        local_now = datetime.now(user_tz)
        local_date = local_now.date()
        local_hour = local_now.hour
        
        # 1. Check if logged today
        last_log = db.query(models.MoodLog).filter(
            models.MoodLog.user_id == user.id,
            # Use func.date(logged_at) compared to local_date
            # Simplification: check logs in the last 24h as a proxy or exact date match
        ).order_by(models.MoodLog.logged_at.desc()).first()
        
        logged_today = False
        if last_log:
            last_log_local = last_log.logged_at.astimezone(user_tz).date()
            if last_log_local == local_date:
                logged_today = True
                
        if logged_today:
            continue
            
        # 2. Check Active Hours (8 AM to 11 PM)
        if local_hour < 8 or local_hour >= 23:
            continue
            
        # 3. Random Jitter (1 in 4 chance per hour check to spread it out)
        # This means on average they'll get it within 4 hours of entering the active window
        if random.random() > 0.25:
            continue
            
        # Send reminder
        try:
            print(f"[Reminders] Sending reminder to {user.email}")
            send_mood_reminder_notification(user.expo_push_token, user.display_name or "there")
        except Exception as e:
            print(f"[Reminders] Failed for {user.email}: {e}")
