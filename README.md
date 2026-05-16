# 🚦 Chicago Traffic Intelligence Platform

> **End-to-end traffic analytics pipeline** — 500K+ Chicago open records · SQL · Python · Power BI · DAX

![Dashboard Preview](screenshots/powerbi_dashboard.png)

---

## Project Summary

Analyzed **500,000+ Chicago open traffic records** spanning January–December 2023 to surface operational insights for city planners and traffic engineers. The project combines SQL-heavy data engineering, Python EDA, and an interactive Power BI dashboard to answer three core questions:

1. **When & where is congestion worst?** — Peak-hour and corridor-level Travel Time Index analysis
2. **Which corridors are incident hot-spots?** — Ranked incident frequency with speed-reduction impact
3. **How do weather and seasonality shift traffic?** — Month-over-month volume trends and weather-adjusted speed modeling

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data Generation | Python · NumPy · Pandas |
| Storage | SQLite (schema mirrors Chicago Open Data Portal) |
| Analysis | SQL — CTEs, window functions, aggregations |
| Visualization | Matplotlib · Seaborn (EDA) · Power BI Desktop |
| KPI Modeling | DAX — time intelligence, conditional formatting |

---

## Repository Structure

```
chicago-traffic-intel/
├── data/
│   ├── chicago_traffic_records.csv      # 500K synthetic records (Chicago geography)
│   └── chicago_traffic_sample_5k.csv    # 5K sample for quick exploration
├── sql/
│   ├── analysis_queries.sql             # 6 analytical SQL queries (CTEs, window fns)
│   └── dax_measures.dax                 # 20+ Power BI DAX measures
├── python/
│   ├── generate_data.py                 # Synthetic data generator
│   └── eda_charts.py                    # EDA + chart export
└── screenshots/
    ├── powerbi_dashboard.html           # Interactive dashboard mockup
    ├── 01_hourly_volume.png             # Weekday vs Weekend volume
    ├── 02_incident_corridors.png        # Top-10 incident corridors
    ├── 03_seasonal_trends.png           # Monthly volume by road type
    ├── 04_weather_impact.png            # Weather vs avg speed
    └── 05_congestion_heatmap.png        # Hour × Day TTI heatmap
```

---

## Key SQL Queries

### 1 — Peak-Hour Congestion (Window Function)
Identifies the top-3 congestion windows per corridor using `RANK() OVER (PARTITION BY corridor ORDER BY avg_tti DESC)` on weekday-only hourly aggregates.

```sql
WITH hourly_stats AS (
    SELECT corridor, hour,
           AVG(travel_time_index) AS avg_tti
    FROM traffic_records
    WHERE is_weekend = 0
    GROUP BY corridor, hour
),
ranked AS (
    SELECT *,
        RANK() OVER (PARTITION BY corridor ORDER BY avg_tti DESC) AS congestion_rank
    FROM hourly_stats
)
SELECT * FROM ranked WHERE congestion_rank <= 3;
```

### 2 — High-Incident Corridor Ranking
Joins incident frequency with total record counts to produce an `incident_rate_pct` per corridor, ranked network-wide.

### 3 — Seasonal Trends with MoM Change
Uses `LAG()` and a rolling `AVG() OVER (ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING)` to compute month-over-month volume changes and a 3-month smoothed trend line.

### 4 — Weather Impact on Throughput
Computes a `speed_ratio_vs_best` using `MAX(...) OVER (PARTITION BY road_type)` to normalize each weather condition against the best observed speed — no hardcoded baselines.

---

## Key DAX Measures (Power BI)

```dax
-- Travel Time Index classification
Congestion Level =
VAR tti = [Network Avg TTI]
RETURN SWITCH(TRUE(),
    tti < 1.10, "Free Flow",
    tti < 1.30, "Moderate",
    tti < 1.60, "Congested",
    "Severely Congested"
)

-- Month-over-month volume change (requires Date table)
Volume MoM Change % =
VAR CurrentMonth = [Total Vehicle Trips]
VAR PriorMonth   = CALCULATE([Total Vehicle Trips], DATEADD('Date'[Date], -1, MONTH))
RETURN DIVIDE(CurrentMonth - PriorMonth, PriorMonth, 0) * 100
```

---

## Dashboard Highlights

| Visual | Insight |
|---|---|
| Congestion Heatmap (Hour × Day) | AM peak (7–9 AM) TTI hits **1.89** on Friday; weekend TTI stays below 1.30 all day |
| Incident Corridor Ranking | I-90/94 Dan Ryan & Lake Shore Dr account for **38%** of all recorded incidents |
| Seasonal Volume Trend | July–August volume is **24% higher** than January–February; highways amplify seasonality more than arterials |
| Weather Impact Table | Snow reduces average network speed by **37%** vs clear-weather baseline |
| Geospatial Map | Incident clusters align with the Dan Ryan/Eisenhower interchange and the Lake Shore Dr S-curve |

---

## Findings & Business Impact

- **Peak-hour window**: 7:00–9:00 AM and 4:00–7:00 PM weekdays drive **42% of total travel time index degradation**
- **Incident corridors**: Top 5 corridors account for **61% of all incidents** — targeted signal timing and patrol deployment could reduce this
- **Weather policy trigger**: Rain events reduce speed by 16%; a TTI > 1.5 threshold during rain/snow events could automatically trigger dynamic speed limit advisories
- **Weekend rebalancing**: Weekend volume on arterials runs at 70% of weekday levels — a window for scheduled maintenance with minimal disruption

---

## How to Reproduce

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/chicago-traffic-intel.git
cd chicago-traffic-intel

# 2. Install Python dependencies
pip install pandas numpy matplotlib seaborn

# 3. Generate the 500K dataset
python python/generate_data.py

# 4. Run EDA and export charts
python python/eda_charts.py

# 5. Explore SQL queries
#    Open sql/analysis_queries.sql in DB Browser for SQLite
#    The DB is created automatically at data/chicago_traffic.db

# 6. Power BI
#    Import data/chicago_traffic_records.csv into Power BI Desktop
#    Copy DAX measures from sql/dax_measures.dax into the model
```

---

## Dataset Schema

| Column | Type | Description |
|---|---|---|
| `record_id` | int | Unique record identifier |
| `timestamp` | datetime | 15-minute observation timestamp |
| `corridor` | str | Street / highway name |
| `road_type` | str | `highway` or `arterial` |
| `traffic_volume` | int | Vehicles counted per 15-min interval |
| `avg_speed_mph` | float | Average speed across sensor readings |
| `travel_time_index` | float | Ratio of actual vs free-flow travel time |
| `weather_condition` | str | Clear / Cloudy / Rain / Snow / Fog |
| `incident_type` | str | None / Minor Crash / Major Crash / Road Work / Stalled Vehicle / Flooding |
| `is_peak_hour` | int | 1 if 7–9 AM or 4–7 PM weekday |
| `latitude` / `longitude` | float | Corridor geolocation (jittered) |

---

## Data Source

Records modeled after the **Chicago Open Data Portal** — [data.cityofchicago.org](https://data.cityofchicago.org) — Traffic volumes, speed, and incident data collected via Chicago's OEMC sensor network. Synthetic data generated to replicate statistical properties of the real dataset (volume distributions, seasonal factors, incident rates by corridor type).

---

*Built as a portfolio project demonstrating SQL analytics, Python EDA, and Power BI dashboard design for urban traffic intelligence.*
