
import os
import sys
import pickle
import numpy as np

# Mocking paths
MODELS_DIR = r"c:\Users\21meh\OneDrive\Desktop\MoodRing\backend\models"
MODEL_PATH = os.path.join(MODELS_DIR, 'v1.pkl')
SCALER_PATH = os.path.join(MODELS_DIR, 'scaler_v1.pkl')

print(f"Checking paths:\n{MODEL_PATH}\n{SCALER_PATH}")
print(f"Model exists: {os.path.exists(MODEL_PATH)}")
print(f"Scaler exists: {os.path.exists(SCALER_PATH)}")

try:
    with open(MODEL_PATH, 'rb') as f:
        classifier = pickle.load(f)
    with open(SCALER_PATH, 'rb') as f:
        scaler = pickle.load(f)
    print("✅ Model and Scaler loaded successfully!")
    
    # Test prediction with dummy data
    # features: mood_delta_7d, sentiment_trend, response_lag_hours, calendar_stress, streak_broken, volatility_score, low_score_overlap
    dummy_X = np.array([2.0, -0.5, 4.0, 0.8, 1, 2.5, 3]).reshape(1, -1)
    scaled = scaler.transform(dummy_X)
    prob = classifier.predict_proba(scaled)[0][1]
    print(f"Dummy prediction probability: {prob}")
    
except Exception as e:
    print(f"❌ Error: {e}")
