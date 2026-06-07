-- =========================================================
-- ADVANCED ANALYTICAL VIEW: HOURLY INVENTORY DELTA
-- =========================================================

CREATE OR REPLACE VIEW view_hourly_inventory_delta AS
WITH outbound AS (
    -- Count how many bikes left the station each hour
    SELECT 
        start_station_id as station_id, 
        DATE_TRUNC('hour', start_time) as demand_hour, 
        COUNT(trip_id) as bikes_out
    FROM fact_trips 
    GROUP BY 1, 2
),
inbound AS (
    -- Count how many bikes arrived at the station each hour
    SELECT 
        end_station_id as station_id, 
        DATE_TRUNC('hour', end_time) as demand_hour, 
        COUNT(trip_id) as bikes_in
    FROM fact_trips 
    GROUP BY 1, 2
)
SELECT 
    COALESCE(o.station_id, i.station_id) as station_id,
    COALESCE(o.demand_hour, i.demand_hour) as demand_hour,
    COALESCE(i.bikes_in, 0) as inbound_volume,
    COALESCE(o.bikes_out, 0) as outbound_volume,
    -- NET CHANGE: Positive means filling up, Negative means draining
    COALESCE(i.bikes_in, 0) - COALESCE(o.bikes_out, 0) as net_inventory_change
FROM outbound o
FULL OUTER JOIN inbound i 
    ON o.station_id = i.station_id AND o.demand_hour = i.demand_hour;

-- ==============================================================================
-- TABLEAU DASHBOARD FEEDS (Execute these to generate your CSVs)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- FEED 1: THE EXECUTIVE SCORECARD (Contextual & Macro P&L)
-- ------------------------------------------------------------------------------
SELECT 
    (SELECT COUNT(DISTINCT station_id) FROM dim_stations) AS total_network_stations,
    (SELECT COUNT(*) FROM fact_trips) AS total_monthly_ridership,
    -- Financial Impact (Using SUM to capture total bleeding)
    SUM(ABS(CASE WHEN net_inventory_change < 0 THEN net_inventory_change ELSE 0 END)) * 4.50 AS total_gross_revenue_loss,
    -- Operational Impact
    COUNT(CASE WHEN net_inventory_change <= -26 THEN 1 END) AS total_critical_dispatch_events
FROM view_hourly_inventory_delta;


-- ------------------------------------------------------------------------------
-- FEED 2: TEMPORAL RISK PROFILE (The Time Impact)
-- ------------------------------------------------------------------------------
SELECT 
    EXTRACT(HOUR FROM demand_hour) AS hour_of_day,
    -- Actionable: The TOTAL financial loss at this hour
    SUM(ABS(CASE WHEN net_inventory_change < 0 THEN net_inventory_change ELSE 0 END)) * 4.50 AS total_hourly_revenue_loss,
    -- Profiling: The AVERAGE loss per station at this hour
    ROUND(AVG(ABS(CASE WHEN net_inventory_change < 0 THEN net_inventory_change ELSE 0 END)) * 4.50, 2) AS avg_revenue_loss_per_station
FROM view_hourly_inventory_delta
GROUP BY 1
ORDER BY total_hourly_revenue_loss DESC;


-- ------------------------------------------------------------------------------
-- FEED 3: GEOSPATIAL STATION ARCHETYPES (The Location Impact)
-- ------------------------------------------------------------------------------
SELECT 
    s.station_id,
    s.name AS station_name,
    s.lat AS latitude,
    s.lon AS longitude,
    s.capacity,
    -- Calculate exact historical deficits
    SUM(CASE WHEN v.net_inventory_change < 0 THEN v.net_inventory_change ELSE 0 END) AS total_bikes_lost,
    SUM(CASE WHEN v.net_inventory_change > 0 THEN v.net_inventory_change ELSE 0 END) AS total_bikes_gained,
    -- Group into Business Archetypes for Tableau Color Coding
    CASE 
        WHEN SUM(v.net_inventory_change) <= -50 THEN 'High-Risk Source (Drains)'
        WHEN SUM(v.net_inventory_change) >= 50 THEN 'High-Risk Sink (Overflows)'
        ELSE 'Self-Balancing (Stable)'
    END AS operational_archetype
FROM view_hourly_inventory_delta v
JOIN dim_stations s ON v.station_id = s.station_id
GROUP BY 1, 2, 3, 4, 5;


-- ------------------------------------------------------------------------------
-- FEED 4: WEATHER & CLIMATE IMPACT (The Disruption Impact)
-- ------------------------------------------------------------------------------
SELECT 
    -- Dynamically generate weather categories based on your millimeter data
    CASE 
        WHEN w.precipitation_mm = 0 THEN 'Clear / Dry'
        WHEN w.precipitation_mm > 0 AND w.precipitation_mm <= 2.5 THEN 'Light Rain'
        WHEN w.precipitation_mm > 2.5 THEN 'Heavy Rain'
        ELSE 'Unknown'
    END AS weather_condition,
    ROUND(AVG(w.temperature_celsius), 1) AS avg_temperature_c,
    COUNT(DISTINCT v.station_id) AS impacted_stations_count,
    -- Financial severity during this specific weather condition
    SUM(ABS(CASE WHEN v.net_inventory_change < 0 THEN v.net_inventory_change ELSE 0 END)) * 4.50 AS total_weather_revenue_loss,
    -- Baseline severity
    ROUND(AVG(ABS(CASE WHEN v.net_inventory_change < 0 THEN v.net_inventory_change ELSE 0 END)) * 4.50, 2) AS avg_loss_per_weather_event
FROM view_hourly_inventory_delta v
JOIN dim_weather w ON v.demand_hour = w.datetime_local
GROUP BY 1
ORDER BY total_weather_revenue_loss DESC;