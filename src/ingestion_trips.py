import pandas as pd
from pathlib import Path


def process_trip_data(file_name):
    """Loads raw trip data, enforces schema standardization, and strips bloat."""

    # 1. Define Paths
    raw_path = Path(f"data/raw/{file_name}")
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)

    if not raw_path.exists():
        print(f"❌ ERROR: Could not find {raw_path}. Did you misspell the file name?")
        return

    print(f"Loading raw dataset from {raw_path}... (This might take a moment)")

    # 2. Read CSV (low_memory=False handles mixed data types in messy open data)
    df = pd.read_csv(raw_path, low_memory=False, encoding='latin-1')
    print(f"Loaded {len(df):,} raw rides.")

    # 3. Standardize all column names (lowercase, strip whitespace, replace spaces with underscores)
    df.columns = [str(col).strip().lower().replace(" ", "_") for col in df.columns]

    # Account for known typos in Toronto Open Data history
    rename_map = {
        'trip__duration': 'trip_duration_seconds',
        'trip_duration': 'trip_duration_seconds',
        'duration': 'trip_duration_seconds'
    }
    df = df.rename(columns=rename_map)

    # 4. Enforce Star Schema (Drop redundant text columns)
    # We only keep IDs, metrics, and timestamps.
    cols_to_keep = [
        'trip_id', 'trip_duration_seconds',
        'start_station_id', 'start_time',
        'end_station_id', 'end_time',
        'bike_id', 'user_type', 'bike_model'
    ]

    # Only keep columns that actually exist in the dataframe to prevent KeyError
    actual_cols = [c for c in cols_to_keep if c in df.columns]
    df = df[actual_cols]

    # 5. Type Casting (Convert string times to true Datetime objects)
    print("Converting timestamps to datetime objects...")
    df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
    df['end_time'] = pd.to_datetime(df['end_time'], errors='coerce')

    # 6. Save the cleaned base table
    output_path = processed_dir / "fact_trips_base.csv"
    df.to_csv(output_path, index=False)

    print(f"✅ Success! Standardized fact table saved to: {output_path}")
    print("Current Schema:")
    print(df.dtypes)


if __name__ == "__main__":
    # ⚠️ CHANGE THIS STRING TO THE EXACT NAME OF YOUR RAW CSV FILE
    TARGET_FILE = "bikeshare_2025_07.csv"

    process_trip_data(TARGET_FILE)