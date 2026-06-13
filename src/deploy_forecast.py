import pandas as pd
import joblib
from sqlalchemy import create_engine
import datetime
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

def deploy_scenario_forecast(start_date, days=3):
    engine = get_engine()
    model = joblib.load("models/xgboost_inventory_model.pkl")

    # Get baseline historical outbound to seed the rolling momentum features
    station_query = "SELECT station_id, COALESCE(AVG(outbound_volume), 0) as historical_avg FROM view_hourly_inventory_delta GROUP BY station_id"
    df_stations = pd.read_sql(station_query, engine)

    print(f"Generating {days}-day Stress Test Scenario starting {start_date}...")
    dates = [start_date + datetime.timedelta(days=i) for i in range(days)]
    hours = list(range(24))

    # Grid: Days * Stations * Hours
    grid = pd.MultiIndex.from_product([dates, df_stations['station_id'], hours], names=['date', 'station_id', 'hour_of_day']).to_frame(index=False)
    grid = grid.merge(df_stations, on='station_id')

    # Apply Scenario Logic
    grid['day_of_week'] = grid['date'].dt.weekday
    grid['is_weekend'] = grid['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)
    grid['is_holiday'] = 0 
    grid['rolling_2hr_outbound'] = grid['historical_avg']
    
    # THE HEATWAVE STRESS TEST: Blistering 32 degrees, no wind, no rain
    grid['temperature_celsius'] = 32.0 
    grid['precipitation_mm'] = 0.0
    grid['wind_speed_kmh'] = 5

    features = ['station_id', 'hour_of_day', 'day_of_week', 'is_weekend', 'is_holiday', 'rolling_2hr_outbound', 'temperature_celsius', 'precipitation_mm', 'wind_speed_kmh']
    
    # Inference
    grid['predicted_net_inventory_change'] = model.predict(grid[features]).round(0)
    grid['forecast_datetime'] = pd.to_datetime(grid['date']) + pd.to_timedelta(grid['hour_of_day'], unit='h')

    # Export
    grid[['forecast_datetime', 'station_id', 'predicted_net_inventory_change']].to_sql('fact_forecasts', engine, if_exists='replace', index=False)
    print(f"Scenario storage complete: {len(grid)} rows in fact_forecasts.")

if __name__ == "__main__":
    # Target: A peak summer Friday in 2026
    start = datetime.datetime(2026, 8, 7)
    deploy_scenario_forecast(start)
