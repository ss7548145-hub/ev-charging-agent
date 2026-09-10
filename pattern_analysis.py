"""
Charging Pattern Analysis Module
Analyzes historical charging session data to compute:
- Per-station utilization %
- Peak usage hours and congestion levels
- Hourly, daily, and weekday vs. weekend demand profiles
- 7x24 heatmap matrix of station occupancy
"""

import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd

DEFAULT_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "sample_charging_data.csv"
)

# In-memory cache for fast response times
_CACHED_DF: Optional[pd.DataFrame] = None


def load_charging_data(filepath: str = DEFAULT_DATA_PATH) -> pd.DataFrame:
    """
    Loads and cleans charging session data from CSV with datetime parsing.
    """
    global _CACHED_DF
    if _CACHED_DF is not None and filepath == DEFAULT_DATA_PATH:
        return _CACHED_DF

    if not os.path.exists(filepath):
        # Auto-generate if missing
        from backend.data.generate_data import generate_dataset
        df = generate_dataset(days=90, output_path=filepath)
    else:
        df = pd.read_csv(filepath)

    df["start_time"] = pd.to_datetime(df["start_time"])
    df["end_time"] = pd.to_datetime(df["end_time"])
    df["hour"] = df["start_time"].dt.hour
    df["day_name"] = df["start_time"].dt.day_name()
    df["day_index"] = df["start_time"].dt.dayofweek # 0=Mon, 6=Sun
    df["date"] = df["start_time"].dt.date

    if filepath == DEFAULT_DATA_PATH:
        _CACHED_DF = df
    return df


def get_stations_summary(filepath: str = DEFAULT_DATA_PATH) -> List[Dict[str, Any]]:
    """
    Returns high-level metadata and aggregate utilization metrics for all stations.
    """
    df = load_charging_data(filepath)
    stations_summary = []

    for station_id, group in df.groupby("station_id"):
        first_row = group.iloc[0]
        total_energy = float(group["energy_delivered_kwh"].sum())
        total_sessions = int(len(group))
        avg_duration = float(group["duration_minutes"].mean())
        avg_energy_session = float(group["energy_delivered_kwh"].mean())

        # Determine total ports and capacity
        ports_count = int(group["port_id"].nunique())
        
        # Calculate overall utilization %
        # Total available port-hours over 90 days = ports * 90 days * 24h * 60m
        total_days = max(1, (group["start_time"].max() - group["start_time"].min()).days)
        total_available_minutes = ports_count * total_days * 24 * 60
        total_occupied_minutes = group["duration_minutes"].sum()
        utilization_pct = min(100.0, round((total_occupied_minutes / total_available_minutes) * 100.0, 1))

        # Peak hour identification
        hourly_counts = group.groupby("hour")["session_id"].count()
        peak_hour = int(hourly_counts.idxmax())

        stations_summary.append({
            "station_id": station_id,
            "station_name": first_row["station_name"],
            "station_type": first_row["station_type"],
            "total_ports": ports_count,
            "total_sessions": total_sessions,
            "total_energy_kwh": round(total_energy, 1),
            "avg_duration_minutes": round(avg_duration, 1),
            "avg_energy_per_session_kwh": round(avg_energy_session, 2),
            "utilization_pct": utilization_pct,
            "peak_hour": peak_hour,
            "peak_hour_formatted": f"{peak_hour:02d}:00 - {(peak_hour+1)%24:02d}:00"
        })

    return sorted(stations_summary, key=lambda x: x["station_id"])


def analyze_station_patterns(station_id: str, filepath: str = DEFAULT_DATA_PATH) -> Dict[str, Any]:
    """
    Performs in-depth pattern analysis for a specific station (or ALL stations if 'ALL').
    Returns:
    - Peak hours ranking & congestion thresholds
    - Hourly demand profile (0-23)
    - Weekday vs Weekend breakdown
    - Day-of-week profile (Mon-Sun)
    - 7x24 Heatmap Matrix
    - High-level KPIs
    """
    df = load_charging_data(filepath)

    if station_id and station_id.upper() != "ALL":
        station_df = df[df["station_id"] == station_id].copy()
        if station_df.empty:
            raise ValueError(f"Station ID '{station_id}' not found in historical data.")
        station_name = station_df["station_name"].iloc[0]
        station_type = station_df["station_type"].iloc[0]
        total_ports = int(station_df["port_id"].nunique())
    else:
        station_df = df.copy()
        station_id = "ALL"
        station_name = "All Network Stations"
        station_type = "Full Grid Aggregation"
        total_ports = int(df.groupby(["station_id", "port_id"]).ngroups)

    # Date range
    total_days = max(1, (station_df["start_time"].max() - station_df["start_time"].min()).days)
    total_energy_kwh = float(station_df["energy_delivered_kwh"].sum())
    total_sessions = int(len(station_df))
    avg_session_duration = float(station_df["duration_minutes"].mean())
    avg_power_kw = float(station_df["avg_power_kw"].mean())

    # Overall Station Utilization
    total_available_minutes = total_ports * total_days * 24 * 60
    total_occupied_minutes = station_df["duration_minutes"].sum()
    overall_utilization_pct = min(100.0, round((total_occupied_minutes / total_available_minutes) * 100.0, 1))

    # 1. Hourly Profile (0-23)
    hourly_stats = []
    hourly_group = station_df.groupby("hour")
    
    # Calculate hourly average sessions per day and average kWh
    hourly_sessions = hourly_group["session_id"].count() / total_days
    hourly_energy = hourly_group["energy_delivered_kwh"].sum() / total_days
    hourly_avg_power = hourly_group["avg_power_kw"].mean()

    max_hourly_energy = max(hourly_energy.max(), 1.0)

    for h in range(24):
        sess_count = float(hourly_sessions.get(h, 0.0))
        kwh_val = float(hourly_energy.get(h, 0.0))
        power_val = float(hourly_avg_power.get(h, 0.0))
        
        # Utilization in this hour: concurrent occupied ports estimate
        # Average sessions per hour * avg duration in hours / ports
        est_concurrent_chargers = min(float(total_ports), (sess_count * (avg_session_duration / 60.0)))
        hourly_util_pct = min(100.0, round((est_concurrent_chargers / max(1, total_ports)) * 100.0, 1))

        # Congestion classification
        if hourly_util_pct >= 65.0:
            congestion_level = "High / Peak"
        elif hourly_util_pct >= 35.0:
            congestion_level = "Moderate"
        else:
            congestion_level = "Low / Off-Peak"

        hourly_stats.append({
            "hour": h,
            "hour_label": f"{h:02d}:00",
            "avg_sessions_per_day": round(sess_count, 2),
            "avg_energy_kwh": round(kwh_val, 2),
            "avg_power_kw": round(power_val, 1),
            "utilization_pct": hourly_util_pct,
            "congestion_level": congestion_level
        })

    # Peak Hours Identification (sorted by utilization)
    sorted_hours = sorted(hourly_stats, key=lambda x: x["utilization_pct"], reverse=True)
    peak_hours = [item["hour"] for item in sorted_hours[:4]]
    off_peak_hours = [item["hour"] for item in sorted_hours[-6:]]

    # 2. Weekday vs Weekend Comparison
    weekday_df = station_df[station_df["is_weekend"] == 0]
    weekend_df = station_df[station_df["is_weekend"] == 1]

    num_weekdays = max(1, len(set(weekday_df["date"])))
    num_weekends = max(1, len(set(weekend_df["date"])))

    weekday_hourly = weekday_df.groupby("hour")["energy_delivered_kwh"].sum() / num_weekdays
    weekend_hourly = weekend_df.groupby("hour")["energy_delivered_kwh"].sum() / num_weekends

    weekday_vs_weekend = []
    for h in range(24):
        weekday_vs_weekend.append({
            "hour": h,
            "hour_label": f"{h:02d}:00",
            "weekday_kwh": round(float(weekday_hourly.get(h, 0.0)), 2),
            "weekend_kwh": round(float(weekend_hourly.get(h, 0.0)), 2),
        })

    # 3. Day of Week Breakdown (Monday - Sunday)
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    day_stats = []
    for idx, day_name in enumerate(day_names):
        sub_df = station_df[station_df["day_index"] == idx]
        num_specific_days = max(1, len(set(sub_df["date"])))
        day_total_kwh = float(sub_df["energy_delivered_kwh"].sum()) / num_specific_days
        day_sessions = float(len(sub_df)) / num_specific_days

        day_stats.append({
            "day_index": idx,
            "day_name": day_name,
            "avg_daily_kwh": round(day_total_kwh, 2),
            "avg_daily_sessions": round(day_sessions, 1),
            "is_weekend": idx >= 5
        })

    # 4. 7x24 Heatmap Matrix
    # Matrix rows = Day of week (0..6), Cols = Hour of day (0..23), Value = Utilization % (0-100)
    heatmap_matrix = []
    for day_idx, day_name in enumerate(day_names):
        day_sub = station_df[station_df["day_index"] == day_idx]
        num_days = max(1, len(set(day_sub["date"])))
        hourly_counts = day_sub.groupby("hour")["session_id"].count() / num_days

        row_values = []
        for h in range(24):
            sess_rate = float(hourly_counts.get(h, 0.0))
            est_ports_used = sess_rate * (avg_session_duration / 60.0)
            cell_util = min(100.0, round((est_ports_used / max(1, total_ports)) * 100.0, 1))
            row_values.append({
                "hour": h,
                "hour_label": f"{h:02d}:00",
                "utilization_pct": cell_util
            })

        heatmap_matrix.append({
            "day_index": day_idx,
            "day_name": day_name,
            "hours": row_values
        })

    return {
        "station_id": station_id,
        "station_name": station_name,
        "station_type": station_type,
        "total_ports": total_ports,
        "metrics": {
            "total_energy_delivered_kwh": round(total_energy_kwh, 1),
            "total_sessions": total_sessions,
            "overall_utilization_pct": overall_utilization_pct,
            "avg_session_duration_minutes": round(avg_session_duration, 1),
            "avg_power_kw": round(avg_power_kw, 1),
            "analyzed_days": total_days
        },
        "peak_hours": peak_hours,
        "off_peak_hours": off_peak_hours,
        "hourly_profile": hourly_stats,
        "weekday_vs_weekend": weekday_vs_weekend,
        "day_of_week_profile": day_stats,
        "heatmap_matrix": heatmap_matrix
    }


if __name__ == "__main__":
    summary = get_stations_summary()
    print("Stations Summary:", len(summary))
    analysis = analyze_station_patterns("ST-01")
    print(f"Station 1 Overall Utilization: {analysis['metrics']['overall_utilization_pct']}%")
    print(f"Station 1 Peak Hours: {analysis['peak_hours']}")
