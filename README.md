# Proactive Bike Share Logistics Engine

**Live Executive Dashboard:** (https://public.tableau.com/app/profile/minsu.kim8285/viz/ProactiveBikeShareLogisticsEngine/Sheet1)

## 1. The Business Problem
City bike-share networks lose revenue in two primary ways: Stockouts (empty stations) and Overflows (full stations). Currently, urban dispatch logistics operate *reactively*—trucks are only deployed after a station has completely drained, resulting in unfulfilled demand and customer friction during peak commuting hours.

## 2. The Solution
An end-to-end data architecture and machine learning engine that shifts operations from reactive to *proactive*. The system forecasts exact station inventory changes 24 hours in advance, calculates the "Estimated Lost Revenue," and allows dispatch operators to dynamically compare the financial risk of a stockout against the operational cost of sending a dispatch truck.

## 3. Data Architecture & Quality Governance
* **Tech Stack:** Python, PostgreSQL, Pandas, XGBoost, Tableau.
* **Data Volume:** Ingested 1.1+ million real transaction logs (Toronto Open Data), integrated with live GBFS v3.0 station capacities and historical Environment Canada climate data.
* **Automated Data Quality:** Engineered a Python-based Interquartile Range (IQR) isolation script to automatically detect and quarantine mechanical API glitches (e.g., broken docks recording 1,000-hour trips) before database insertion, protecting warehouse integrity.
* **Database Design:** Developed a PostgreSQL Star Schema. Wrote advanced SQL window functions (`LEAD`, `LAG`) to track the precise physical and chronological trajectory of individual assets.

## 4. Machine Learning & Explainable AI
The predictive engine utilizes an XGBoost Regressor predicting `net_inventory_change` to prevent the compounding error of forecasting inbound and outbound flows separately. The model achieved a baseline Mean Absolute Error (MAE) of **1.92 bikes**.

**Key AI Decision Drivers (Feature Importance):**
To ensure business stakeholders trust the AI, the model's logic was extracted and quantified:
1. **Time of Day (27.57%):** Foundational temporal schedule.
2. **Day of Week (19.80%):** Differentiates commuter vs. recreational patterns.
3. **Station Profile (16.01%):** Geographic node characteristics.
4. **Rolling 2-Hour Momentum (10.77%):** *The crucial lag feature.* This grants the AI short-term memory, allowing it to override static historical schedules and react to real-time physical conditions (e.g., sudden weather events or transit delays).

## 5. The Financial ROI Engine (Tableau)
The predictive output is fed into a Tableau executive dashboard containing a 24-hour interactive time-slider. 
* **Business Logic:** The dashboard isolates predicted negative net flows and multiplies them by a $4.50 proxy ticket price. 
* **Operational Value:** This instantly quantifies the exact "Estimated Lost Revenue" at any given hour, allowing dispatchers to mathematically justify a $120 truck deployment.

## 6. Future Scope (Production Scaling)
While this MVP prototype runs locally via batch processing, a true enterprise deployment would require:
1. **Cloud Orchestration:** Containerizing the Python extraction/training scripts via Docker and scheduling automated runs using Apache Airflow.
2. **Live Feature Store:** Migrating from daily PostgreSQL batch inserts to real-time event streaming using Apache Kafka to update station states by the second.
3. **Chronological Validation:** Upgrading the 80/20 random train/test split to a strict Out-of-Time chronological backtest to completely eliminate time-series data leakage.
