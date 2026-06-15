import pandas as pd
from sqlalchemy import create_engine
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def get_engine():
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "bike_share_dw")
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

def export_all_tableau_feeds():
    engine = get_engine()
    out_dir = Path("data/processed/tableau_feeds")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    print("Extracting BI feeds from Data Warehouse...")

    # 1. Extract the Business Metrics (Scorecard, Temporal, Weather, Archetypes)
    views = [
        "view_tableau_scorecard", 
        "view_tableau_temporal", 
        "view_tableau_archetypes", 
        "view_tableau_weather"
    ]
    
    for view in views:
        try:
            df = pd.read_sql(f"SELECT * FROM {view}", engine)
            file_path = out_dir / f"{view.replace('view_tableau_', '')}.csv"
            df.to_csv(file_path, index=False)
            print(f" -> Exported {file_path.name}")
        except Exception as e:
            print(f" -> Skipping {view}: Ensure the view is created in PostgreSQL.")

    # 2. Extract the Predictive Forecast Map (Formerly extract_for_tableau.py)
    forecast_query = """
    SELECT 
        f.forecast_datetime as demand_hour, 
        f.station_id, 
        s.name as station_name, 
        s.lat as latitude, 
        s.lon as longitude, 
        f.predicted_net_inventory_change as net_inventory_change,
        CASE 
            WHEN f.predicted_net_inventory_change <= -10 THEN 'Critical Drain'
            WHEN f.predicted_net_inventory_change >= 10 THEN 'Critical Overflow'
            ELSE 'Stable'
        END as risk_category
    FROM fact_forecasts f
    JOIN dim_stations s ON f.station_id = s.station_id;
    """
    
    try:
        df_forecast = pd.read_sql(forecast_query, engine)
        forecast_path = out_dir / "forecast_map.csv"
        df_forecast.to_csv(forecast_path, index=False)
        print(f" -> Exported forecast_map.csv ({len(df_forecast):,} rows)")
    except Exception as e:
        print(f" -> Forecast extraction failed: {e}")

    print("All BI Feeds successfully staged for Tableau.")

if __name__ == "__main__":
    export_all_tableau_feeds()
