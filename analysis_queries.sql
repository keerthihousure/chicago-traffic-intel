-- ============================================================
-- Chicago Traffic Intelligence Platform
-- SQL Analysis Scripts
-- Database: SQLite (compatible with PostgreSQL / SQL Server)
-- ============================================================

-- ── 0. Schema ────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS traffic_records (
    record_id          INTEGER PRIMARY KEY,
    timestamp          TEXT,
    date               TEXT,
    year               INTEGER,
    month              INTEGER,
    month_name         TEXT,
    day_of_week        TEXT,
    hour               INTEGER,
    is_weekend         INTEGER,
    is_peak_hour       INTEGER,
    corridor           TEXT,
    road_type          TEXT,
    latitude           REAL,
    longitude          REAL,
    traffic_volume     INTEGER,
    avg_speed_mph      REAL,
    speed_limit_mph    INTEGER,
    travel_time_index  REAL,
    weather_condition  TEXT,
    incident_type      TEXT,
    has_incident       INTEGER
);


-- ── 1. PEAK-HOUR CONGESTION ANALYSIS ─────────────────────────────────────
--    Identifies the top congested hours per corridor using window functions
WITH hourly_stats AS (
    SELECT
        corridor,
        road_type,
        hour,
        COUNT(*)                              AS observations,
        AVG(traffic_volume)                   AS avg_volume,
        AVG(avg_speed_mph)                    AS avg_speed,
        AVG(travel_time_index)                AS avg_tti,
        ROUND(AVG(has_incident) * 100, 2)     AS incident_pct
    FROM traffic_records
    WHERE is_weekend = 0          -- weekdays only
    GROUP BY corridor, road_type, hour
),
ranked AS (
    SELECT *,
        RANK() OVER (
            PARTITION BY corridor
            ORDER BY avg_tti DESC
        ) AS congestion_rank
    FROM hourly_stats
)
SELECT
    corridor,
    road_type,
    hour                                               AS peak_hour,
    PRINTF('%02d:00 – %02d:00', hour, hour + 1)        AS time_window,
    ROUND(avg_volume)                                  AS avg_volume,
    ROUND(avg_speed, 1)                                AS avg_speed_mph,
    ROUND(avg_tti, 3)                                  AS travel_time_index,
    incident_pct                                       AS incident_pct,
    congestion_rank
FROM ranked
WHERE congestion_rank <= 3
ORDER BY corridor, congestion_rank;


-- ── 2. HIGH-INCIDENT CORRIDOR RANKING ────────────────────────────────────
--    Ranks corridors by incident frequency & severity impact on speed
WITH corridor_incidents AS (
    SELECT
        corridor,
        road_type,
        incident_type,
        COUNT(*)                                         AS incident_count,
        AVG(avg_speed_mph)                               AS avg_speed_during,
        AVG(speed_limit_mph) - AVG(avg_speed_mph)        AS avg_speed_reduction
    FROM traffic_records
    WHERE has_incident = 1
    GROUP BY corridor, road_type, incident_type
),
corridor_totals AS (
    SELECT
        corridor,
        SUM(incident_count)                              AS total_incidents,
        AVG(avg_speed_during)                            AS avg_speed_incidents,
        AVG(avg_speed_reduction)                         AS avg_speed_reduction,
        SUM(CASE WHEN incident_type = 'Major Crash'
                 THEN incident_count ELSE 0 END)         AS major_crashes,
        SUM(CASE WHEN incident_type = 'Minor Crash'
                 THEN incident_count ELSE 0 END)         AS minor_crashes,
        SUM(CASE WHEN incident_type = 'Road Work'
                 THEN incident_count ELSE 0 END)         AS road_works
    FROM corridor_incidents
    GROUP BY corridor
),
all_records AS (
    SELECT corridor, COUNT(*) AS total_records
    FROM traffic_records
    GROUP BY corridor
)
SELECT
    ct.corridor,
    ar.total_records,
    ct.total_incidents,
    ROUND(ct.total_incidents * 100.0 / ar.total_records, 2)  AS incident_rate_pct,
    ct.major_crashes,
    ct.minor_crashes,
    ct.road_works,
    ROUND(ct.avg_speed_incidents, 1)                         AS avg_speed_during_incident,
    ROUND(ct.avg_speed_reduction, 1)                         AS mph_lost_to_incidents,
    RANK() OVER (ORDER BY ct.total_incidents DESC)           AS incident_rank
FROM corridor_totals ct
JOIN all_records ar ON ct.corridor = ar.corridor
ORDER BY ct.total_incidents DESC;


-- ── 3. SEASONAL VOLUME TRENDS ─────────────────────────────────────────────
--    Month-over-month traffic volume changes with rolling 3-month avg
WITH monthly_volume AS (
    SELECT
        month,
        month_name,
        road_type,
        COUNT(*)                    AS total_records,
        ROUND(AVG(traffic_volume))  AS avg_volume,
        SUM(traffic_volume)         AS total_volume,
        ROUND(AVG(avg_speed_mph), 1) AS avg_speed,
        ROUND(AVG(has_incident) * 100, 2) AS incident_pct
    FROM traffic_records
    GROUP BY month, month_name, road_type
),
with_lag AS (
    SELECT *,
        LAG(avg_volume, 1) OVER (
            PARTITION BY road_type ORDER BY month
        ) AS prev_month_volume,
        AVG(avg_volume) OVER (
            PARTITION BY road_type
            ORDER BY month
            ROWS BETWEEN 1 PRECEDING AND 1 FOLLOWING
        ) AS rolling_3mo_avg
    FROM monthly_volume
)
SELECT
    month,
    month_name,
    road_type,
    avg_volume,
    ROUND(rolling_3mo_avg)                                          AS rolling_3mo_avg,
    ROUND((avg_volume - prev_month_volume) * 100.0
          / NULLIF(prev_month_volume, 0), 2)                        AS mom_change_pct,
    avg_speed,
    incident_pct
FROM with_lag
ORDER BY road_type, month;


-- ── 4. WEATHER IMPACT ON THROUGHPUT ──────────────────────────────────────
SELECT
    weather_condition,
    road_type,
    COUNT(*)                                              AS records,
    ROUND(AVG(traffic_volume))                            AS avg_volume,
    ROUND(AVG(avg_speed_mph), 1)                          AS avg_speed,
    ROUND(AVG(travel_time_index), 3)                      AS avg_tti,
    ROUND(AVG(has_incident) * 100, 2)                     AS incident_pct,
    -- compare to clear-weather baseline using ratio
    ROUND(AVG(avg_speed_mph) / MAX(AVG(avg_speed_mph))
          OVER (PARTITION BY road_type), 3)               AS speed_ratio_vs_best
FROM traffic_records
GROUP BY weather_condition, road_type
ORDER BY road_type, avg_speed DESC;


-- ── 5. WEEKEND vs WEEKDAY PATTERNS ───────────────────────────────────────
WITH day_hour AS (
    SELECT
        CASE WHEN is_weekend = 1 THEN 'Weekend' ELSE 'Weekday' END AS day_type,
        hour,
        AVG(traffic_volume)    AS avg_volume,
        AVG(avg_speed_mph)     AS avg_speed,
        AVG(travel_time_index) AS avg_tti
    FROM traffic_records
    GROUP BY is_weekend, hour
)
SELECT
    day_type,
    hour,
    PRINTF('%02d:00', hour)   AS time_label,
    ROUND(avg_volume)         AS avg_volume,
    ROUND(avg_speed, 1)       AS avg_speed_mph,
    ROUND(avg_tti, 3)         AS travel_time_index,
    ROUND(avg_volume * 100.0 / SUM(avg_volume) OVER (
        PARTITION BY day_type), 2) AS pct_of_daily_volume
FROM day_hour
ORDER BY day_type, hour;


-- ── 6. KPI SUMMARY TABLE (for Power BI cards) ────────────────────────────
SELECT
    COUNT(*)                                          AS total_records,
    SUM(traffic_volume)                               AS total_vehicles,
    ROUND(AVG(traffic_volume))                        AS avg_volume_per_interval,
    ROUND(AVG(avg_speed_mph), 1)                      AS network_avg_speed_mph,
    ROUND(AVG(travel_time_index), 3)                  AS network_avg_tti,
    SUM(has_incident)                                 AS total_incidents,
    ROUND(AVG(has_incident) * 100, 2)                 AS overall_incident_rate_pct,
    COUNT(DISTINCT corridor)                          AS corridors_monitored,
    COUNT(DISTINCT date)                              AS days_monitored
FROM traffic_records;
