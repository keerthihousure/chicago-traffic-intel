"""
Chicago Traffic Intelligence Platform
EDA & Chart Generation — produces all visuals used in the README & dashboard
"""

import sqlite3, os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.gridspec import GridSpec
import warnings
warnings.filterwarnings("ignore")

# ── paths ──────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
ROOT    = os.path.join(BASE, "..")
DATA    = os.path.join(ROOT, "data", "chicago_traffic_records.csv")
DB      = os.path.join(ROOT, "data", "chicago_traffic.db")
OUTDIR  = os.path.join(ROOT, "screenshots")
os.makedirs(OUTDIR, exist_ok=True)

# ── palette ────────────────────────────────────────────────────────────────
BG      = "#0d1117"
CARD    = "#161b22"
ACCENT  = "#00c8ff"
ORANGE  = "#ff6b35"
GREEN   = "#39d353"
PURPLE  = "#8957e5"
RED     = "#f85149"
TEXT    = "#e6edf3"
MUTED   = "#8b949e"

plt.rcParams.update({
    "figure.facecolor": BG, "axes.facecolor": CARD,
    "text.color": TEXT, "axes.labelcolor": TEXT,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.spines.left": False, "axes.spines.bottom": False,
    "axes.grid": True, "grid.color": "#21262d", "grid.linewidth": 0.6,
    "font.family": "monospace",
})

# ── load data ──────────────────────────────────────────────────────────────
print("Loading data …")
df = pd.read_csv(DATA, parse_dates=["timestamp"])
print(f"  {len(df):,} records loaded")

# also load into SQLite so SQL scripts can run
print("Building SQLite DB …")
conn = sqlite3.connect(DB)
df.to_sql("traffic_records", conn, if_exists="replace", index=False)
conn.commit()

def sql(q): return pd.read_sql_query(q, conn)

# ──────────────────────────────────────────────────────────────────────────
# CHART 1 — Hourly Volume: Weekday vs Weekend (line)
# ──────────────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 5))
fig.patch.set_facecolor(BG)
ax.set_facecolor(CARD)

for is_wknd, label, color in [(0, "Weekday", ACCENT), (1, "Weekend", ORANGE)]:
    g = df[df.is_weekend == is_wknd].groupby("hour")["traffic_volume"].mean()
    ax.plot(g.index, g.values, color=color, lw=2.5, label=label, marker="o",
            markersize=4, markerfacecolor=color)
    ax.fill_between(g.index, g.values, alpha=0.12, color=color)

# shade AM/PM peaks
for start, end in [(7, 9), (16, 19)]:
    ax.axvspan(start, end, color=ACCENT, alpha=0.07, label="_")

ax.set_title("Average Traffic Volume by Hour  |  Weekday vs Weekend",
             fontsize=14, fontweight="bold", color=TEXT, pad=14)
ax.set_xlabel("Hour of Day", fontsize=11)
ax.set_ylabel("Avg Vehicles / 15-min Interval", fontsize=11)
ax.set_xticks(range(0, 24))
ax.set_xticklabels([f"{h:02d}:00" for h in range(24)], rotation=45, fontsize=8)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(frameon=False, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "01_hourly_volume.png"), dpi=150, bbox_inches="tight")
plt.close(); print("✓ Chart 1 saved")

# ──────────────────────────────────────────────────────────────────────────
# CHART 2 — Top 10 High-Incident Corridors (horizontal bar)
# ──────────────────────────────────────────────────────────────────────────
inc = (df[df.has_incident == 1]
       .groupby("corridor")["has_incident"].count()
       .sort_values(ascending=True).tail(10))

fig, ax = plt.subplots(figsize=(12, 6))
fig.patch.set_facecolor(BG); ax.set_facecolor(CARD)

colors = [RED if v == inc.max() else ORANGE if v >= inc.quantile(0.75) else ACCENT
          for v in inc.values]
bars = ax.barh(inc.index, inc.values, color=colors, height=0.65, edgecolor="none")

for bar, val in zip(bars, inc.values):
    ax.text(val + 200, bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", fontsize=10, color=TEXT, fontweight="bold")

ax.set_title("Top 10 High-Incident Corridors — Full Year 2023",
             fontsize=14, fontweight="bold", color=TEXT, pad=14)
ax.set_xlabel("Total Incidents Recorded", fontsize=11)
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "02_incident_corridors.png"), dpi=150, bbox_inches="tight")
plt.close(); print("✓ Chart 2 saved")

# ──────────────────────────────────────────────────────────────────────────
# CHART 3 — Seasonal Volume Trends (area chart by road type)
# ──────────────────────────────────────────────────────────────────────────
months = range(1, 13)
month_labels = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]

fig, ax = plt.subplots(figsize=(12, 5))
fig.patch.set_facecolor(BG); ax.set_facecolor(CARD)

for road_type, color in [("highway", ACCENT), ("arterial", ORANGE)]:
    g = (df[df.road_type == road_type]
         .groupby("month")["traffic_volume"].mean())
    ax.plot(g.index, g.values, color=color, lw=2.5,
            label=road_type.title(), marker="o", markersize=5)
    ax.fill_between(g.index, g.values, alpha=0.15, color=color)

ax.set_xticks(list(months))
ax.set_xticklabels(month_labels, fontsize=10)
ax.set_title("Monthly Average Traffic Volume by Road Type — 2023",
             fontsize=14, fontweight="bold", color=TEXT, pad=14)
ax.set_ylabel("Avg Vehicles / 15-min Interval", fontsize=11)
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
ax.legend(frameon=False, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "03_seasonal_trends.png"), dpi=150, bbox_inches="tight")
plt.close(); print("✓ Chart 3 saved")

# ──────────────────────────────────────────────────────────────────────────
# CHART 4 — Weather Impact on Avg Speed (grouped bar)
# ──────────────────────────────────────────────────────────────────────────
weather_order = ["Clear", "Cloudy", "Rain", "Fog", "Snow"]
g = (df.groupby(["weather_condition", "road_type"])["avg_speed_mph"]
     .mean().unstack("road_type").loc[weather_order])

fig, ax = plt.subplots(figsize=(10, 5))
fig.patch.set_facecolor(BG); ax.set_facecolor(CARD)

x  = np.arange(len(weather_order))
w  = 0.35
ax.bar(x - w/2, g["arterial"], w, label="Arterial", color=ORANGE, alpha=0.9)
ax.bar(x + w/2, g["highway"],  w, label="Highway",  color=ACCENT,  alpha=0.9)

ax.set_xticks(x); ax.set_xticklabels(weather_order, fontsize=11)
ax.set_ylabel("Avg Speed (mph)", fontsize=11)
ax.set_title("Weather Condition Impact on Average Speed",
             fontsize=14, fontweight="bold", color=TEXT, pad=14)
ax.legend(frameon=False, fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "04_weather_impact.png"), dpi=150, bbox_inches="tight")
plt.close(); print("✓ Chart 4 saved")

# ──────────────────────────────────────────────────────────────────────────
# CHART 5 — Heatmap: Hour × Day-of-Week (Travel Time Index)
# ──────────────────────────────────────────────────────────────────────────
dow_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
pivot = (df.groupby(["day_of_week","hour"])["travel_time_index"]
         .mean().unstack("hour").reindex(dow_order))

fig, ax = plt.subplots(figsize=(14, 5))
fig.patch.set_facecolor(BG); ax.set_facecolor(BG)

im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd",
               vmin=pivot.values.min(), vmax=pivot.values.max())

ax.set_yticks(range(7)); ax.set_yticklabels(dow_order, fontsize=10)
ax.set_xticks(range(24)); ax.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=9)
ax.set_xlabel("Hour of Day", fontsize=11)
ax.set_title("Congestion Heatmap — Travel Time Index by Day & Hour",
             fontsize=14, fontweight="bold", color=TEXT, pad=14)
cb = fig.colorbar(im, ax=ax, shrink=0.8, pad=0.02)
cb.set_label("Travel Time Index", color=TEXT, fontsize=10)
cb.ax.yaxis.set_tick_params(color=MUTED)
plt.setp(cb.ax.yaxis.get_ticklabels(), color=TEXT, fontsize=9)
fig.tight_layout()
fig.savefig(os.path.join(OUTDIR, "05_congestion_heatmap.png"), dpi=150, bbox_inches="tight")
plt.close(); print("✓ Chart 5 saved")

conn.close()
print("\n── All charts saved to /screenshots/ ───────────────")
