"""
Synthetic EV Charging Session Data Generator
Generates ~90 days of realistic EV charging session records across multiple stations
with distinctive profiles, morning/evening rush hours, weekend patterns, and power tiers.
"""

import os
import random
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Seed for reproducibility
random.seed(42)
np.random.seed(42)

STATIONS = [
    {
        "station_id": "ST-01",
        "name": "Downtown Fast Hub",
        "location": "Downtown Metro Plaza",
        "total_ports": 8,
        "max_power_kw": 150,
        "type": "Commercial / Fast Charger",
        "base_traffic": 1.4,
        "morning_peak": (8, 10, 1.8),
        "evening_peak": (17, 20, 2.3),
        "weekend_mult": 0.65
    },
    {
        "station_id": "ST-02",
        "name": "Residential North Complex",
        "location": "Greenwood District",
        "total_ports": 12,
        "max_power_kw": 22,
        "type": "Residential / AC",
        "base_traffic": 0.8,
        "morning_peak": (6, 8, 0.9),
        "evening_peak": (19, 23, 2.5),
        "weekend_mult": 1.35
    },
    {
        "station_id": "ST-03",
        "name": "Highway Supercharger West",
        "location": "Interstate 95 Exit 42",
        "total_ports": 16,
        "max_power_kw": 250,
        "type": "Highway / Ultra-Fast",
        "base_traffic": 1.1,
        "morning_peak": (10, 13, 1.6),
        "evening_peak": (16, 19, 2.0),
        "weekend_mult": 1.8
    },
    {
        "station_id": "ST-04",
        "name": "Tech Park Innovation Hub",
        "location": "Silicon Valley Blvd",
        "total_ports": 10,
        "max_power_kw": 50,
        "type": "Workplace / Fleet",
        "base_traffic": 1.2,
        "morning_peak": (8, 11, 2.6),
        "evening_peak": (16, 18, 1.9),
        "weekend_mult": 0.15
    },
    {
        "station_id": "ST-05",
        "name": "Grand Mall & Cinema Plaza",
        "location": "Westfield Retail Center",
        "total_ports": 14,
        "max_power_kw": 50,
        "type": "Retail / Leisure",
        "base_traffic": 0.9,
        "morning_peak": (12, 15, 1.7),
        "evening_peak": (18, 22, 2.4),
        "weekend_mult": 2.2
    },
    {
        "station_id": "ST-06",
        "name": "Airport Long-Stay Station",
        "location": "Terminal 2 Park & Ride",
        "total_ports": 20,
        "max_power_kw": 11,
        "type": "Airport / Overnight",
        "base_traffic": 1.0,
        "morning_peak": (5, 9, 1.5),
        "evening_peak": (17, 21, 1.6),
        "weekend_mult": 1.1
    }
]

VEHICLE_MODELS = [
    {"model": "Tesla Model 3", "battery_kwh": 60, "max_charge_kw": 170},
    {"model": "Tesla Model Y", "battery_kwh": 75, "max_charge_kw": 250},
    {"model": "Hyundai Ioniq 5", "battery_kwh": 77, "max_charge_kw": 220},
    {"model": "Kia EV6", "battery_kwh": 77, "max_charge_kw": 230},
    {"model": "Ford Mustang Mach-E", "battery_kwh": 70, "max_charge_kw": 150},
    {"model": "Nissan Leaf", "battery_kwh": 40, "max_charge_kw": 50},
    {"model": "BMW i4", "battery_kwh": 81, "max_charge_kw": 200},
    {"model": "Tata Nexon EV", "battery_kwh": 40.5, "max_charge_kw": 30},
    {"model": "Mahindra XUV400", "battery_kwh": 39.4, "max_charge_kw": 50},
    {"model": "Chevy Bolt EV", "battery_kwh": 65, "max_charge_kw": 55},
]


def generate_dataset(days: int = 90, output_path: str = None) -> pd.DataFrame:
    """
    Generates historical EV charging sessions.
    """
    end_date = datetime.now().replace(minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days)

    records = []
    session_counter = 10001
    user_pool = [f"USR-{1000 + i}" for i in range(400)]

    current_day = start_date
    while current_day < end_date:
        is_weekend = current_day.weekday() >= 5

        for station in STATIONS:
            # Determine daily session volume for this station
            base_sessions = int(station["total_ports"] * 2.8 * station["base_traffic"])
            if is_weekend:
                daily_sessions = int(base_sessions * station["weekend_mult"])
            else:
                daily_sessions = base_sessions

            # Add random variation
            daily_sessions = max(2, int(daily_sessions * np.random.uniform(0.8, 1.25)))

            # Hourly arrival probability distribution (24 hours)
            hourly_weights = np.ones(24) * 0.3
            # Low night traffic
            hourly_weights[0:6] = 0.1

            # Morning peak
            m_start, m_end, m_weight = station["morning_peak"]
            for h in range(m_start, m_end + 1):
                hourly_weights[h] = m_weight * (0.8 if is_weekend else 1.2)

            # Midday
            hourly_weights[11:15] = 1.0 * (1.5 if is_weekend else 0.9)

            # Evening peak
            e_start, e_end, e_weight = station["evening_peak"]
            for h in range(e_start, e_end + 1):
                hourly_weights[h] = e_weight * (1.3 if is_weekend else 1.1)

            # Normalize weights
            hourly_weights = hourly_weights / hourly_weights.sum()

            # Sample arrival hours
            arrival_hours = np.random.choice(24, size=daily_sessions, p=hourly_weights)

            for hour in arrival_hours:
                minute = np.random.randint(0, 60)
                session_start = current_day + timedelta(hours=int(hour), minutes=int(minute))

                vehicle = random.choice(VEHICLE_MODELS)
                user_id = random.choice(user_pool)
                port_id = f"P-{np.random.randint(1, station['total_ports'] + 1):02d}"

                # Desired SoC (State of charge) delta
                start_soc = np.random.uniform(10, 45)
                target_soc = np.random.uniform(75, 95)
                soc_needed = target_soc - start_soc
                kwh_requested = round((soc_needed / 100.0) * vehicle["battery_kwh"], 2)

                # Effective power is min of station max power and vehicle charge capability
                effective_power_kw = min(station["max_power_kw"], vehicle["max_charge_kw"])
                # Real world efficiency and power curve factor (~85% average output)
                effective_power_kw = effective_power_kw * np.random.uniform(0.75, 0.95)

                # Duration in minutes
                duration_hours = kwh_requested / max(effective_power_kw, 3.0)
                duration_minutes = int(duration_hours * 60) + np.random.randint(5, 25) # idle time added
                session_end = session_start + timedelta(minutes=duration_minutes)

                energy_delivered_kwh = round(kwh_requested * np.random.uniform(0.96, 1.02), 2)
                avg_power_kw = round(energy_delivered_kwh / (duration_minutes / 60.0), 2)

                records.append({
                    "session_id": f"SES-{session_counter}",
                    "station_id": station["station_id"],
                    "station_name": station["name"],
                    "station_type": station["type"],
                    "user_id": user_id,
                    "port_id": port_id,
                    "vehicle_model": vehicle["model"],
                    "start_time": session_start.strftime("%Y-%m-%d %H:%M:%S"),
                    "end_time": session_end.strftime("%Y-%m-%d %H:%M:%S"),
                    "duration_minutes": duration_minutes,
                    "energy_delivered_kwh": energy_delivered_kwh,
                    "avg_power_kw": avg_power_kw,
                    "start_soc_pct": round(start_soc, 1),
                    "end_soc_pct": round(target_soc, 1),
                    "day_of_week": session_start.strftime("%A"),
                    "is_weekend": int(is_weekend)
                })
                session_counter += 1

        current_day += timedelta(days=1)

    df = pd.DataFrame(records)
    # Sort chronologically
    df["start_dt"] = pd.to_datetime(df["start_time"])
    df = df.sort_values("start_dt").drop(columns=["start_dt"]).reset_index(drop=True)

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        print(f"[DATA GENERATOR] Generated {len(df)} sessions across {len(STATIONS)} stations -> {output_path}")

    return df


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    target_csv = os.path.join(current_dir, "sample_charging_data.csv")
    generate_dataset(days=90, output_path=target_csv)
