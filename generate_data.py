"""
Chicago Traffic Intelligence Platform
Data Generation Script - Synthetic Chicago Open Traffic Records
Generates 500K+ realistic traffic records based on Chicago geography
"""

import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
import os

np.random.seed(42)
random.seed(42)

# ── Chicago corridors & intersections ──────────────────────────────────────
CORRIDORS = [
    ("Lake Shore Dr",       41.8781, -87.6168, "arterial"),
    ("Michigan Ave",        41.8796, -87.6237, "arterial"),
    ("Wacker Dr",           41.8874, -87.6369, "arterial"),
    ("State St",            41.8827, -87.6278, "arterial"),
    ("Western Ave",         41.8600, -87.6875, "arterial"),
    ("Ashland Ave",         41.8650, -87.6648, "arterial"),
    ("Chicago Ave",         41.8962, -87.6355, "arterial"),
    ("North Ave",           41.9108, -87.6378, "arterial"),
    ("Cermak Rd",           41.8522, -87.6333, "arterial"),
    ("95th St",             41.7220, -87.6500, "arterial"),
    ("I-90/94 Dan Ryan",    41.8300, -87.6350, "highway"),
    ("I-290 Eisenhower",    41.8700, -87.7200, "highway"),
    ("I-55 Stevenson",      41.7800, -87.6800, "highway"),
    ("I-94 Edens",          42.0100, -87.7200, "highway"),
    ("I-88 East-West",      41.8600, -87.8200, "highway"),
    ("Milwaukee Ave",       41.9200, -87.7000, "arterial"),
    ("Pulaski Rd",          41.8780, -87.7260, "arterial"),
    ("Cicero Ave",          41.8580, -87.7450, "arterial"),
    ("Harlem Ave",          41.8700, -87.8100, "arterial"),
    ("Stony Island Ave",    41.7900, -87.5860, "arterial"),
]

WEATHER = ["Clear", "Clear", "Clear", "Cloudy", "Cloudy", "Rain", "Rain", "Snow", "Fog"]
INCIDENT_TYPES = ["None", "None", "None", "None", "None",
                  "Minor Crash", "Minor Crash", "Stalled Vehicle",
                  "Road Work", "Major Crash", "Flooding"]

# ── Volume model: peaks at AM/PM rush, dip overnight ──────────────────────
def hourly_volume_factor(hour: int, road_type: str) -> float:
    base = {
        "highway": [0.3, 0.2, 0.15, 0.15, 0.25, 0.55,
                    0.90, 1.00, 0.85, 0.70, 0.65, 0.70,
                    0.75, 0.72, 0.70, 0.75, 0.90, 1.00,
                    0.85, 0.72, 0.60, 0.50, 0.42, 0.35],
        "arterial":[0.25, 0.18, 0.13, 0.12, 0.20, 0.45,
                    0.75, 0.88, 0.80, 0.68, 0.65, 0.72,
                    0.78, 0.74, 0.70, 0.74, 0.85, 0.95,
                    0.88, 0.76, 0.62, 0.50, 0.38, 0.28],
    }
    return base[road_type][hour]

def seasonal_factor(month: int) -> float:
    return [0.82, 0.83, 0.88, 0.94, 0.98, 1.00,
            1.02, 1.01, 0.99, 0.96, 0.90, 0.84][month - 1]

def generate_traffic_records(n: int = 500_000) -> pd.DataFrame:
    print(f"Generating {n:,} traffic records...")
    start_date = datetime(2023, 1, 1)
    end_date   = datetime(2023, 12, 31)
    date_range = (end_date - start_date).days

    records = []
    batch   = 10_000

    for i in range(0, n, batch):
        size = min(batch, n - i)
        days     = np.random.randint(0, date_range, size)
        hours    = np.random.randint(0, 24, size)
        minutes  = np.random.choice([0, 15, 30, 45], size)
        cor_idx  = np.random.randint(0, len(CORRIDORS), size)

        timestamps = [
            start_date + timedelta(days=int(d), hours=int(h), minutes=int(m))
            for d, h, m in zip(days, hours, minutes)
        ]

        for j in range(size):
            ts        = timestamps[j]
            corridor  = CORRIDORS[cor_idx[j]]
            hour      = hours[j]
            month     = ts.month
            dow       = ts.weekday()          # 0=Mon … 6=Sun
            road_type = corridor[3]

            vf        = hourly_volume_factor(hour, road_type)
            sf        = seasonal_factor(month)
            wday_f    = 1.0 if dow < 5 else 0.70
            weather   = random.choice(WEATHER)
            wx_f      = {"Clear": 1.0, "Cloudy": 0.97, "Rain": 0.85,
                         "Snow": 0.65, "Fog": 0.78}[weather]

            base_vol  = 4500 if road_type == "highway" else 1800
            volume    = max(10, int(base_vol * vf * sf * wday_f * wx_f
                                    * np.random.uniform(0.88, 1.12)))

            speed_limit = 55 if road_type == "highway" else 30
            speed_f     = 1 - (1 - vf) * 0.45
            avg_speed   = max(5, round(speed_limit * speed_f
                                       * wx_f * np.random.uniform(0.92, 1.08), 1))

            incident   = random.choice(INCIDENT_TYPES)
            if incident != "None":
                avg_speed = max(5, avg_speed * np.random.uniform(0.35, 0.70))

            travel_time_idx = round(speed_limit / max(avg_speed, 1), 2)

            lat = corridor[1] + np.random.uniform(-0.012, 0.012)
            lng = corridor[2] + np.random.uniform(-0.012, 0.012)

            records.append({
                "record_id":         i + j + 1,
                "timestamp":         ts.strftime("%Y-%m-%d %H:%M:%S"),
                "date":              ts.strftime("%Y-%m-%d"),
                "year":              ts.year,
                "month":             month,
                "month_name":        ts.strftime("%B"),
                "day_of_week":       ts.strftime("%A"),
                "hour":              hour,
                "is_weekend":        1 if dow >= 5 else 0,
                "is_peak_hour":      1 if hour in range(7, 9) or hour in range(16, 19) else 0,
                "corridor":          corridor[0],
                "road_type":         road_type,
                "latitude":          round(lat, 6),
                "longitude":         round(lng, 6),
                "traffic_volume":    volume,
                "avg_speed_mph":     round(avg_speed, 1),
                "speed_limit_mph":   speed_limit,
                "travel_time_index": travel_time_idx,
                "weather_condition": weather,
                "incident_type":     incident,
                "has_incident":      0 if incident == "None" else 1,
            })

        if (i // batch) % 5 == 0:
            print(f"  {i + size:>9,} / {n:,} records generated")

    df = pd.DataFrame(records)
    print(f"\n✓ Generated {len(df):,} records")
    return df


if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(out_dir, exist_ok=True)

    df = generate_traffic_records(500_000)

    csv_path = os.path.join(out_dir, "chicago_traffic_records.csv")
    df.to_csv(csv_path, index=False)
    print(f"✓ Saved → {csv_path}")

    sample = df.sample(5_000, random_state=1)
    sample.to_csv(os.path.join(out_dir, "chicago_traffic_sample_5k.csv"), index=False)
    print("✓ Saved 5K sample")

    print("\n── Dataset Summary ──────────────────────────────")
    print(f"  Records   : {len(df):,}")
    print(f"  Date range: {df['date'].min()} → {df['date'].max()}")
    print(f"  Corridors : {df['corridor'].nunique()}")
    print(f"  Avg volume: {df['traffic_volume'].mean():,.0f} vehicles / 15-min")
    print(f"  Incidents : {df['has_incident'].sum():,} ({df['has_incident'].mean()*100:.1f}%)")
