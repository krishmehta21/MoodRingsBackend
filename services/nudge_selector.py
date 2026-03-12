import json
import os
import random
from datetime import datetime
from typing import Dict, List, Optional
from services.ml.forecaster import ForecastResult

# Load the suggestions at module startup
SUGGESTIONS_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "partner_nudge_suggestions.json"))
_NUDGE_DATASET: List[Dict] = []

try:
    if os.path.exists(SUGGESTIONS_PATH):
        with open(SUGGESTIONS_PATH, "r") as f:
            _NUDGE_DATASET = json.load(f)
except Exception as e:
    # We should log this in a real app
    print(f"Failed to load nudge suggestions: {e}")

def select_partner_nudge(
    forecast: ForecastResult,
    partner_score: float,
    time_of_day: str  # "morning" | "afternoon" | "evening" | "night"
) -> Optional[Dict]:
    """
    Selects a nudge from the dataset based on mood context and time of day.
    """
    if not _NUDGE_DATASET:
        return None

    # 1. Determine mood_context
    today_dayname = datetime.now().strftime("%A").lower()
    
    if forecast.pattern_detected and f"low_on_{today_dayname}s" == forecast.pattern_detected:
        mood_context = "partner_low_recurring"
    elif partner_score < 4 and forecast.slope_7d < -0.3:
        mood_context = "both_declining"
    elif forecast.predicted_score_24h < 3.0:
        mood_context = "partner_declining_severe"
    elif forecast.predicted_score_24h < 5.0:
        mood_context = "partner_declining_moderate"
    else:
        mood_context = "partner_declining_mild"

    # 2. Filter suggestions
    matches = [
        n for n in _NUDGE_DATASET 
        if n.get("mood_context") == mood_context and 
        (time_of_day in n.get("time_of_day", []) or "any" in n.get("time_of_day", []))
    ]

    # 3. Fallback to just mood_context if no time-of-day matches
    if not matches:
        matches = [n for n in _NUDGE_DATASET if n.get("mood_context") == mood_context]

    # 4. Final selection
    if not matches:
        return None
        
    return random.choice(matches)
