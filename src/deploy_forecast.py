import pandas as pd
import joblib
from sqlalchemy import create_engine
import datetime
from pathlib import Path


def deploy_inventory_forecast():
    """Generates a 24-hour Net Inventory forecast for August 1, 2025."""

    # Database configuration credentials
    DB_USER = "postgres"
    DB_PASS = "Mk1111653*"  # ⚠️ UPDATE THIS TO YOUR ACTUAL POSTGRES PASSWORD
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_NAME = "bike_share_dw"

    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    model_path = Path("models/xgboost_inventory_model.pkl")
    if not model_path.exists():
        print("[ERROR] Model not found. Run train_model.py first.")
        return

    print("[LOADING] Booting Enterprise AI Model...")
    model = joblib.load(model_path)

    # Fetch active stations and compute their average historical outbound volume to seed rolling features
    station_query = """
    SELECT 
        s.station_id, 
        COALESCE(AVG(v.outbound_volume), 0) as historical_avg_outbound
    FROM dim_stations s
    LEFT JOIN view_hourly_inventory_delta v ON s.station_id = v.station_id
    WHERE s.capacity > 0
    GROUP BY s.station_id
    """
    df_stations = pd.read_sql(station_query, engine)

    print("[PROCESSING] Constructing 24-hour prediction matrix for August 1, 2025...")
    target_date = datetime.date(2025, 8, 1)
    hours = list(range(24))

    # Generate the complete Cartesian product grid (Hours * Stations)
    forecast_grid = pd.MultiIndex.from_product(
        [df_stations['station_id'], hours],
        names=['station_id', 'hour_of_day']
    ).to_frame(index=False)

    # Link historical station characteristics back to the grid
    forecast_grid = forecast_grid.merge(df_stations, on='station_id', how='left')

    # Temporal feature calculations for August 1st, 2025 (Friday)
    forecast_grid['day_of_week'] = target_date.weekday()  # 4 = Friday
    forecast_grid['is_weekend'] = 0
    forecast_grid['is_holiday'] = 0

    # Seed the rolling momentum feature with the station's stable history
    forecast_grid['rolling_2hr_outbound'] = forecast_grid['historical_avg_outbound']

    # Grounding deployment variables with true historical summer weather baseline values
    forecast_grid['temperature_celsius'] = 25.0
    forecast_grid['precipitation_mm'] = 0.0
    forecast_grid['wind_speed_kmh'] = 14

    # Strictly align features to match the exact training matrix layout
    features = [
        'station_id', 'hour_of_day', 'day_of_week', 'is_weekend',
        'is_holiday', 'rolling_2hr_outbound',
        'temperature_celsius', 'precipitation_mm', 'wind_speed_kmh'
    ]
    X_predict = forecast_grid[features]

    print("[INFERENCE] Executing XGBoost predictions for Network Inventory Delta...")
    predictions = model.predict(X_predict)

    # Clean, format, and assign timestamp markers to predictions
    forecast_grid['predicted_net_inventory_change'] = predictions.round(0)
    forecast_grid['forecast_datetime'] = pd.to_datetime('2025-08-01') + pd.to_timedelta(forecast_grid['hour_of_day'],
                                                                                        unit='h')

    final_output = forecast_grid[['forecast_datetime', 'station_id', 'predicted_net_inventory_change']]

    print("[EXPORT] Pushing intelligent forecast into PostgreSQL 'fact_forecasts' table...")
    final_output.to_sql('fact_forecasts', engine, if_exists='replace', index=False)

    print(f"[SUCCESS] 24-Hour Forecasting complete. {len(final_output):,} predictions stored.")


if __name__ == "__main__":
    deploy_inventory_forecast()