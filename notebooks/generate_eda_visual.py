import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path


def generate_outlier_visual():
    print("[EDA] Loading raw trips to visualize hardware anomalies...")

    # We load the base file (before the IQR filter cleaned it)
    file_path = Path("data/processed/fact_trips_base.csv")
    if not file_path.exists():
        print("Base trips file not found.")
        return

    df = pd.read_csv(file_path)

    # Convert trip duration from seconds to hours for easier reading
    df['duration_hours'] = df['trip_duration_seconds'] / 3600

    # Create a professional-grade Seaborn visualization
    plt.figure(figsize=(10, 4))
    sns.boxplot(x=df['duration_hours'], color='#E63946')

    plt.title('Distribution of Raw Trip Durations (Revealing Hardware Glitches)', fontsize=14, pad=15)
    plt.xlabel('Trip Duration (Hours)', fontsize=12)

    # Highlight the absurdity of the anomalies
    plt.annotate('Legitimate Rides', xy=(24, 0), xytext=(500, -0.2),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6))

    plt.annotate('Broken Docks (1000+ hours)', xy=(2000, 0), xytext=(1500, -0.3),
                 arrowprops=dict(facecolor='black', shrink=0.05, width=1, headwidth=6))

    plt.tight_layout()

    # Save the visual directly to the notebooks folder
    output_path = Path("notebooks/trip_outliers_plot.png")
    plt.savefig(output_path, dpi=300)
    print(f"[SUCCESS] Visual saved to: {output_path}")


if __name__ == "__main__":
    generate_outlier_visual()