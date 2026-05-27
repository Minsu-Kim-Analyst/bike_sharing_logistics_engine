import pandas as pd
import requests
import io
from pathlib import Path


def ingest_historical_weather():
    """Dynamically downloads corresponding hourly weather logs based on trips timeframe."""

    trips_path = Path("data/processed/fact_trips_clean.csv")
    output_path = Path("data/raw/dim_weather_raw.csv")

    if not trips_path.exists():
        print("[ERROR] Clean trips file not found. Please complete the QA Gateway phase first.")
        return

    # 1. Dynamically read timestamps to map our download parameters
    print("[INFO] Auditing trip time boundaries to construct weather timeline...")
    df_trips = pd.read_csv(trips_path, usecols=['start_time'], parse_dates=['start_time'])

    min_date = df_trips['start_time'].min()
    max_date = df_trips['start_time'].max()

    target_year = min_date.year
    target_month = min_date.month

    print(f"[METRICS] Target Window Identified: Year {target_year}, Month {target_month}")
    print(f"[METRICS] Spanning from: {min_date} to {max_date}")

    # 2. Environment Canada Bulk Query Parameterization
    # Station ID 51459 corresponds to the Toronto City Centre Airport weather station (closest to downtown bike core)
    STATION_ID = 51459
    L_TIMEFRAME = 1  # Hourly data identifier

    base_url = "https://climate.weather.gc.ca/climate_data/bulk_data_e.html"

    params = {
        "format": "csv",
        "stationID": STATION_ID,
        "Year": target_year,
        "Month": target_month,
        "Day": 1,
        "timeframe": L_TIMEFRAME
    }

    # 3. Secure the Connection and Execute API Stream
    print(f"[INGESTION] Directing endpoint query to Environment Canada for Station {STATION_ID}...")
    response = requests.get(base_url, params=params)

    if response.status_code == 200:
        print("[SUCCESS] Payload received from federal climate repository. Processing file...")

        # Read directly from the string stream, skipping metadata headers if present
        # Environment Canada CSV data typically has standard column blocks
        weather_df = pd.read_csv(io.StringIO(response.text))

        # 4. Standardize Columns immediately for our Relational Schema
        weather_df.columns = [str(col).strip().lower().replace(" ", "_") for col in weather_df.columns]

        # Dynamically find whatever they named the date/time column this year
        time_col = next((col for col in weather_df.columns if 'date/time' in col), None)
        if time_col:
            weather_df = weather_df.rename(columns={time_col: 'datetime_local'})

        # Select and isolate key analytics components
        keep_cols = {
            'datetime_local': 'datetime_local',
            'temp_(°c)': 'temperature_celsius',
            'precip._amount_(mm)': 'precipitation_mm',
            'wind_spd_(km/h)': 'wind_speed_kmh',
            'stn_press_(kpa)': 'station_pressure_kpa'
        }

        # Verify columns exist before renaming
        existing_rename = {k: v for k, v in keep_cols.items() if k in weather_df.columns}
        weather_df = weather_df[list(existing_rename.keys())].rename(columns=existing_rename)

        # Handle default structural naming quirks for different schema variations
        if 'datetime_local' not in weather_df.columns and 'date/time' in weather_df.columns:
            weather_df = weather_df.rename(columns={'date/time': 'datetime_local'})

        # 5. Export to Local Immutable Raw Directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        weather_df.to_csv(output_path, index=False)
        print(f"[EXPORT] Raw hourly weather observations successfully saved to: {output_path}")
        print("\nSample Environment Log Profile:")
        print(weather_df.head(3))

    else:
        print(f"[ERROR] Failed to fetch climate array. Server HTTP Response: {response.status_code}")


if __name__ == "__main__":
    ingest_historical_weather()