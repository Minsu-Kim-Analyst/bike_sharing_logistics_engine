import requests
import pandas as pd
from pathlib import Path

def fetch_station_data():
    # Using modern v3.0 endpoint (v2 is deprecated and drops capacity fields)
    url = "https://toronto.publicbikesystem.net/customer/gbfs/v3.0/station_information"
    print(f"Connecting to API: {url}...")
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        stations = data['data']['stations']
        df_stations = pd.DataFrame(stations)
        
        # Strip bloat, keep only core physical attributes for the star schema
        cols_to_keep = ['station_id', 'name', 'lat', 'lon', 'capacity']
        actual_cols = [col for col in cols_to_keep if col in df_stations.columns]
        df_stations = df_stations[actual_cols]

        print(f"Extracted {len(df_stations)} active stations.")
        return df_stations
    else:
        print(f"API Error. HTTP Status: {response.status_code}")
        return None

if __name__ == "__main__":
    dim_stations = fetch_station_data()
    if dim_stations is not None:
        output_dir = Path("data/raw")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save as immutable raw baseline
        output_path = output_dir / "dim_stations_raw.csv"
        dim_stations.to_csv(output_path, index=False)
        print(f"Saved raw station data to: {output_path}")
