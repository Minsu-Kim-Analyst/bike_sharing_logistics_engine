-- =========================================================
-- 0. TEARDOWN EXISTING VIEWS (Prevents schema conflicts)
-- =========================================================
DROP VIEW IF EXISTS view_tableau_weather CASCADE;
DROP VIEW IF EXISTS view_tableau_archetypes CASCADE;
DROP VIEW IF EXISTS view_tableau_temporal CASCADE;
DROP VIEW IF EXISTS view_tableau_scorecard CASCADE;
DROP VIEW IF EXISTS view_asset_trajectories CASCADE;
DROP VIEW IF EXISTS view_hourly_inventory_delta CASCADE;

-- =========================================================
-- 1. BASE VIEW: HOURLY INVENTORY DELTA
-- =========================================================
CREATE VIEW view_hourly_inventory_delta AS
WITH outbound AS (
    SELECT start_station_id as station_id, DATE_TRUNC('hour', start_time) as demand_hour, COUNT(trip_id) as bikes_out
    FROM fact_trips GROUP BY 1, 2
),
inbound AS (
    SELECT end_station_id as station_id, DATE_TRUNC('hour', end_time) as demand_hour, COUNT(trip_id) as bikes_in
    FROM fact_trips GROUP BY 1, 2
)
SELECT 
    COALESCE(o.station_id, i.station_id) as station_id,
    COALESCE(o.demand_hour, i.demand_hour) as demand_hour,
    COALESCE(i.bikes_in, 0) as inbound_volume,
    COALESCE(o.bikes_out, 0) as outbound_volume,
    COALESCE(i.bikes_in, 0) - COALESCE(o.bikes_out, 0) as net_inventory_change
FROM outbound o
FULL OUTER JOIN inbound i ON o.station_id = i.station_id AND o.demand_hour = i.demand_hour;

-- =========================================================
-- 2. ASSET TRAJECTORY VIEW (Window Functions)
-- =========================================================
CREATE VIEW view_asset_trajectories AS
WITH chronological_bike_log AS (
    SELECT 
        bike_id, start_station_id, start_time,
        LAG(end_station_id) OVER(PARTITION BY bike_id ORDER BY start_time) as previous_end_station_id
    FROM fact_trips
)
SELECT 
    bike_id,
    CASE 
        WHEN previous_end_station_id IS NULL THEN 0
        WHEN start_station_id <> previous_end_station_id THEN 1
        ELSE 0
    END as was_system_rebalanced
FROM chronological_bike_log;

-- =========================================================
-- 3. TABLEAU EXPORT VIEWS
-- =========================================================

-- Executive Scorecard View 
CREATE VIEW view_tableau_scorecard AS
SELECT 
    (SELECT COUNT(DISTINCT station_id) FROM dim_stations) AS total_network_stations,
    (SELECT COUNT(*) FROM fact_trips) AS total_monthly_ridership,
    (SELECT SUM(was_system_rebalanced) FROM view_asset_trajectories) AS manual_truck_moves_detected,
    SUM(ABS(CASE WHEN net_inventory_change < 0 THEN net_inventory_change ELSE 0 END)) * 4.50 AS total_gross_revenue_loss
FROM view_hourly_inventory_delta;

-- Temporal Risk View
CREATE VIEW view_tableau_temporal AS
SELECT 
    EXTRACT(HOUR FROM demand_hour) AS hour_of_day,
    SUM(ABS(CASE WHEN net_inventory_change < 0 THEN net_inventory_change ELSE 0 END)) * 4.50 AS total_hourly_revenue_loss
FROM view_hourly_inventory_delta
GROUP BY 1 ORDER BY total_hourly_revenue_loss DESC;

-- Geospatial Archetypes View
CREATE VIEW view_tableau_archetypes AS
SELECT 
    s.station_id, s.name AS station_name, s.lat AS latitude, s.lon AS longitude,
    SUM(CASE WHEN v.net_inventory_change < 0 THEN v.net_inventory_change ELSE 0 END) AS total_bikes_lost,
    SUM(CASE WHEN v.net_inventory_change > 0 THEN v.net_inventory_change ELSE 0 END) AS total_bikes_gained,
    CASE 
        WHEN SUM(v.net_inventory_change) <= -50 THEN 'High-Risk Source (Drains)'
        WHEN SUM(v.net_inventory_change) >= 50 THEN 'High-Risk Sink (Overflows)'
        ELSE 'Self-Balancing (Stable)'
    END AS operational_archetype
FROM view_hourly_inventory_delta v
JOIN dim_stations s ON v.station_id = s.station_id
GROUP BY 1, 2, 3, 4;

-- Weather Impact View
CREATE VIEW view_tableau_weather AS
SELECT 
    CASE 
        WHEN w.precipitation_mm = 0 THEN 'Clear / Dry'
        WHEN w.precipitation_mm > 0 AND w.precipitation_mm <= 2.5 THEN 'Light Rain'
        ELSE 'Heavy Rain'
    END AS weather_condition,
    SUM(ABS(CASE WHEN v.net_inventory_change < 0 THEN v.net_inventory_change ELSE 0 END)) * 4.50 AS total_weather_revenue_loss
FROM view_hourly_inventory_delta v
JOIN dim_weather w ON v.demand_hour = w.datetime_local
GROUP BY 1 ORDER BY total_weather_revenue_loss DESC;