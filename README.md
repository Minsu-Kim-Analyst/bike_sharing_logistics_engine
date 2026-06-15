# 🚲 Operational Analytics & Demand Forecasting System: Toronto Bike-Share

**[View the Interactive Tableau Dashboard Here] ->** *(https://public.tableau.com/app/profile/minsu.kim8285/viz/ProactiveBikeShareLogisticsEngine/Sheet1)*

## 🌆 Executive Summary
This project is an end-to-end operational analytics and decision-support system designed to solve a costly logistics problem: urban bike-share inventory imbalance. 

By engineering a modular pipeline that processes **one full year of 2025 historical trip records** (7.2 million rows) and integrates Environment Canada climate signals, this platform identifies the root causes of station stockouts and overflows. It deploys a Time-Series XGBoost forecasting model to predict network stress during a **3-day peak summer stress test in 2026**, allowing operations teams to transition from reactive truck dispatching to proactive, AI-driven rebalancing.

## 🎯 The Business Problem
Urban mobility networks bleed revenue through predictable, localized inefficiencies:
* 🚫 **Stockouts (Critical Drain):** Empty stations mean lost ridership revenue and frustrated commuters.
* 🚧 **Overflows (Critical Surplus):** Full stations prevent riders from ending trips, destroying the user experience.
* 🚚 **Reactive Logistics:** Dispatching maintenance trucks *after* a station is empty creates operational bottlenecks and wastes labor hours.

**Objective:** Build a data engine that answers: *"Where will demand exceed supply in the next 24-72 hours, and what is the financial cost if we fail to act?"*

## 🧠 Key Business Insights & Findings
Through rigorous diagnostic analytics and machine learning feature extraction on the 2025 dataset, the model revealed critical operational realities:
1. **Behavior Overrides Weather:** Time-of-day and day-of-week commuting patterns account for over 50% of network demand volatility. While heavy rain impacts overall trip volume, it has a negligible impact on *net-inventory movement*. Proactive rebalancing around rush hour yields higher ROI than weather-based planning.
2. **Permanent Network Archetypes:** The network contains permanent "Source nodes" (residential areas that drain daily) and "Sink nodes" (commercial hubs that flood daily). This proves the imbalance is a structural capacity issue, not just random daily variance.
3. **The Cost of Inaction:** Quantifiable lost revenue spikes drastically between 4:00 PM and 6:00 PM on weekdays, providing a narrow, highly profitable window for targeted truck dispatching.

## 🏗️ System Architecture & Engineering Workflow

### 1. Master ETL & Data Integration (The Merge Strategy)
A core engineering challenge was aligning high-velocity transactional data with static infrastructure and hourly climate APIs. The `etl_master_pipeline.py` script executes a comprehensive Dimensional Modeling merge:
* **Temporal Weather Alignment:** Raw 2025 bike trips are recorded down to the exact second. The pipeline truncates these transaction timestamps to the nearest hour (e.g., 14:32:05 -> 14:00:00) to perform a clean, one-to-many SQL join with Environment Canada's hourly meteorological measurements (temperature, precipitation).
* **Geospatial Station Alignment:** 7.2M trip ledgers are joined against static station IDs to map physical docking capacity, latitude, and longitude, enabling the calculation of network distances and localized stress points.
* **Data Governance:** Prior to loading, the pipeline passes all records through an IQR anomaly detection gateway, automatically **quarantining 544,342 corrupted sensor records** (e.g., negative durations, ghost trips) to ensure the AI model trained exclusively on high-fidelity data.

### 2. Database Architecture (PostgreSQL)
To handle the dataset efficiently, the data warehouse utilizes a **Star Schema** approach, decoupling raw storage from machine learning outputs and BI computation.
* **Storage Layer:** `fact_trips` (2025 historical data), `fact_forecasts` (2026 predictive outputs), `dim_stations`, and `dim_weather`.
* **Compute Layer:** Complex logic is pushed to the database via explicit reporting views. 
    * `view_hourly_inventory_delta`: Base view calculating exact inbound/outbound volume per station, per hour.
    * `view_asset_trajectories`: Utilizes advanced SQL Window Functions (`LAG`) to track individual physical assets and detect undocumented manual truck rebalancing.
    * `view_tableau_*`: Dedicated reporting views (Scorecard, Temporal, Weather, Archetypes) that pre-aggregate ROI and risk metrics for lightning-fast Tableau consumption.

### 3. Forecasting Engine (XGBoost)
* Trained a time-series regressor using 2-hour rolling demand momentum and temporal flags extracted from the 2025 dataset.
* Utilized Time-Series Cross-Validation (TSCV) to prevent data leakage, achieving a **Mean Absolute Error (MAE) of ~1.7 bikes** per station-hour.
* **The 2026 Simulation:** Deployed the model on an "out-of-sample" 3-day summer peak scenario in 2026, generating 75,000+ predictions mapping exactly when and where the network would break without intervention.

### 4. BI Deployment (Tableau)
Designed a comprehensive Business Intelligence dashboard:
* 📊 **Tier 1 (Executive Scorecard):** Tracks macro KPIs and estimated projected revenue loss for Finance and Directors.
* 📈 **Tier 2 (Diagnostic Analysis):** Profiles historical 2025 demand patterns by time of day, weather impact, and geospatial station archetypes.
* 🗺️ **Tier 3 (Operational Forecast):** A geospatial map animating the 2026 stress-test, predicting specific stockout and overflow risks to guide future truck dispatching.

## 📁 Repository Structure

    bike_share_logistics_engine/
    ├── .env                           # Local database credentials (Ignored by Git)
    ├── .gitignore                     # Enterprise security and system file exclusions
    ├── README.md                      # Project documentation and setup guide
    ├── requirements.txt               # Strict version-pinned Python dependencies
    ├── run_pipeline.sh                # Master bash orchestrator for end-to-end execution
    ├── assets/                        # Rendered UI components for repository documentation
    │   └── dashboard_preview.png      # Tableau geospatial network dashboard preview
    ├── data/                          # Local data storage (Ignored by Git)
    │   ├── processed/                 # Aggregated Tableau BI feeds
    │   ├── quarantine/                # Anomalous records failing IQR checks
    │   └── raw/                       # Raw API and historical transaction ledgers
    ├── models/                        # Serialized Machine Learning Ecosystem
    │   └── xgboost_inventory_model.pkl # Production-ready trained regressor
    ├── notebooks/                     # Exploratory Data Analysis & Prototyping
    │   ├── generate_eda_visual.py     # Script generating statistical data profiling plots
    │   └── trip_outliers_plot.png     # Visual output of IQR distribution and anomalies
    ├── sql/                           # Relational Database Architecture & Views
    │   ├── create_tables.sql          # PostgreSQL schema initialization
    │   └── business_metrics.sql       # Aggregation queries for BI feeds
    ├── src/                           # Core Python Architecture
    │   ├── ingestion_stations.py      # Independent API ingest for static nodes
    │   ├── ingestion_weather.py       # Independent climate data integration
    │   ├── etl_master_pipeline.py     # High-volume trip ingestion & IQR governance
    │   ├── train_model.py             # XGBoost training pipeline & feature engineering
    │   ├── deploy_forecast.py         # 2026 scenario inference script
    │   └── generate_business_metrics.py # Automated SQL-to-CSV Tableau extraction
    └── tests/                         # Validation & Quality Assurance
        └── test_data_quality.py       # Pytest suite executing Data Quality contracts

## 🚀 Execution Guide
To replicate the environment and generate the BI feeds locally:

1. Clone the repository and install dependencies:
    
    git clone https://github.com/Minsu-Kim-Analyst/bike_sharing_logistics_engine.git
    cd bike_sharing_logistics_engine
    pip install -r requirements.txt

2. Configure a `.env` file with your local PostgreSQL credentials.

3. Execute the pipeline manually or via the master orchestrator:
    
    chmod +x run_pipeline.sh
    ./run_pipeline.sh

## 🛠️ Tech Stack
* **Core:** Python (Pandas, NumPy, Scikit-Learn, XGBoost, Pytest)
* **Database:** PostgreSQL (Star Schema, CTEs, Window Functions)
* **Visualization:** Tableau Public
* **Data Sources:** Toronto Bike Share API, Environment Canada Climate Archive

## 👤 Author
**Minsu Kim**
*B.Math (Mathematical Studies) | Post-Graduate Certificate in Business Analytics*
Focus: Data Engineering, Forecasting Systems, and Operational Analytics