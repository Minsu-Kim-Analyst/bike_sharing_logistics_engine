import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import os
from dotenv import load_dotenv

# Load credentials from your .env file
load_dotenv()

def get_engine():
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "bike_share_dw")
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def export_dashboard_data():
    engine = get_engine()
    
    # This query joins our AI forecasts with the station geometry (lat/lon)
    # to create the geospatial dataset required for Tableau map plotting.
    query = """
    SELECT 
        f.forecast_datetime as demand_hour, 
        f.station_id, 
        s.name as station_name, 
        s.lat as latitude, 
        s.lon as longitude, 
        f.predicted_net_inventory_change as net_inventory_change,
        -- Add a column to identify the "Risk" archetype for easy color-coding in Tableau
        CASE 
            WHEN f.predicted_net_inventory_change <= -10 THEN 'Critical Drain'
            WHEN f.predicted_net_inventory_change >= 10 THEN 'Critical Overflow'
            ELSE 'Stable'
        END as risk_category
    FROM fact_forecasts f
    JOIN dim_stations s ON f.station_id = s.station_id;
    """
    
    print("Extracting BI production feed for Tableau...")
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        print(f"Extraction failed. Ensure fact_forecasts table is populated. Error: {e}")
        return

    # Ensure the output directory exists
    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = output_dir / "tableau_dashboard_feed.csv"
    
    # Export without index to keep the CSV clean for Tableau ingestion
    df.to_csv(output_path, index=False)
    
    print(f"Success! {len(df):,} rows exported to {output_path}.")
    print("You are ready to connect this CSV to Tableau Public.")

if __name__ == "__main__":
    export_dashboard_data()
