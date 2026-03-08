import datetime
import logging
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

def get_calendar_stress_score(access_token: str) -> float:
    """
    Fetches events for the next 7 days using the provided OAuth token.
    Calculates a stress score (0.0 to 1.0) based on event density and duration.
    """
    if not access_token:
        # If no strict calendar token is available, return base score
        return 0.0

    try:
        creds = Credentials(token=access_token)
        service = build('calendar', 'v3', credentials=creds)

        # Get current time and time 7 days from now
        now = datetime.datetime.utcnow()
        timeMin = now.isoformat() + 'Z'  # 'Z' indicates UTC time
        timeMax = (now + datetime.timedelta(days=7)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary', timeMin=timeMin, timeMax=timeMax,
            singleEvents=True, orderBy='startTime').execute()
        
        events = events_result.get('items', [])

        if not events:
            return 0.0

        total_duration_hours = 0.0
        event_count = len(events)

        for event in events:
            # We ONLY process dates/times to compute duration. We drop titles/descriptions.
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            # Parse strings to datetime
            try:
                # Some all-day events just have 'date' like '2023-10-01'
                if len(start) == 10:
                    dt_start = datetime.datetime.strptime(start, '%Y-%m-%d')
                    dt_end = datetime.datetime.strptime(end, '%Y-%m-%d')
                else:
                    # ISO format datetime
                    dt_start = datetime.datetime.fromisoformat(start.replace('Z', '+00:00'))
                    dt_end = datetime.datetime.fromisoformat(end.replace('Z', '+00:00'))

                duration = (dt_end - dt_start).total_seconds() / 3600.0
                total_duration_hours += duration
            except Exception as e:
                logger.warning(f"Failed to parse event dates: {e}")
                pass

        # Calculate Stress Score
        # Assume 40 hours of events over 7 days is 100% (1.0) stress
        # Base stress from duration
        duration_stress = min(1.0, total_duration_hours / 40.0)
        
        # Base stress from count (assume > 20 events is high context switching)
        count_stress = min(1.0, event_count / 20.0)

        # Blended score (70% duration density, 30% frequency density)
        final_score = (duration_stress * 0.7) + (count_stress * 0.3)

        return round(final_score, 3)

    except HttpError as error:
        # Could happen if token is expired, revoked, or insufficient scopes
        logger.error(f"Google Calendar API error: {error}")
        return 0.0
    except Exception as e:
        logger.error(f"Unexpected error in calendar service: {e}")
        return 0.0
