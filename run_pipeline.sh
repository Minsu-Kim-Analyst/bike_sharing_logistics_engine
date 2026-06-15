#!/bin/bash
echo "🚲 Starting Bike-Share Logistics Engine..."

echo "--- 1. Running Modular Ingestion ---"
python src/ingestion_stations.py
python src/ingestion_weather.py

echo "--- 2. Executing Master ETL & Governance ---"
python src/etl_master_pipeline.py

echo "--- 3. Retraining AI Model ---"
python src/train_model.py

echo "--- 4. Deploying 2026 Forecast ---"
python src/deploy_forecast.py

echo "--- 5. Extracting BI Feeds for Tableau ---"
python src/generate_business_metrics.py

echo "✅ Pipeline Complete. Data is ready in data/processed/tableau_feeds/"
