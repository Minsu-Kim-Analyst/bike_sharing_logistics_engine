import pandas as pd
import requests
import io
from sqlalchemy import create_engine, text
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

def ingest_full_year_weather():
    STATION_ID = 51459 
    L_TIMEFRAME = 1 
    base_url = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"
    engine = get_engine()

    # PRE-FLIGHT SWEEP: Clear any existing 2025 records to prevent Primary Key crashes
    # This ensures the backfill starts with a clean slate for the target year
    print("Executing pre-flight sweep: Clearing legacy 2025 weather records...")
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dim_weather WHERE EXTRACT(year FROM datetime_local) = 2025"))

    print("Pinging Env Canada for fresh 2025 climate array...")

    for month in range(1, 13):
        print(f" -> Pulling Month {month:02d}/2025...")
        params = {"format": "csv", "stationID": STATION_ID, "Year": 2025, "Month": month, "Day": 1, "timeframe": L_TIMEFRAME}
        response = requests.get(base_url, params=params)

        if response.status_code == 200:
            df = pd.read_csv(io.StringIO(response.text))
            
            df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

            time_col = next((col for col in df.columns if 'date/time' in col), None)
            if time_col: df = df.rename(columns={time_col: 'datetime_local'})

            keep_cols = {
                'datetime_local': 'datetime_local', 'temp_(°c)': 'temperature_celsius',
                'precip._amount_(mm)': 'precipitation_mm', 'wind_spd_(km/h)': 'wind_speed_kmh',
                'stn_press_(kpa)': 'station_pressure_kpa'
            }
            existing_rename = {k: v for k, v in keep_cols.items() if k in df.columns}
            df = df[list(existing_rename.keys())].rename(columns=existing_rename)

            df['precipitation_mm'] = df['precipitation_mm'].fillna(0.0)
            
            df.to_sql('dim_weather', engine, if_exists='append', index=False)
        else:
            print(f"Failed Month {month}. HTTP: {response.status_code}")

    print("2025 Weather Pipeline Complete.")

if __name__ == "__main__":
    ingest_full_year_weather()
