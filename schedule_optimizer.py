"""
Charging Schedule Optimizer Module
Applies constraint-based multi-objective optimization to determine the best
charging window that minimizes electricity cost and grid congestion while
strictly satisfying the user's completion deadline and charger speed limits.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np

from backend.analysis.pattern_analysis import analyze_station_patterns, DEFAULT_DATA_PATH
from backend.analysis.demand_prediction import predict_station_demand
from backend.analysis.cost_optimizer import calculate_session_cost, get_tariff_for_hour


def optimize_charging_schedule(
    station_id: str,
    kwh_needed: float,
    deadline_hours: float,
    charging_power_kw: float = 50.0,
    current_time: Optional[datetime] = None,
    alpha_cost_weight: float = 0.55,
    beta_congestion_weight: float = 0.45,
    filepath: str = DEFAULT_DATA_PATH
) -> Dict[str, Any]:
    """
    Optimizes the EV charging start window based on user deadline, station load forecast,
    and Time-of-Use electricity tariffs.

    Parameters:
    - station_id: Target charging station ID (e.g., 'ST-01')
    - kwh_needed: Energy to be delivered in kWh (e.g., 40 kWh)
    - deadline_hours: Departure deadline in hours from now (e.g., 12.0 hours)
    - charging_power_kw: Charger power delivery in kW (e.g., 50 kW)
    - current_time: Current simulation timestamp (defaults to datetime.now())
    """
    if kwh_needed <= 0:
        raise ValueError("kwh_needed must be greater than 0")
    if deadline_hours <= 0:
        raise ValueError("deadline_hours must be greater than 0")
    if charging_power_kw <= 0:
        charging_power_kw = 50.0

    current_time = current_time or datetime.now().replace(second=0, microsecond=0)
    deadline_time = current_time + timedelta(hours=deadline_hours)

    # 1. Compute required duration
    duration_hours = kwh_needed / charging_power_kw
    duration_minutes = max(10, int(np.ceil(duration_hours * 60)))
    
    # Check if deadline is physically impossible
    available_minutes = int(deadline_hours * 60)
    if duration_minutes > available_minutes:
        is_feasible = False
        warning_msg = f"Requested {kwh_needed} kWh at {charging_power_kw} kW requires {duration_minutes // 60}h {duration_minutes % 60}m, but deadline is in {deadline_hours}h. Charging will finish after deadline."
    else:
        is_feasible = True
        warning_msg = None

    # 2. Fetch station patterns and 48h demand forecast
    try:
        patterns = analyze_station_patterns(station_id, filepath)
        forecast_res = predict_station_demand(station_id, forecast_hours=48, filepath=filepath)
        forecast_map = {f["hour_label"]: f["predicted_demand_kwh"] for f in forecast_res["forecast"]}
        forecast_list = forecast_res["forecast"]
    except Exception as e:
        print(f"[OPTIMIZER] Warning reading station pattern/forecast ({e}), using default profiles.")
        patterns = {"peak_hours": [8, 9, 17, 18, 19], "hourly_profile": []}
        forecast_list = []

    # 3. Generate candidate windows (30-minute intervals)
    candidate_windows = []
    # Maximum search horizon is up to min(deadline, 36 hours)
    max_search_hours = min(deadline_hours, 36.0)
    step_minutes = 30
    total_steps = int(max_search_hours * 60 // step_minutes)

    # If charging takes almost entire time, at least evaluate step 0
    if total_steps == 0:
        total_steps = 1

    for step in range(total_steps + 1):
        win_start = current_time + timedelta(minutes=step * step_minutes)
        win_end = win_start + timedelta(minutes=duration_minutes)

        # Check deadline breach
        deadline_breach_mins = max(0, int((win_end - deadline_time).total_seconds() / 60))
        if deadline_breach_mins > 0 and step > 0:
            # Skip candidates starting too late if earlier ones fit
            continue

        # Calculate exact TOU electricity cost
        cost_res = calculate_session_cost(win_start, duration_minutes, kwh_needed)
        total_cost = cost_res["total_cost"]

        # Calculate grid congestion score (0 to 100)
        # Slices across duration and assesses peak overlap
        congestion_points = []
        curr = win_start
        while curr < win_end:
            h = curr.hour
            is_peak_hour = h in patterns.get("peak_hours", [17, 18, 19])
            rate_kwh, tier_label, _ = get_tariff_for_hour(h)
            
            # Base congestion proxy
            if is_peak_hour:
                score = 85.0
            elif tier_label == "Mid-Peak":
                score = 55.0
            elif tier_label == "Off-Peak":
                score = 30.0
            else: # Super off peak
                score = 10.0

            congestion_points.append(score)
            curr += timedelta(minutes=15)

        avg_congestion = float(np.mean(congestion_points)) if congestion_points else 30.0

        # Buffer bonus (prefer finishing comfortably before deadline)
        slack_minutes = max(0, int((deadline_time - win_end).total_seconds() / 60))
        urgency_penalty = 0.0 if slack_minutes >= 30 else (30 - slack_minutes) * 0.5

        # Normalization for multi-objective scoring
        # Benchmark max cost is peak rate * kwh
        max_possible_cost = kwh_needed * 0.42
        cost_score_normalized = (total_cost / max(0.01, max_possible_cost)) * 100.0

        # Weighted objective score (Lower is better)
        composite_score = (
            alpha_cost_weight * cost_score_normalized +
            beta_congestion_weight * avg_congestion +
            urgency_penalty * 0.2
        )

        candidate_windows.append({
            "window_id": f"WIN-{step:02d}",
            "start_time": win_start.strftime("%Y-%m-%d %H:%M"),
            "end_time": win_end.strftime("%Y-%m-%d %H:%M"),
            "start_formatted": win_start.strftime("%a %I:%M %p"),
            "end_formatted": win_end.strftime("%a %I:%M %p"),
            "duration_formatted": f"{duration_minutes // 60}h {duration_minutes % 60}m",
            "total_cost_usd": round(total_cost, 2),
            "avg_rate_usd_per_kwh": round(cost_res["avg_rate_per_kwh"], 3),
            "congestion_score": round(avg_congestion, 1),
            "congestion_level": "Low" if avg_congestion < 35 else ("Moderate" if avg_congestion < 65 else "High"),
            "composite_score": round(composite_score, 2),
            "slack_minutes": slack_minutes,
            "tier_breakdown": cost_res["tier_breakdown"]
        })

    if not candidate_windows:
        # Fallback to immediate window
        win_start = current_time
        win_end = win_start + timedelta(minutes=duration_minutes)
        cost_res = calculate_session_cost(win_start, duration_minutes, kwh_needed)
        candidate_windows.append({
            "window_id": "WIN-00",
            "start_time": win_start.strftime("%Y-%m-%d %H:%M"),
            "end_time": win_end.strftime("%Y-%m-%d %H:%M"),
            "start_formatted": win_start.strftime("%a %I:%M %p"),
            "end_formatted": win_end.strftime("%a %I:%M %p"),
            "duration_formatted": f"{duration_minutes // 60}h {duration_minutes % 60}m",
            "total_cost_usd": round(cost_res["total_cost"], 2),
            "avg_rate_usd_per_kwh": round(cost_res["avg_rate_per_kwh"], 3),
            "congestion_score": 40.0,
            "congestion_level": "Moderate",
            "composite_score": 50.0,
            "slack_minutes": 0,
            "tier_breakdown": cost_res["tier_breakdown"]
        })

    # 4. Rank candidates
    ranked_candidates = sorted(candidate_windows, key=lambda x: x["composite_score"])
    best_window = ranked_candidates[0]

    # Benchmark: Worst-case Peak Time Cost
    peak_benchmark_start = current_time.replace(hour=18, minute=0, second=0, microsecond=0)
    peak_cost_res = calculate_session_cost(peak_benchmark_start, duration_minutes, kwh_needed)
    peak_cost_usd = peak_cost_res["total_cost"]

    # Immediate Start Cost
    immediate_cost_res = calculate_session_cost(current_time, duration_minutes, kwh_needed)
    immediate_cost_usd = immediate_cost_res["total_cost"]

    # Savings relative to peak
    cost_savings_usd = max(0.0, round(peak_cost_usd - best_window["total_cost_usd"], 2))
    cost_savings_pct = round((cost_savings_usd / max(0.01, peak_cost_usd)) * 100.0, 1)

    # Alternative Options:
    # Option A: Fastest / Immediate Start
    fastest_option = candidate_windows[0] # step 0
    # Option B: Lowest Electricity Cost
    cheapest_option = min(candidate_windows, key=lambda x: x["total_cost_usd"])
    # Option C: Lowest Congestion / Greenest
    greenest_option = min(candidate_windows, key=lambda x: x["congestion_score"])

    alternatives = [
        {
            "tag": "Cheapest Slot",
            "badge": "Maximum Savings",
            "window": cheapest_option
        },
        {
            "tag": "Fastest Start",
            "badge": "Immediate Departure",
            "window": fastest_option
        },
        {
            "tag": "Greenest / Low Grid Strain",
            "badge": "Eco-Friendly",
            "window": greenest_option
        }
    ]

    return {
        "station_id": station_id,
        "station_name": patterns.get("station_name", f"Station {station_id}"),
        "kwh_requested": kwh_needed,
        "charging_power_kw": charging_power_kw,
        "duration_minutes": duration_minutes,
        "duration_formatted": f"{duration_minutes // 60}h {duration_minutes % 60}m",
        "deadline_hours": deadline_hours,
        "deadline_formatted": deadline_time.strftime("%a %I:%M %p"),
        "is_feasible": is_feasible,
        "warning": warning_msg,
        "recommended_window": best_window,
        "cost_analysis": {
            "recommended_cost_usd": best_window["total_cost_usd"],
            "peak_window_cost_usd": peak_cost_usd,
            "immediate_start_cost_usd": immediate_cost_usd,
            "projected_savings_usd": cost_savings_usd,
            "projected_savings_pct": cost_savings_pct,
            "avg_rate_usd_per_kwh": best_window["avg_rate_usd_per_kwh"]
        },
        "alternatives": alternatives,
        "total_candidate_windows_evaluated": len(candidate_windows),
        "candidates_overview": ranked_candidates[:8]
    }


if __name__ == "__main__":
    opt = optimize_charging_schedule(
        station_id="ST-01",
        kwh_needed=45.0,
        deadline_hours=12.0,
        charging_power_kw=50.0
    )
    print("Recommended Start:", opt["recommended_window"]["start_formatted"])
    print("Savings:", f"${opt['cost_analysis']['projected_savings_usd']} ({opt['cost_analysis']['projected_savings_pct']}%)")
