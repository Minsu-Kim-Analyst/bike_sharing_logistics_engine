import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path
import os
from dotenv import load_dotenv

# Load the secret vault
load_dotenv()

def export_dashboard_data():
    """Extracts the final August 1st analytical forecast for Tableau Public."""

    # Pull the passwords securely from the .env file
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = os.getenv("DB_PORT")
    DB_NAME = os.getenv("DB_NAME")

    print("[CONN] Connecting to PostgreSQL Data Warehouse...")
    engine = create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

    query = """
    SELECT 
        f.forecast_datetime as demand_hour,
        f.station_id,
        s.name,
        s.lat,
        s.lon,
        f.predicted_net_inventory_change as net_inventory_change
    FROM fact_forecasts f
    JOIN dim_stations s ON f.station_id = s.station_id
    WHERE DATE(f.forecast_datetime) = '2025-08-01';
    """

    print("[EXTRACTION] Pulling 24-hour predictive matrix for August 1, 2025...")
    try:
        df = pd.read_sql(query, engine)
    except Exception as e:
        print(f"[ERROR] Extraction failed. Ensure fact_forecasts exists. Details: {e}")
        return

    if df.empty:
        print("[WARNING] No rows returned. Check if deploy_inventory_forecast.py was run.")
        return

    output_dir = Path("data/processed")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "tableau_dashboard_feed.csv"

    df.to_csv(output_path, index=False)

    print(f"[SUCCESS] Exported {len(df):,} rows to {output_path}.")
    print("Pipeline complete. File is ready to be loaded into Tableau Public as a Text File.")


if __name__ == "__main__":
    export_dashboard_data()