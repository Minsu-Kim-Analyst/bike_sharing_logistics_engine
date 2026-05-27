import requests
import pandas as pd
from pathlib import Path


def fetch_station_data():
    """Fetches live station infrastructure data from the Toronto Bike Share API (v3.0)."""

    # UPGRADED: Using the modern v3.0 endpoint you discovered
    url = "https://toronto.publicbikesystem.net/customer/gbfs/v3.0/station_information"

    print(f"Connecting to modern API: {url}...")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()

        # Navigate the JSON tree to isolate the station list
        stations = data['data']['stations']

        # Convert to a Pandas DataFrame
        df_stations = pd.DataFrame(stations)

        # Filter down to the essential columns for our Star Schema
        cols_to_keep = ['station_id', 'name', 'lat', 'lon', 'capacity']

        # Ensure only columns that actually exist are kept to avoid KeyError
        actual_cols = [col for col in cols_to_keep if col in df_stations.columns]
        df_stations = df_stations[actual_cols]

        print(f"Success! Extracted {len(df_stations)} active stations using GBFS v3.0.")
        return df_stations
    else:
        print(f"Failed to fetch data. HTTP Status: {response.status_code}")
        return None


if __name__ == "__main__":
    # 1. Execute the extraction
    dim_stations = fetch_station_data()

    if dim_stations is not None:
        # 2. Define the output path pointing to your raw data folder
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)

        # 3. Save as an immutable raw CSV file
        output_path = output_dir / "dim_stations_raw.csv"
        dim_stations.to_csv(output_path, index=False)

        print(f"Pipeline complete. Saved raw station data to: {output_path}")