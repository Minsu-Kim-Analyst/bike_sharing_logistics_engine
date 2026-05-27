import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib
from pathlib import Path


def train_inventory_optimization_model():
    print("[LOADING] Ingesting advanced feature matrix...")
    df = pd.read_csv("data/processed/advanced_feature_matrix.csv")

    # 1. Feature Selection (Excluding manually added event features)
    features = [
        'station_id', 'hour_of_day', 'day_of_week', 'is_weekend',
        'is_holiday', 'rolling_2hr_outbound',
        'temperature_celsius', 'precipitation_mm', 'wind_speed_kmh'
    ]
    target = 'net_inventory_change'

    X = df[features]
    y = df[target]

    print("[PROCESSING] Splitting training data...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print("[TRAINING] Initializing XGBoost Regressor for Net Inventory Forecasting...")
    model = xgb.XGBRegressor(n_estimators=200, max_depth=8, learning_rate=0.1, n_jobs=-1, random_state=42)
    model.fit(X_train, y_train)

    print("[EVALUATION] Testing algorithm accuracy...")
    predictions = model.predict(X_test)
    mae = mean_absolute_error(y_test, predictions)

    print("\n" + "=" * 50)
    print("      INVENTORY OPTIMIZATION MODEL METRICS        ")
    print("=" * 50)
    print(f"Mean Absolute Error (Net Change) : {mae:.2f} bikes")
    print("=" * 50)

    # 2. Extract Feature Importance (Explainable AI)
    importances = model.feature_importances_
    feature_weights = pd.DataFrame({
        'Feature': features,
        'Importance': importances
    }).sort_values(by='Importance', ascending=False)

    # Format as percentages for executive readability
    feature_weights['Importance (%)'] = (feature_weights['Importance'] * 100).round(2)

    print("\n" + "=" * 50)
    print("        AI DECISION DRIVERS (FEATURE IMPORTANCE)  ")
    print("=" * 50)
    print(feature_weights[['Feature', 'Importance (%)']].to_string(index=False))
    print("=" * 50)

    # Export the final trained model artifact
    Path("models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, "models/xgboost_inventory_model.pkl")
    print("\n[EXPORT] Enterprise Model compiled and saved.")


if __name__ == "__main__":
    train_inventory_optimization_model()