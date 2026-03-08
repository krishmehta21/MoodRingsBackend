import datetime
from typing import List, Dict, Optional

SUGGESTIONS = [
    # Tier: Soft
    {
        "id": "soft_1",
        "tier": "soft",
        "mood_context": "any",
        "time_of_day": "evening",
        "message": "You've both had a long day. Put your phones down for 20 minutes and just be in the same room.",
        "actions": ["Silence phones", "20 mins quality time"]
    },
    {
        "id": "soft_2",
        "tier": "soft",
        "mood_context": "high_stress",
        "time_of_day": "morning",
        "message": "Today looks heavy. Send a simple 'thinking of you' text at noon.",
        "actions": ["Set a reminder", "Send a brief text"]
    },
    {
        "id": "soft_3",
        "tier": "soft",
        "mood_context": "diverging",
        "time_of_day": "any",
        "message": "You're feeling a bit out of sync. Ask: 'What's one small thing I can do to make your day better?'",
        "actions": ["Send the question", "Listen without advice"]
    },
    {
        "id": "soft_4",
        "tier": "soft",
        "mood_context": "one_low",
        "time_of_day": "evening",
        "message": "Your partner seems low. A simple 30-second hug can lower their cortisol levels.",
        "actions": ["Initiate a hug", "No words needed"]
    },
    {
        "id": "soft_5",
        "tier": "soft",
        "mood_context": "both_low",
        "time_of_day": "any",
        "message": "It's been a tough day for both of you. Give each other permission to just 'be' without any chores.",
        "actions": ["Cancel one chore", "Relax together"]
    },
    {
        "id": "soft_6",
        "tier": "soft",
        "mood_context": "any",
        "time_of_day": "afternoon",
        "message": "Take a 5-minute walk together when you're both home. Fresh air helps reset the mood.",
        "actions": ["Walk together", "Leave phones behind"]
    },
    {
        "id": "soft_7",
        "tier": "soft",
        "mood_context": "any",
        "time_of_day": "morning",
        "message": "Start the day with a shared cup of coffee/tea before jumping into work tasks.",
        "actions": ["Brew together", "5 mins of chat"]
    },

    # Tier: Active
    {
        "id": "active_1",
        "tier": "active",
        "mood_context": "any",
        "time_of_day": "any",
        "message": "Order food from that place you both love tonight. No cooking, no effort, just together.",
        "actions": ["Pick the restaurant", "Order delivery"]
    },
    {
        "id": "active_2",
        "tier": "active",
        "mood_context": "high_stress",
        "time_of_day": "evening",
        "message": "Stress is high. Do a 10-minute guided meditation together before sleep.",
        "actions": ["Find a 10m track", "Dim the lights"]
    },
    {
        "id": "active_3",
        "tier": "active",
        "mood_context": "diverging",
        "time_of_day": "any",
        "message": "Sync your calendars. Find one 1-hour slot this week for an intentional date.",
        "actions": ["Open calendars", "Pick a 1-hour slot"]
    },
    {
        "id": "active_4",
        "tier": "active",
        "mood_context": "both_low",
        "time_of_day": "afternoon",
        "message": "You're both drained. Skip the gym or errands today and nap for 30 minutes together.",
        "actions": ["Lay down together", "30 min timer"]
    },
    {
        "id": "active_5",
        "tier": "active",
        "mood_context": "one_low",
        "time_of_day": "any",
        "message": "Plan a small surprise. Maybe their favorite snack or a song you both like.",
        "actions": ["Get the snack/song", "Present it casually"]
    },
    {
        "id": "active_6",
        "tier": "active",
        "mood_context": "any",
        "time_of_day": "morning",
        "message": "Write a 2-sentence appreciation note and leave it where they'll find it.",
        "actions": ["Find a sticky note", "Write something kind"]
    },
    {
        "id": "active_7",
        "tier": "active",
        "mood_context": "high_stress",
        "time_of_day": "evening",
        "message": "Give each other a 10-minute shoulder or foot rub to decompress.",
        "actions": ["Set a 10 min timer", "Take turns"]
    },
    {
        "id": "active_8",
        "tier": "active",
        "mood_context": "any",
        "time_of_day": "any",
        "message": "Put on a playlist of 'your' songs and cook something simple together.",
        "actions": ["Start the playlist", "Cook together"]
    },

    # Tier: Priority
    {
        "id": "priority_1",
        "tier": "priority",
        "mood_context": "high_stress",
        "time_of_day": "evening",
        "message": "You two have been ships passing in the night. Block 30 minutes tonight — no phones, no agenda, just check in.",
        "actions": ["30 mins no phones", "Direct eye contact"]
    },
    {
        "id": "priority_2",
        "tier": "priority",
        "mood_context": "both_low",
        "time_of_day": "any",
        "message": "Burnout alert. Cancel all non-essential plans for the next 48 hours to recover together.",
        "actions": ["Cancel one plan", "Stock up on comfort food"]
    },
    {
        "id": "priority_3",
        "tier": "priority",
        "mood_context": "diverging",
        "time_of_day": "evening",
        "message": "The gap is widening. Use 'The State of the Union' check-in: 'What went well this week? Where do we need to sync?'",
        "actions": ["Ask the questions", "No interruptions"]
    },
    {
        "id": "priority_4",
        "tier": "priority",
        "mood_context": "any",
        "time_of_day": "any",
        "message": "High stress detected. It's time for a 'Relationship Reset' — go for a long walk and talk without distractions.",
        "actions": ["Go for a 30m walk", "Address the stressor"]
    },
    {
        "id": "priority_5",
        "tier": "priority",
        "mood_context": "one_low",
        "time_of_day": "evening",
        "message": "Your partner is struggling. Take over all household duties for tonight so they can rest completely.",
        "actions": ["Handle chores", "Encourage their rest"]
    },
    {
        "id": "priority_6",
        "tier": "priority",
        "mood_context": "both_low",
        "time_of_day": "morning",
        "message": "Tough start. Send each other one thing you're grateful for about the other right now.",
        "actions": ["Identify 1 gratitude", "Send it now"]
    },
    {
        "id": "priority_7",
        "tier": "priority",
        "mood_context": "high_stress",
        "time_of_day": "afternoon",
        "message": "Stress levels are critical. Commit to one 'no-stress' hour tonight. No talking about work, money, or kids.",
        "actions": ["Define the hour", "Redirect stress talk"]
    },
    {
        "id": "priority_8",
        "tier": "priority",
        "mood_context": "diverging",
        "time_of_day": "any",
        "message": "Mismatch found. Acknowledge it: 'I feel like we're on different pages. How are you really doing?'",
        "actions": ["Say the words", "Listen deeply"]
    },
    {
        "id": "priority_9",
        "tier": "priority",
        "mood_context": "any",
        "time_of_day": "evening",
        "message": "Reconnect tonight. Shared ritual: Play a board game or look through old photos together.",
        "actions": ["Pick an activity", "Engage fully"]
    },
    {
        "id": "priority_10",
        "tier": "priority",
        "mood_context": "high_stress",
        "time_of_day": "morning",
        "message": "Big Day ahead. Give each other a long hug (20+ seconds) before you part ways.",
        "actions": ["20 second hug", "Deep breath together"]
    }
]

def get_current_time_of_day() -> str:
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 17:
        return "afternoon"
    elif 17 <= hour < 22:
        return "evening"
    else:
        return "any" # Night/Late

def select_best_suggestion(p_stress: float, u_score: int, p_score: int) -> Dict:
    """
    Selects the most appropriate suggestion based on:
    - p_stress (tier threshold)
    - Relationship between u_score and p_score (mood_context)
    - Current time of day
    """
    # 1. Determine Tier
    if p_stress > 0.85:
        tier = "priority"
    elif p_stress > 0.70:
        tier = "active"
    else:
        tier = "soft"

    # 2. Determine Mood Context
    context = "any"
    if u_score < 4 and p_score < 4:
        context = "both_low"
    elif (u_score < 4 or p_score < 4) and abs(u_score - p_score) < 3:
        context = "one_low"
    elif abs(u_score - p_score) >= 4:
        context = "diverging"
    elif p_stress > 0.75:
        context = "high_stress"

    time_of_day = get_current_time_of_day()

    # 3. Filter and Rank
    # Priority 1: Match Tier + Context + Time
    # Priority 2: Match Tier + Context + "any" Time
    # Priority 3: Match Tier + "any" Context + Time
    # Priority 4: Match Tier + "any" Context + "any" Time
    
    tier_matches = [s for s in SUGGESTIONS if s["tier"] == tier]
    
    # Attempt 1: Tier + Context + Time
    matches = [s for s in tier_matches if s["mood_context"] == context and s["time_of_day"] == time_of_day]
    if matches: return matches[0]

    # Attempt 2: Tier + Context + "any"
    matches = [s for s in tier_matches if s["mood_context"] == context and (s["time_of_day"] == "any" or s["time_of_day"] == time_of_day)]
    if matches: return matches[0]

    # Attempt 3: Tier + "any" + Time
    matches = [s for s in tier_matches if (s["mood_context"] == "any" or s["mood_context"] == context) and s["time_of_day"] == time_of_day]
    if matches: return matches[0]

    # Fallback: Just Tier
    return tier_matches[0]
