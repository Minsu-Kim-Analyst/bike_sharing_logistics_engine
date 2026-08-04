# Operational Analytics & Demand Forecasting Report: Toronto Bike-Share System

---

## 1. Executive Summary & Problem Statement

### Project Overview
Bike Share Toronto serves as a critical component of the municipality's sustainable urban transit strategy. However, the network experiences severe, recurring station inventory imbalances where high-demand nodes either run completely out of bicycles (**stockouts**) or fill up entirely with no open docks (**overflows**).

### The Business Challenge
Current redistribution efforts rely on reactive truck dispatching, where field operations relocate bicycles only after riders have already experienced service interruptions. This operational inefficiency leads to direct ridership revenue losses, inflated labor and fuel costs, and diminished public trust in bike-sharing as a dependable commuting option.

### Project Objectives
* **Demand Forecasting:** Construct a time-series machine learning model to predict station-level inventory changes across hourly, daily, and seasonal cycles.
* **Behavioral Segmentation:** Classify network nodes into operational archetypes based on historical net-inventory flow.
* **Decision Support:** Deploy an interactive BI dashboard and operational pipeline to transition logistics management from reactive troubleshooting to proactive dispatch scheduling.

---

## 2. Data Sources & Architecture Strategy

The platform integrates three primary data streams into a unified data warehouse:

| Data Stream | Source | Technical Parameters | Analytical Purpose |
| :--- | :--- | :--- | :--- |
| **Historical Trips** | Bike Share Toronto Open Data | 7.26M transaction ledgers (2025) | Identifies baseline ridership trends, trip durations, and start/end node frequencies. |
| **Climate Records** | Environment Canada API | Hourly precipitation (mm) and temperature (°C) | Evaluates climate sensitivity on net-inventory variance. |
| **Network Metadata** | GBFS Real-Time Feed Snapshots | 1,000+ station capacities, latitudes, longitudes | Defines physical spatial boundaries and station capacity limits. |

### Data Integration Methodology
1. **Temporal Alignment:** Transaction timestamps in raw trip ledgers are truncated to the hour to perform a one-to-many join with hourly climate logs.
2. **Geospatial Mapping:** Transactional start and end station IDs are joined against static station dimension tables to capture physical docking constraints and geospatial coordinates.

---

## 3. Data Governance & Quality Assurance Layer

To protect downstream models and dashboards from dirty data, an explicit ETL data governance gateway was implemented.

```
+------------------+      +-------------------------+      +----------------------+
|  Raw API & Trip  | ---> |   IQR Anomaly Gateway   | ---> |  PostgreSQL DW /     |
|  Data Ingestion  |      | (Quarantines Corrupted) |      | Clean Fact Tables    |
+------------------+      +-------------------------+      +----------------------+
                                       |
                                       v
                          +--------------------------+
                          |   quarantine/ Directory   |
                          | (544,342 Anomalous Rows) |
                          +--------------------------+
```

### Governance Mechanics
* **Boundary Rules:** Filtered out mechanical baseline anomalies, including ghost trips lasting under 60 seconds and negative trip durations.
* **IQR Anomaly Filtering:** Evaluated trip durations using an Interquartile Range (IQR) threshold, automatically routing **544,342 corrupted sensor records** into an isolated quarantine directory.
* **Database Quality Contracts:** Built automated assertion tests using `pytest` to verify that no null station IDs or negative capacity values enter production tables.

---

## 4. PostgreSQL Relational Data Warehouse

The database architecture utilizes a **Star Schema** to decouple transactional ingestion from predictive analytics and BI reporting.

```
                         +-------------------+
                         |   dim_stations    |
                         +-------------------+
                         | PK  station_id    |
                         |     name          |
                         |     capacity      |
                         |     lat / lon     |
                         +-------------------+
                                   |            \
                                   | 1:N         \ 1:N
                                   v              v
+------------------+     +-------------------+     +------------------+
|   dim_weather    |     |    fact_trips     |     |  fact_forecasts  |
+------------------+     +-------------------+     +------------------+
| PK  datetime     | --->| FK  start_time    |     | PK  forecast_id  |
|     temp_c       | 1:N | FK  start_station |     | FK  station_id   |
|     precip_mm    |     | FK  end_station   |     |     target_hour  |
+------------------+     |     duration_sec  |     |     predicted_net|
                         +-------------------+     +------------------+
```

### Advanced Analytical SQL Views

#### 1. Asset Trajectories & System Anomaly Detection
Tracks individual bike movements to detect undocumented rebalancing by maintenance trucks using SQL Window Functions:

```sql
CREATE OR REPLACE VIEW view_asset_trajectories AS
WITH chronological_bike_log AS (
    SELECT 
        trip_id, bike_id, start_station_id, start_time, end_station_id, end_time,
        LAG(end_station_id) OVER(PARTITION BY bike_id ORDER BY start_time) as previous_end_station_id,
        LAG(end_time) OVER(PARTITION BY bike_id ORDER BY start_time) as previous_end_time
    FROM fact_trips
)
SELECT 
    trip_id, bike_id, start_station_id, start_time, end_station_id, end_time,
    CASE 
        WHEN previous_end_station_id IS NULL THEN 0
        WHEN start_station_id <> previous_end_station_id THEN 1
        ELSE 0
    END as was_system_rebalanced
FROM chronological_bike_log;
```
* **Business Value:** Automatically flags records where a bike's starting station differs from its previous arrival station, proving physical truck intervention while offline.

#### 2. Hourly Inventory Delta View
Calculates net hourly bike volume changes across all network nodes:

```sql
CREATE OR REPLACE VIEW view_hourly_inventory_delta AS
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
    COALESCE(i.bikes_in, 0) - COALESCE(o.bikes_out, 0) as net_inventory_change
FROM outbound o
FULL OUTER JOIN inbound i ON o.station_id = i.station_id AND o.demand_hour = i.demand_hour;
```

---

## 5. Predictive Analytics & Machine Learning Pipeline

### Model Architecture
* **Algorithm:** Time-Series XGBoost Regressor.
* **Training Dataset:** 2025 historical trip and climate data.
* **Feature Set:** Temporal indicators (hour of day, day of week, month), climate signals (precipitation, temperature), and 2-hour rolling lag demand indicators.

### Validation & Accuracy
* **Validation Strategy:** Time-Series Cross-Validation (TSCV) to prevent temporal data leakage.
* **Model Metric:** Achieved a **Mean Absolute Error (MAE) of ~1.7 bikes** per station-hour.

### Out-of-Sample Simulation (2026 Peak Stress Test)
The trained regressor was executed against an out-of-sample 3-day summer peak scenario in 2026, generating **75,000+ predictions** to identify network bottlenecks prior to operational execution.

---

## 6. Diagnostic Findings & Business Insights

1. **Commuter Behavior Dominates Volatility:** Time-of-day and day-of-week commuting patterns account for over 50% of total network demand variance. Financial losses spike sharply during weekday rush hours (4:00 PM – 6:00 PM).
2. **Behavior Overrides Weather:** While heavy rain reduces total overall ridership volume, it has a minimal impact on net station inventory movement. Commuters continue to drain residential stations regardless of light precipitation.
3. **Structural Station Archetypes Exist:** Stations naturally cluster into permanent behavioral profiles:
   * **High-Risk Sources (Drains):** Residential neighborhoods that completely empty during morning rush hours.
   * **High-Risk Sinks (Overflows):** Commercial downtown hubs that fill to capacity during morning arrivals.
   * **Self-Balancing (Stable):** Mixed-use stations with equal inbound and outbound trip rates.

---

## 7. Business Intelligence & Decision Support System

The analytical outputs are extracted via Python (`generate_business_metrics.py`) into five pre-aggregated CSV feeds powering a **3-Tier Tableau Public Dashboard**:

```
+----------------------------------------------------------------------------------+
|                            TIER 1: EXECUTIVE SCORECARD                           |
|  Total Monthly Ridership  | Active Stations | Truck Moves | Revenue Loss ($)     |
+----------------------------------------------------------------------------------+
|                            TIER 2: DIAGNOSTIC ANALYSIS                           |
|  [ Temporal Loss Line Chart ]      [ Weather Sensitivity ]   [ Archetype Scatter ] |
+----------------------------------------------------------------------------------+
|                            TIER 3: OPERATIONAL FORECAST                          |
|  [ 2026 Geospatial Risk Map with 72-Hour Animated Time-Slider ]                  |
+----------------------------------------------------------------------------------+
```

---

## 8. Strategic Recommendations & Managerial Implications

### Practical Recommendations for Operations
1. **Pre-Shift Rebalancing Routes:** Schedule truck crews to deploy to "High-Risk Source" stations 60 to 90 minutes prior to the morning commuter surge.
2. **Targeted Fleet Capacity Adjustments:** Permanently increase physical docking infrastructure at high-density "Sink" nodes in downtown business districts.

### Managerial & Financial Impact
* **Proactive Resource Allocation:** Transitions operational strategy from reactive firefighting to scheduled, predictive fleet deployment.
* **Cost Optimization:** Reduces unnecessary truck mileage and overtime labor expenses by focusing rebalancing exclusively on high-probability shortage nodes.
* **Revenue Protection:** Minimizes failed customer trips, preserving per-ride and membership subscription revenues.

---

## 9. Project Constraints & Limitations

* **Batch Ingestion Framework:** The platform relies on historical batch processing and predictive scenario generation rather than a live, cloud-hosted real-time API loop.
* **External Event Variables:** Municipal event calendars (e.g., stadium closures, major concerts) were excluded to manage pipeline scope, which may introduce short-term variance during unannounced city events.