# 🚲 Proactive Bike Share Logistics Engine

![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14.0+-blue.svg)
![XGBoost](https://img.shields.io/badge/XGBoost-Machine%20Learning-orange.svg)
![Tableau](https://img.shields.io/badge/Tableau-Dashboard-red.svg)

**Live Executive Dashboard:** [https://public.tableau.com/app/profile/minsu.kim8285/viz/ProactiveBikeShareLogisticsEngine/Sheet1]

An end-to-end data architecture and predictive machine learning pipeline built to optimize urban logistics, forecast station inventory, and shift network dispatching from a reactive to a proactive model.

## 📌 Executive Summary
City bike-share networks lose revenue in two primary ways: Stockouts (empty stations) and Overflows (full stations). Currently, urban dispatch logistics operate *reactively*—trucks are only deployed after a station has completely drained, resulting in unfulfilled demand during peak commuting hours.

This project bridges data engineering and machine learning to forecast exact station inventory changes 24 hours in advance. It calculates the "Estimated Lost Revenue," allowing dispatch operators to dynamically compare the financial risk of a stockout against the operational cost of sending a dispatch truck.

### 📊 Key Business Outcomes:
* **Operational ROI:** Mathematically optimized a **$120 truck dispatch cost** by translating predicted station deficits into a financial "Lost Revenue" metric via a Tableau heuristic engine.
* **Predictive Accuracy:** Achieved a highly precise Mean Absolute Error (MAE) of **1.92 bikes** by engineering a rolling 2-hour momentum feature, granting the AI "short-term memory" to react to real-time grid conditions.
* **Data Governance:** Intercepted and quarantined mechanical API glitches (e.g., broken docks recording 1,000-hour trips) across **1.1M+ transaction records** using an automated Python IQR isolation script.

---

## 🏗 System Architecture & Directory

```text
bike_share_logistics_engine/
├── .gitignore                        # Blocks env, raw data, and secret credentials
├── README.md                         # Project documentation
├── requirements.txt                  # Python dependencies
├── data/                             
│   ├── raw/                          # Raw API and historical data (Gitignored)
│   ├── quarantine/                   # Anomalous records failing IQR checks
│   └── processed/                    # ML feature matrices and Tableau feeds
├── sql/                              
│   ├── 01_create_tables.sql          # PostgreSQL schema initialization
│   └── 02_asset_trajectories.sql     # Window functions tracking physical assets
├── src/                              # Production Python backend
│   ├── ingestion_stations.py         
│   ├── ingestion_trips.py            
│   ├── data_quality.py               # IQR Anomaly Detection
│   ├── load_to_postgres.py           
│   ├── build_features.py             
│   ├── train_model.py                # XGBoost Regressor training
│   ├── deploy_forecast.py            
│   └── extract_for_tableau.py 
└── tests/                            
    └── validate_pipeline.py          # Data quality and unit tests
```

---

## 🛠 Core Features & Tech Stack

### 1. Automated Data Governance (`data_quality.py`)
* **Tech:** Python, Pandas, Numpy
* **Function:** Ingests raw trip ledgers and enforces strict logical boundaries. Automatically isolates impossible physical events and routes them to a quarantine directory, protecting warehouse integrity.

### 2. Relational Data Warehouse (`PostgreSQL`)
* **Tech:** PostgreSQL, SQL (DDL, Window Functions)
* **Function:** A Star Schema database. Engineered advanced SQL window functions (`LEAD`, `LAG`) to chronologically track the precise physical trajectory and idle time of individual bicycles across the city.

### 3. Predictive Logistics Modeling (`XGBoost`)
* **Tech:** Python, XGBoost, Scikit-Learn
* **Function:** Engineered temporal schedules and rolling recent-departure momentum features. Trained an XGBoost Regressor predicting `net_inventory_change` to prevent the compounding error of forecasting inbound and outbound flows separately.

### 4. Executive BI Dashboard (`Tableau`)
* **Tech:** Tableau Public
* **Function:** A geospatial executive dashboard featuring a 24-hour interactive time-slider. Instantly quantifies the exact "Estimated Lost Revenue" at any given hour, allowing dispatchers to triage the geographic network.

---

## 📸 Dashboard Previews

> **Predictive Network Map:** Visualizing hourly stockout risks and estimated revenue loss.
> <br>![Tableau Dashboard](assets/dashboard_preview.png) *(Note: Create an 'assets' folder, take a screenshot of your Tableau map, name it dashboard_preview.png, and put it in the folder to make this image render!)*

---

## 🚀 Local Deployment & Setup

*Note: For security and compliance, the massive 3GB raw transaction dataset and the local `.env` database credentials are deliberately excluded from this repository via `.gitignore`.*

**1. Clone the repository**
```bash
git clone [https://github.com/Minsu-Kim-Analyst/bike_sharing_logistics_engine.git](https://github.com/Minsu-Kim-Analyst/bike_sharing_logistics_engine.git)
cd bike_sharing_logistics_engine
```

**2. Establish the isolated virtual environment**
```bash
python3 -m venv env
source env/bin/activate  # On Windows use: env\Scripts\activate
pip install -r requirements.txt
```

**3. Configure secure environment variables**
Create a `.env` file in the root directory to map your local PostgreSQL instance:
```text
DB_USER=postgres
DB_PASS=your_secure_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=bike_share_dw
```

**4. Execute the ETL and ML Pipeline**
```bash
python src/ingestion_trips.py
python src/data_quality.py
python src/train_model.py
```