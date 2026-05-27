import pandas as pd
import pytest
from pathlib import Path


# Load the clean data once for all tests to use
@pytest.fixture(scope="module")
def clean_trips_data():
    file_path = Path("data/processed/fact_trips_clean.csv")
    if not file_path.exists():
        pytest.fail(f"Clean trips file missing at {file_path}. Cannot run tests.")
    return pd.read_csv(file_path)


@pytest.fixture(scope="module")
def raw_stations_data():
    file_path = Path("data/raw/dim_stations_raw.csv")
    if not file_path.exists():
        pytest.fail(f"Stations file missing at {file_path}. Cannot run tests.")
    return pd.read_csv(file_path)


# ==========================================
# ENTERPRISE DATA CONTRACTS
# ==========================================

def test_no_missing_critical_ids(clean_trips_data):
    """CONTRACT 1: A trip cannot exist without a valid start and end station ID."""
    missing_starts = clean_trips_data['start_station_id'].isna().sum()
    missing_ends = clean_trips_data['end_station_id'].isna().sum()

    assert missing_starts == 0, f"Failed: Found {missing_starts} missing start station IDs."
    assert missing_ends == 0, f"Failed: Found {missing_ends} missing end station IDs."


def test_trip_duration_logical_bounds(clean_trips_data):
    """CONTRACT 2: Trips must be at least 60 seconds (mechanical baseline)."""
    invalid_durations = clean_trips_data[clean_trips_data['trip_duration_seconds'] < 60]

    assert len(invalid_durations) == 0, f"Failed: Found {len(invalid_durations)} trips under 60 seconds."


def test_station_capacity_is_positive(raw_stations_data):
    """CONTRACT 3: A physical station cannot have a negative docking capacity."""
    negative_capacity = raw_stations_data[raw_stations_data['capacity'] < 0]

    assert len(negative_capacity) == 0, f"Failed: Found stations with negative capacity."