import os
import pickle
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# Ensure the models directory exists
MODELS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'models'))
os.makedirs(MODELS_DIR, exist_ok=True)

MODEL_PATH = os.path.join(MODELS_DIR, 'v1.pkl')
SCALER_PATH = os.path.join(MODELS_DIR, 'scaler_v1.pkl')

def generate_synthetic_data(n_samples=500):
    """
    Generates synthetic data for 7 features:
    1. mood_delta_7d: (-9.0 to 9.0)
    2. sentiment_trend: (-2.0 to 2.0)
    3. response_lag_hours: (0.0 to 48.0)
    4. calendar_stress: (0.0 to 1.0)
    5. streak_broken: (0 or 1)
    6. volatility_score: (0.0 to 5.0)
    7. low_score_overlap: (0 to 7)
    """
    np.random.seed(42)
    
    mood_delta_7d = np.random.uniform(-5.0, 5.0, n_samples)
    sentiment_trend = np.random.uniform(-1.0, 1.0, n_samples)
    response_lag = np.random.uniform(0.0, 12.0, n_samples)
    calendar_stress = np.random.uniform(0.0, 1.0, n_samples)
    streak_broken = np.random.randint(0, 2, n_samples)
    volatility = np.random.uniform(0.5, 3.5, n_samples)
    low_score_overlap = np.random.randint(0, 4, n_samples)
    
    X = np.column_stack([
        mood_delta_7d,
        sentiment_trend,
        response_lag,
        calendar_stress,
        streak_broken,
        volatility,
        low_score_overlap
    ])
    
    # Generate labels (p_stress target 0 or 1)
    # Primary stress signals: high mood divergence, simultaneous lows, broken streak
    # Secondary: negative sentiment trend, high response lag, calendar stress, volatility
    hidden_score = (
        np.abs(mood_delta_7d) * 1.5 +      # primary: divergence is the strongest signal
        (-sentiment_trend) * 1.0 +           # secondary: negative sentiment compounds stress
        (response_lag / 12.0) * 0.5 +        # secondary: slow responses add tension
        calendar_stress * 0.8 +              # secondary
        streak_broken * 1.2 +               # primary: broken engagement pattern
        volatility * 0.6 +                  # secondary
        low_score_overlap * 1.8             # primary: both partners low at the same time
    )
    
    # Normalize hidden score roughly around 0
    hidden_score = hidden_score - np.mean(hidden_score)
    
    # Sigmoid probability
    probs = 1 / (1 + np.exp(-hidden_score))
    
    y = (probs > 0.5).astype(int)
    
    return X, y


def train_baseline_model():
    print("Generating synthetic data for 7 features...")
    X, y = generate_synthetic_data(500)
    
    print("Training StandardScaler...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    print("Training LogisticRegression model...")
    model = LogisticRegression(random_state=42, class_weight='balanced')
    model.fit(X_scaled, y)
    
    print("\n--- Model Coefficients ---")
    features = [
        "mood_delta_7d",
        "sentiment_trend",
        "response_lag_hours",
        "calendar_stress",
        "streak_broken",
        "volatility_score",
        "low_score_overlap"
    ]
    for name, coef in zip(features, model.coef_[0]):
        print(f"{name:>20}: {coef:.4f}")
        
    # Save the artifacts
    with open(MODEL_PATH, 'wb') as f:
        pickle.dump(model, f)
    with open(SCALER_PATH, 'wb') as f:
        pickle.dump(scaler, f)
        
    print(f"\n✅ Model saved to {MODEL_PATH}")
    print(f"✅ Scaler saved to {SCALER_PATH}")

if __name__ == "__main__":
    train_baseline_model()
