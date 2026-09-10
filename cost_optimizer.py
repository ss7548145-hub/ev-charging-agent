"""
Cost Optimization Insights Module
Models dynamic Time-of-Use (TOU) electricity tariff structures and calculates
monetary costs, savings opportunities, and tariff breakdowns across charging windows.
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta

# Standard Commercial EV Time-of-Use (TOU) Rate Table ($/kWh)
DEFAULT_TARIFF_SCHEDULE = {
    "super_off_peak": {
        "rate": 0.10,
        "label": "Super Off-Peak",
        "color": "#10b981", # Emerald
        "hours": [0, 1, 2, 3, 4, 5]
    },
    "off_peak": {
        "rate": 0.18,
        "label": "Off-Peak",
        "color": "#06b6d4", # Cyan
        "hours": [6, 7, 8, 9, 10, 11, 12, 13, 21, 22, 23]
    },
    "mid_peak": {
        "rate": 0.28,
        "label": "Mid-Peak",
        "color": "#f59e0b", # Amber
        "hours": [14, 15, 16]
    },
    "peak": {
        "rate": 0.42,
        "label": "On-Peak",
        "color": "#ef4444", # Red / Rose
        "hours": [17, 18, 19, 20]
    }
}


def get_tariff_for_hour(hour: int, schedule: Dict[str, Any] = None) -> Tuple[float, str, str]:
    """
    Returns (rate_per_kwh, tier_name, color) for a given hour of day (0-23).
    """
    schedule = schedule or DEFAULT_TARIFF_SCHEDULE
    normalized_hour = hour % 24
    for tier_key, tier_info in schedule.items():
        if normalized_hour in tier_info["hours"]:
            return tier_info["rate"], tier_info["label"], tier_info["color"]
    return 0.20, "Standard Rate", "#6b7280"


def calculate_session_cost(
    start_time: datetime,
    duration_minutes: int,
    kwh_delivered: float,
    schedule: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Accurately computes total electricity cost for a session that may span
    multiple tariff periods by integrating across minute-by-minute or hourly slices.
    """
    if duration_minutes <= 0 or kwh_delivered <= 0:
        return {"total_cost": 0.0, "avg_rate_per_kwh": 0.0, "tier_breakdown": {}}

    avg_power_kw = kwh_delivered / (duration_minutes / 60.0)
    end_time = start_time + timedelta(minutes=duration_minutes)

    total_cost = 0.0
    tier_energy = {tier["label"]: 0.0 for tier in (schedule or DEFAULT_TARIFF_SCHEDULE).values()}
    tier_cost = {tier["label"]: 0.0 for tier in (schedule or DEFAULT_TARIFF_SCHEDULE).values()}

    # Step through time in 15-minute intervals for precision
    curr_time = start_time
    interval_minutes = 15

    while curr_time < end_time:
        next_time = min(curr_time + timedelta(minutes=interval_minutes), end_time)
        slice_mins = (next_time - curr_time).total_seconds() / 60.0
        slice_kwh = avg_power_kw * (slice_mins / 60.0)

        rate, label, _ = get_tariff_for_hour(curr_time.hour, schedule)
        slice_cost = slice_kwh * rate

        total_cost += slice_cost
        tier_energy[label] = tier_energy.get(label, 0.0) + slice_kwh
        tier_cost[label] = tier_cost.get(label, 0.0) + slice_cost

        curr_time = next_time

    avg_rate = total_cost / kwh_delivered if kwh_delivered > 0 else 0.0

    return {
        "total_cost": round(total_cost, 2),
        "avg_rate_per_kwh": round(avg_rate, 4),
        "kwh_delivered": round(kwh_delivered, 2),
        "duration_minutes": duration_minutes,
        "start_time": start_time.strftime("%Y-%m-%d %H:%M"),
        "end_time": end_time.strftime("%Y-%m-%d %H:%M"),
        "tier_breakdown": {
            k: {
                "kwh": round(tier_energy[k], 2),
                "cost": round(tier_cost[k], 2)
            }
            for k in tier_energy if tier_energy[k] > 0
        }
    }


def compare_charging_scenarios(
    kwh_needed: float,
    charging_power_kw: float,
    current_time: datetime = None
) -> Dict[str, Any]:
    """
    Compares charging costs across 3 scenarios:
    1. Peak Window (worst case during evening rush)
    2. Immediate Start (starting right now)
    3. Super Off-Peak Window (best-case overnight 2 AM)
    """
    current_time = current_time or datetime.now()
    duration_mins = int((kwh_needed / max(1.0, charging_power_kw)) * 60)

    # 1. Peak window (6:00 PM today)
    peak_time = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
    peak_cost_res = calculate_session_cost(peak_time, duration_mins, kwh_needed)

    # 2. Immediate start
    immediate_cost_res = calculate_session_cost(current_time, duration_mins, kwh_needed)

    # 3. Super Off-Peak window (2:00 AM)
    next_offpeak = current_time.replace(hour=2, minute=0, second=0, microsecond=0)
    if next_offpeak <= current_time:
        next_offpeak += timedelta(days=1)
    offpeak_cost_res = calculate_session_cost(next_offpeak, duration_mins, kwh_needed)

    # Savings calculation
    peak_cost = peak_cost_res["total_cost"]
    offpeak_cost = offpeak_cost_res["total_cost"]
    max_savings_dollar = max(0.0, round(peak_cost - offpeak_cost, 2))
    max_savings_pct = round((max_savings_dollar / max(0.01, peak_cost)) * 100.0, 1)

    return {
        "kwh_requested": kwh_needed,
        "charging_power_kw": charging_power_kw,
        "duration_minutes": duration_mins,
        "duration_formatted": f"{duration_mins // 60}h {duration_mins % 60}m",
        "peak_window": {
            "label": "Peak Evening Window (6:00 PM)",
            "start": peak_time.strftime("%a %H:%M"),
            "cost": peak_cost_res["total_cost"],
            "avg_rate": peak_cost_res["avg_rate_per_kwh"]
        },
        "immediate_start": {
            "label": "Charge Immediately",
            "start": current_time.strftime("%a %H:%M"),
            "cost": immediate_cost_res["total_cost"],
            "avg_rate": immediate_cost_res["avg_rate_per_kwh"]
        },
        "super_off_peak": {
            "label": "Optimal Super Off-Peak (2:00 AM)",
            "start": next_offpeak.strftime("%a %H:%M"),
            "cost": offpeak_cost_res["total_cost"],
            "avg_rate": offpeak_cost_res["avg_rate_per_kwh"]
        },
        "max_potential_savings_usd": max_savings_dollar,
        "max_potential_savings_pct": max_savings_pct
    }


def get_tariff_schedule_summary() -> List[Dict[str, Any]]:
    """Returns formatted list of 24 hourly tariff rates for UI display."""
    result = []
    for h in range(24):
        rate, label, color = get_tariff_for_hour(h)
        result.append({
            "hour": h,
            "hour_label": f"{h:02d}:00",
            "rate_usd_per_kwh": rate,
            "tier_label": label,
            "tier_color": color
        })
    return result
