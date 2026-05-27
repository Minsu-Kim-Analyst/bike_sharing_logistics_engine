import pandas as pd
from pathlib import Path


def run_data_quality_gateway():
    """Executes statistical anomaly detection and partitions data into production/quarantine."""

    # 1. Define input and output paths
    input_path = Path("data/processed/fact_trips_base.csv")
    clean_output_path = Path("data/processed/fact_trips_clean.csv")
    quarantine_output_path = Path("data/quarantine/fact_trips_quarantine.csv")

    # Failsafe check
    if not input_path.exists():
        print(f"[ERROR] Base fact table not found at {input_path}. Please run ingestion first.")
        return

    print(f"[LOADING] Opening {input_path} for structural screening...")
    df = pd.read_csv(input_path, parse_dates=['start_time', 'end_time'])
    total_records = len(df)
    print(f"[INFO] Initial record count: {total_records:,} rows.")

    # 2. Schema Enforcements & Basic Structural Cleaning
    # Drop records that completely lack essential primary keys or routing IDs
    critical_cols = ['trip_id', 'start_station_id', 'end_station_id']
    df_clean_schema = df.dropna(subset=critical_cols).copy()

    # Cast station IDs to integers (Open Data sometimes mixes them as floats/strings)
    df_clean_schema['start_station_id'] = df_clean_schema['start_station_id'].astype(int)
    df_clean_schema['end_station_id'] = df_clean_schema['end_station_id'].astype(int)

    schema_dropped = total_records - len(df_clean_schema)

    # 3. Mathematical Anomaly Detection (IQR Method)
    print("[PROCESSING] Calculating Interquartile Range for trip durations...")
    Q1 = df_clean_schema['trip_duration_seconds'].quantile(0.25)
    Q3 = df_clean_schema['trip_duration_seconds'].quantile(0.75)
    IQR = Q3 - Q1

    # Define statistical boundaries
    upper_bound = Q3 + (1.5 * IQR)
    lower_bound = 60  # Hard floor: Trips under 1 minute are mechanical false-starts

    print(f"[METRICS] Statistical Q1 (25th): {Q1:.1f}s | Q3 (75th): {Q3:.1f}s | IQR: {IQR:.1f}s")
    print(f"[METRICS] Automated Cutoff Threshold: Upper = {upper_bound:.1f}s ({upper_bound / 60:.1f} mins)")

    # 4. Partitioning the Dataset
    # Condition for valid records
    valid_duration_mask = (df_clean_schema['trip_duration_seconds'] >= lower_bound) & \
                          (df_clean_schema['trip_duration_seconds'] <= upper_bound)

    # Separate clean data and anomalies
    df_production = df_clean_schema[valid_duration_mask]
    df_quarantine = df_clean_schema[~valid_duration_mask]

    # Add any schema drops into the quarantine logs for tracking
    if schema_dropped > 0:
        df_schema_anomalies = df[df[critical_cols].isna().any(axis=1)]
        df_quarantine = pd.concat([df_quarantine, df_schema_anomalies], ignore_index=True)

    # 5. Exporting Partitioned Datasets
    print(f"[EXPORTING] Writing production ready data to: {clean_output_path}")
    df_production.to_csv(clean_output_path, index=False)

    print(f"[EXPORTING] Isolating and routing anomalies to: {quarantine_output_path}")
    quarantine_output_path.parent.mkdir(parents=True, exist_ok=True)
    df_quarantine.to_csv(quarantine_output_path, index=False)

    # 6. Executive Data Governance Report
    print("\n" + "=" * 40)
    print("      DATA GOVERNANCE QUALITY REPORT      ")
    print("=" * 40)
    print(f"Total Rows Ingested      : {total_records:,}")
    print(f"Passed Quality Gateway   : {len(df_production):,} ({len(df_production) / total_records:.2%})")
    print(f"Quarantined Anomalies    : {len(df_quarantine):,} ({len(df_quarantine) / total_records:.2%})")
    print("-" * 40)
    print(f"  - Missing ID Drops     : {schema_dropped:,}")
    print(f"  - Hardware/Duration Outliers: {len(df_quarantine) - schema_dropped:,}")
    print("=" * 40)


if __name__ == "__main__":
    run_data_quality_gateway()