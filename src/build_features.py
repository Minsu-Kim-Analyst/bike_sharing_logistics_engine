import pandas as pd
from sqlalchemy import create_engine
import holidays
from pathlib import Path
import os
from dotenv import load_dotenv

# Load the secret vault
load_dotenv()

def build_feature_matrix():
    # Pull the passwords securely from the .env file
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    query = """
    SELECT 
        v.station_id,
        v.demand_hour,
        v.inbound_volume,
        v.outbound_volume,
        v.net_inventory_change,
        w.temperature_celsius,
        w.precipitation_mm,
        w.wind_speed_kmh
    FROM view_hourly_inventory_delta v
    LEFT JOIN dim_weather w ON v.demand_hour = w.datetime_local
    ORDER BY v.station_id, v.demand_hour;
    """

    print("[EXTRACTION] Pulling Net Inventory Delta and climate context...")
    df = pd.read_sql(query, engine)

    print("[ENGINEERING] Generating temporal and holiday features...")
    df['hour_of_day'] = df['demand_hour'].dt.hour
    df['day_of_week'] = df['demand_hour'].dt.dayofweek
    df['is_weekend'] = df['day_of_week'].apply(lambda x: 1 if x >= 5 else 0)

    on_holidays = holidays.CA(prov='ON', years=2025)
    df['is_holiday'] = df['demand_hour'].dt.date.apply(lambda x: 1 if x in on_holidays else 0)

    print("[ENGINEERING] Calculating rolling 2-hour departure momentum...")
    df = df.sort_values(by=['station_id', 'demand_hour'])
    df['rolling_2hr_outbound'] = df.groupby('station_id')['outbound_volume'].transform(
        lambda x: x.rolling(window=2, min_periods=1).mean().shift(1))
    df['rolling_2hr_outbound'] = df['rolling_2hr_outbound'].fillna(0)

    # Clean missing weather
    df['temperature_celsius'] = df['temperature_celsius'].fillna(df['temperature_celsius'].median())
    df['precipitation_mm'] = df['precipitation_mm'].fillna(0)
    df['wind_speed_kmh'] = df['wind_speed_kmh'].fillna(df['wind_speed_kmh'].median())

    output_path = Path("data/processed/advanced_feature_matrix.csv")
    df.to_csv(output_path, index=False)

    print(f"\n[SUCCESS] Feature Matrix built with {len(df):,} rows.")


if __name__ == "__main__":
    build_feature_matrix()