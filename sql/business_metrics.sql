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