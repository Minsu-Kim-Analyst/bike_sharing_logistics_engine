-- ==========================================
-- PHASE 3: STAR SCHEMA DEFINITION
-- ==========================================

-- 1. Create the Stations Dimension (Slowly Changing)
CREATE TABLE IF NOT EXISTS dim_stations (
    station_id INT PRIMARY KEY,
    name VARCHAR(255),
    lat DECIMAL(9,6),
    lon DECIMAL(9,6),
    capacity INT
);

-- 2. Create the Weather Dimension (Hourly Fact-Context)
CREATE TABLE IF NOT EXISTS dim_weather (
    datetime_local TIMESTAMP PRIMARY KEY,
    temperature_celsius DECIMAL(5,2),
    precipitation_mm DECIMAL(5,2),
    wind_speed_kmh INT,
    station_pressure_kpa DECIMAL(6,2)
);

-- 3. Create the Trips Fact Table (High Velocity)
CREATE TABLE IF NOT EXISTS fact_trips (
    trip_id BIGINT PRIMARY KEY,
    trip_duration_seconds INT,
    start_station_id INT REFERENCES dim_stations(station_id),
    start_time TIMESTAMP,
    end_station_id INT REFERENCES dim_stations(station_id),
    end_time TIMESTAMP,
    bike_id INT,
    user_type VARCHAR(50),
    bike_model VARCHAR(50)
);

-- 4. Create Indexes for High-Speed Querying
CREATE INDEX idx_fact_start_time ON fact_trips(start_time);
CREATE INDEX idx_fact_start_station ON fact_trips(start_station_id);