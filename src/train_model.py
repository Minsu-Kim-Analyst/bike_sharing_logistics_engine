import pandas as pd
import xgboost as xgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error
import joblib
from sqlalchemy import create_engine
import holidays
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "bike_share_dw")
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def train_inventory_optimization_model():
    engine = get_engine()

    print("Extracting feature matrix from Warehouse...")
    query = """
    SELECT v.station_id, v.demand_hour, v.outbound_volume, v.net_inventory_change,
           w.temperature_celsius, w.precipitation_mm, w.wind_speed_kmh
    FROM view_hourly_inventory_delta v
    LEFT JOIN dim_weather w ON v.demand_hour = w.datetime_local
    ORDER BY v.station_id, v.demand_hour;
    """
    df = pd.read_sql(query, engine)

    print("Computing temporal & holiday flags...")
    df['hour_of_day'] = df['demand_hour'].dt.hour
    df['day_of_week'] = df['demand_hour'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

    # Use official ON statutory holidays
    on_holidays = holidays.CA(prov='ON', years=2025)
    df['is_holiday'] = df['demand_hour'].dt.date.apply(lambda x: 1 if x in on_holidays else 0)

    print("Building rolling momentum features...")
    # Grants the AI "short-term memory" of network flow over the past 2 hours
    df['rolling_2hr_outbound'] = df.groupby('station_id')['outbound_volume'].transform(
        lambda x: x.rolling(window=2, min_periods=1).mean().shift(1)).fillna(0)

    # Patch weather gaps
    df['temperature_celsius'] = df['temperature_celsius'].fillna(df['temperature_celsius'].median())
    df['precipitation_mm'] = df['precipitation_mm'].fillna(0)
    df['wind_speed_kmh'] = df['wind_speed_kmh'].fillna(df['wind_speed_kmh'].median())

    features = [
        'station_id', 'hour_of_day', 'day_of_week', 'is_weekend', 
        'is_holiday', 'rolling_2hr_outbound', 'temperature_celsius', 
        'precipitation_mm', 'wind_speed_kmh'
    ]
    
    X = df[features]
    y = df['net_inventory_change']

    print("Initializing Time-Series CV...")
    # TSCV prevents seasonal data leakage (model shouldn't see Dec data to predict July)
    tscv = TimeSeriesSplit(n_splits=3)
    model = xgb.XGBRegressor(n_estimators=200, max_depth=8, learning_rate=0.1, n_jobs=-1, random_state=42)

    fold = 1
    for train_idx, test_idx in tscv.split(X):
        X_train, X_test = X.iloc[train_idx], X.iloc[test_idx]
        y_train, y_test = y.iloc[train_idx], y.iloc[test_idx]
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        print(f" -> TSCV Fold {fold} MAE: {mae:.2f} bikes")
        fold += 1

    print("Compiling final deployment model on complete timeline...")
    model.fit(X, y)

    # Feature Importance profiling
    importances = model.feature_importances_
    feature_weights = pd.DataFrame({
        'Feature': features, 
        'Importance (%)': (importances * 100).round(2)
    }).sort_values(by='Importance (%)', ascending=False)
    
    print("\n--- AI Decision Weights ---")
    print(feature_weights.to_string(index=False))

    Path("models").mkdir(parents=True, exist_ok=True)
    joblib.dump(model, "models/xgboost_inventory_model.pkl")
    print("Model serialized to disk.")

if __name__ == "__main__":
    train_inventory_optimization_model()
