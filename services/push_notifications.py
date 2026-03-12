import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

async def send_push_notification(
    expo_token: str,
    title: str,
    body: str,
    data: dict = {},
    channel_id: str = "nudges"
) -> bool:
    """
    Send a push notification via Expo Push API.
    Returns True if sent successfully, False otherwise.
    Never raises — notification failure must never crash the app.
    """
    if not expo_token or not expo_token.startswith("ExponentPushToken["):
        logger.warning(f"Invalid push token: {expo_token}")
        return False
    
    payload = {
        "to": expo_token,
        "title": title,
        "body": body,
        "data": data,
        "channelId": channel_id,
        "sound": "default",
        "priority": "normal",
    }
    
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                EXPO_PUSH_URL,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            )
            result = response.json()
            
            # Check for Expo-level errors
            if result.get("data", {}).get("status") == "error":
                error = result["data"].get("message", "unknown")
                logger.error(f"Expo push error for {expo_token}: {error}")
                return False
                
            logger.info(f"Push sent successfully to {expo_token[:30]}...")
            return True
            
    except Exception as e:
        logger.error(f"Push notification failed: {e}")
        return False  # Never propagate — notifications are best-effort


async def send_nudge_notification(
    recipient_token: str,
    subject_name: str,
    nudge_message: str,
    nudge_id: str
) -> bool:
    """
    Send a partner nudge push notification.
    The body is warm and human — never clinical.
    """
    # Truncate nudge_message to fit notification body
    body = nudge_message.replace("[name]", subject_name)
    if len(body) > 150:
        body = body[:147] + "..."
    
    return await send_push_notification(
        expo_token=recipient_token,
        title="💜 A moment for you",
        body=body,
        data={
            "type": "partner_nudge",
            "nudge_id": nudge_id,
            "navigate_to": "nudges"
        },
        channel_id="nudges"
    )


async def send_mood_reminder_notification(
    expo_token: str,
    partner_name: str
) -> bool:
    """
    Send daily mood log reminder.
    """
    return await send_push_notification(
        expo_token=expo_token,
        title="How are you feeling today?",
        body=f"Log your mood — {partner_name} is waiting to see 💜",
        data={"type": "mood_reminder", "navigate_to": "log"},
        channel_id="reminders"
    )
