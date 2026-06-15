import pandas as pd
import pytest
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Load credentials
load_dotenv()

@pytest.fixture(scope="module")
def db_engine():
    DB_USER = os.getenv("DB_USER")
    DB_PASS = os.getenv("DB_PASS")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")
    DB_NAME = os.getenv("DB_NAME", "bike_share_dw")
    return create_engine(f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# ==========================================
# ENTERPRISE DATA CONTRACTS (DB-LEVEL)
# ==========================================

def test_no_missing_critical_ids(db_engine):
    """CONTRACT 1: A trip cannot exist without a valid start and end station ID."""
    # We push the compute to PostgreSQL to count invalid records
    query = """
    SELECT COUNT(*) as invalid_count 
    FROM fact_trips 
    WHERE start_station_id IS NULL OR end_station_id IS NULL;
    """
    invalid_count = pd.read_sql(query, db_engine)['invalid_count'].iloc[0]
    assert invalid_count == 0, f"Failed: Found {invalid_count} trips with missing station IDs."

def test_trip_duration_logical_bounds(db_engine):
    """CONTRACT 2: Trips must be at least 60 seconds (mechanical baseline)."""
    query = """
    SELECT COUNT(*) as invalid_count 
    FROM fact_trips 
    WHERE trip_duration_seconds < 60;
    """
    invalid_count = pd.read_sql(query, db_engine)['invalid_count'].iloc[0]
    assert invalid_count == 0, f"Failed: Found {invalid_count} trips under 60 seconds."

def test_station_capacity_is_positive(db_engine):
    """CONTRACT 3: A physical station cannot have a negative docking capacity."""
    query = """
    SELECT COUNT(*) as invalid_count 
    FROM dim_stations 
    WHERE capacity < 0;
    """
    invalid_count = pd.read_sql(query, db_engine)['invalid_count'].iloc[0]
    assert invalid_count == 0, f"Failed: Found stations with negative capacity."
