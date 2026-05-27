import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import ast


def populate_data_warehouse():
    """Streams cleaned CSV datasets into PostgreSQL and handles missing historical dimensions."""

    # 1. Database Connection Parameters
    DB_USER = "postgres"
    DB_PASS = "Mk1111653*"  # ⚠️ CHANGE TO YOUR ACTUAL POSTGRES PASSWORD
    DB_HOST = "localhost"
    DB_PORT = "5432"
    DB_NAME = "bike_share_dw"

    print("[CONN] Initializing database engine connection...")
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    # 2. Define File Sources
    stations_path = Path("data/raw/dim_stations_raw.csv")
    weather_path = Path("data/raw/dim_weather_raw.csv")
    trips_path = Path("data/processed/fact_trips_clean.csv")

    # 3. Load Dimension: Stations
    if stations_path.exists():
        print("[LOADING] Loading dim_stations into the data warehouse...")
        df_stations = pd.read_csv(stations_path)

        def extract_name(val):
            try:
                parsed_list = ast.literal_eval(val)
                return parsed_list[0]['text']
            except:
                return str(val)

        df_stations['name'] = df_stations['name'].apply(extract_name)
        df_stations = df_stations[['station_id', 'name', 'lat', 'lon', 'capacity']]
        df_stations.to_sql('dim_stations', engine, if_exists='append', index=False)
        print(f"[SUCCESS] Loaded {len(df_stations):,} active stations.")

        # 3.5 The "Ghost Station" Recovery Protocol
        if trips_path.exists():
            print("[AUDIT] Cross-referencing historical trips against active infrastructure...")
            # Read only the IDs to save memory
            df_trip_ids = pd.read_csv(trips_path, usecols=['start_station_id', 'end_station_id'])

            # Find unique IDs in the trip logs vs active stations
            fact_ids = set(df_trip_ids['start_station_id'].dropna()).union(set(df_trip_ids['end_station_id'].dropna()))
            dim_ids = set(df_stations['station_id'])

            missing_ids = fact_ids - dim_ids

            if missing_ids:
                print(f"[RECOVERY] Detected {len(missing_ids)} deactivated/missing stations. Generating archives...")
                df_missing = pd.DataFrame({
                    'station_id': list(missing_ids),
                    'name': 'Archived Station (Removed post-2025)',
                    'lat': 43.6532,  # Default to downtown Toronto coordinates
                    'lon': -79.3832,
                    'capacity': 0
                })
                df_missing.to_sql('dim_stations', engine, if_exists='append', index=False)
                print(f"[SUCCESS] Appended {len(missing_ids)} archived stations to preserve historical integrity.")

    # 4. Load Dimension: Weather
    if weather_path.exists():
        print("[LOADING] Loading dim_weather into the data warehouse...")
        df_weather = pd.read_csv(weather_path)
        df_weather['precipitation_mm'] = df_weather['precipitation_mm'].fillna(0.0)
        df_weather.to_sql('dim_weather', engine, if_exists='append', index=False)
        print(f"[SUCCESS] Loaded {len(df_weather):,} hourly weather metrics.")

    # 5. Load Fact Table: Trips
    if trips_path.exists():
        print("[LOADING] Streaming fact_trips... This will take a minute.")
        chunksize = 100000
        total_rows = 0

        for chunk in pd.read_csv(trips_path, chunksize=chunksize, parse_dates=['start_time', 'end_time']):
            chunk.to_sql('fact_trips', engine, if_exists='append', index=False)
            total_rows += len(chunk)
            print(f" -> Inserted {total_rows:,} rows...")

        print(f"[SUCCESS] Fact table populated with {total_rows:,} clean trip records.")


if __name__ == "__main__":
    populate_data_warehouse()
