-- =========================================================
-- ADVANCED ANALYTICAL VIEW: ASSET TRAJECTORIES & STATE LOCKS
-- =========================================================

CREATE OR REPLACE VIEW view_asset_trajectories AS
WITH chronological_bike_log AS (
    SELECT 
        trip_id,
        bike_id,
        start_station_id,
        start_time,
        end_station_id,
        end_time,
        trip_duration_seconds,
        -- Look backward to find where this specific bike came from
        LAG(end_station_id) OVER(PARTITION BY bike_id ORDER BY start_time) as previous_end_station_id,
        LAG(end_time) OVER(PARTITION BY bike_id ORDER BY start_time) as previous_end_time
    FROM fact_trips
)
SELECT 
    trip_id,
    bike_id,
    start_station_id,
    start_time,
    end_station_id,
    end_time,
    trip_duration_seconds,
    previous_end_station_id,
    previous_end_time,
    -- Calculate how many seconds the bike sat idle at the station before this trip
    EXTRACT(EPOCH FROM (start_time - previous_end_time)) as station_idle_seconds,
    -- System Anomaly Flag: If start station doesn't match previous end station, it was trucked
    CASE 
        WHEN previous_end_station_id IS NULL THEN 0
        WHEN start_station_id <> previous_end_station_id THEN 1
        ELSE 0
    END as was_system_rebalanced
FROM chronological_bike_log;