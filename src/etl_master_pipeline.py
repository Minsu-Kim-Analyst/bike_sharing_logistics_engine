import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import os
import glob
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "bike_share_dw")
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def run_etl_pipeline():
    engine = get_engine()
    # Recursively grab all monthly logs
    raw_files = glob.glob("data/raw/bikeshare-ridership-2025/**/*.csv", recursive=True)
    quarantine_dir = Path("data/quarantine")
    quarantine_dir.mkdir(parents=True, exist_ok=True)

    if not raw_files:
        print("No raw CSVs found in data/raw/bikeshare-2025-ridership/")
        return

    # Load active infrastructure to memory for cross-referencing
    try:
        active_stations = pd.read_sql("SELECT station_id FROM dim_stations", engine)['station_id'].tolist()
        active_stations = set(active_stations)
    except:
        # Fallback if DB isn't seeded yet
        df_stations = pd.read_csv("data/raw/dim_stations_raw.csv")
        df_stations.to_sql('dim_stations', engine, if_exists='replace', index=False)
        active_stations = set(df_stations['station_id'])

    total_clean, total_quarantine, total_ghosts = 0, 0, 0
    print(f"Initiating ETL for {len(raw_files)} ledgers...")

    for file_path in raw_files:
        filename = os.path.basename(file_path)
        print(f" -> Processing {filename}...")

        # low_memory=False required for mixed open-data types
        df = pd.read_csv(file_path, low_memory=False, encoding='latin-1')
        df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]
        
        # Account for Open Data naming changes over the year
        rename_map = {'trip__duration': 'trip_duration_seconds', 'trip_duration': 'trip_duration_seconds', 'duration': 'trip_duration_seconds'}
        df = df.rename(columns=rename_map)

        cols_to_keep = ['trip_id', 'trip_duration_seconds', 'start_station_id', 'start_time', 'end_station_id', 'end_time', 'bike_id', 'user_type', 'bike_model']
        df = df[[c for c in cols_to_keep if c in df.columns]]

        df = df.dropna(subset=['trip_id', 'start_station_id', 'end_station_id'])
        df['start_station_id'] = df['start_station_id'].astype(int)
        df['end_station_id'] = df['end_station_id'].astype(int)

        # GHOST STATION RECOVERY PROTOCOL
        # The network removes/adds docks. If historical trips reference a dead dock,
        # we inject a dummy record to preserve the trip ledger rather than dropping the row.
        fact_ids = set(df['start_station_id']).union(set(df['end_station_id']))
        missing_ids = fact_ids - active_stations

        if missing_ids:
            df_missing = pd.DataFrame({
                'station_id': list(missing_ids), 'name': 'Archived Historical Station',
                'lat': 43.6532, 'lon': -79.3832, 'capacity': 0
            })
            df_missing.to_sql('dim_stations', engine, if_exists='append', index=False)
            active_stations.update(missing_ids) # Update cache to avoid redundant inserts
            total_ghosts += len(missing_ids)

        # DATA QUALITY GATEWAY (IQR FIREWALL)
        # Catch mechanical glitches (e.g., 5-second trips or docks failing to close trips)
        Q1 = df['trip_duration_seconds'].quantile(0.25)
        Q3 = df['trip_duration_seconds'].quantile(0.75)
        IQR = Q3 - Q1
        upper_bound = Q3 + (1.5 * IQR)
        lower_bound = 60 # Hard floor for false-starts

        valid_mask = (df['trip_duration_seconds'] >= lower_bound) & (df['trip_duration_seconds'] <= upper_bound)
        df_clean = df[valid_mask].copy()
        df_quarantine = df[~valid_mask].copy()

        # Route bad rows to disk for auditing
        if not df_quarantine.empty:
            df_quarantine['quarantine_reason'] = 'ERR_DURATION_OUT_OF_BOUNDS'
            df_quarantine.to_csv(quarantine_dir / f"quarantine_{filename}", index=False)
            total_quarantine += len(df_quarantine)

        df_clean['start_time'] = pd.to_datetime(df_clean['start_time'], errors='coerce')
        df_clean['end_time'] = pd.to_datetime(df_clean['end_time'], errors='coerce')
        
        # BULK UPSERT TO POSTGRES
        # Replaced pandas .to_sql with psycopg2 execute_values to handle Primary Key conflicts cleanly
        records = df_clean.values.tolist()
        insert_query = """
            INSERT INTO fact_trips (
                trip_id, trip_duration_seconds, start_station_id, start_time, 
                end_station_id, end_time, bike_id, user_type, bike_model
            ) VALUES %s 
            ON CONFLICT (trip_id) DO NOTHING;
        """
        
        # Tap into the raw connection for maximum speed using explicit try/finally block
        conn = engine.raw_connection()
        try:
            with conn.cursor() as cursor:
                psycopg2.extras.execute_values(cursor, insert_query, records, page_size=10000)
            conn.commit()
        finally:
            conn.close() # Explicitly return the connection to the pool to prevent memory leaks
            
        total_clean += len(df_clean)

    print("\nETL Pipeline Complete.")
    print(f"Clean Rows: {total_clean:,} | Quarantined: {total_quarantine:,} | Ghosts recovered: {total_ghosts:,}")

if __name__ == "__main__":
    run_etl_pipeline()
