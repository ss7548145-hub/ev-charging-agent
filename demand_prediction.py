"""
Energy Demand Prediction Module
Forecasts next 24-48 hours charging demand per station using time-series modeling
(Holt-Winters Exponential Smoothing with fallback seasonal moving average).
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from backend.analysis.pattern_analysis import load_charging_data, DEFAULT_DATA_PATH


def build_hourly_demand_series(station_id: str, filepath: str = DEFAULT_DATA_PATH) -> pd.Series:
    """
    Constructs a continuous regular hourly time-series of total energy delivered (kWh)
    for the specified station.
    """
    df = load_charging_data(filepath)
    if station_id and station_id.upper() != "ALL":
        station_df = df[df["station_id"] == station_id].copy()
    else:
        station_df = df.copy()

    if station_df.empty:
        raise ValueError(f"No data available for station {station_id}")

    # Aggregate by hour
    station_df["hourly_bin"] = station_df["start_time"].dt.floor("h")
    hourly_agg = station_df.groupby("hourly_bin")["energy_delivered_kwh"].sum()

    # Reindex to full continuous hourly range
    min_time = hourly_agg.index.min()
    max_time = hourly_agg.index.max()
    full_index = pd.date_range(start=min_time, end=max_time, freq="h")
    full_series = hourly_agg.reindex(full_index, fill_value=0.0)

    return full_series


def predict_station_demand(
    station_id: str,
    forecast_hours: int = 48,
    filepath: str = DEFAULT_DATA_PATH
) -> Dict[str, Any]:
    """
    Trains/fits a Holt-Winters seasonal model on historical hourly series
    and predicts next 24 to 48 hours of energy demand (kWh) and vehicle concurrency.
    """
    series = build_hourly_demand_series(station_id, filepath)
    
    # We need at least 48 observations to fit 24-period seasonality
    if len(series) < 48:
        raise ValueError("Insufficient data points for time-series forecasting.")

    # Fit Holt-Winters Exponential Smoothing with 24-hour daily seasonality
    model_fitted = False
    forecast_values = None

    try:
        # Use recent 30-45 days for responsive training
        recent_series = series.iloc[-min(len(series), 24 * 45):].copy()
        # Add tiny jitter to avoid exact zero issues with multiplicative/additive
        fit_series = recent_series + 0.001

        model = ExponentialSmoothing(
            fit_series,
            seasonal_periods=24,
            trend="add",
            seasonal="add",
            initialization_method="estimated"
        ).fit(optimized=True)

        raw_forecast = model.forecast(forecast_hours)
        forecast_values = np.clip(raw_forecast.values, a_min=0.0, a_max=None)
        model_name = "Holt-Winters Exponential Smoothing (Additive Trend + 24h Seasonality)"
        model_fitted = True
    except Exception as e:
        # Fallback to Seasonal Moving Average with Day-of-Week matching
        print(f"[PREDICTION] Holt-Winters fitting warning ({e}), using Seasonal Baseline Fallback.")
        model_name = "Seasonal Day-of-Week Profile Baseline"
        forecast_values = []
        last_dt = series.index[-1]
        for step in range(1, forecast_hours + 1):
            target_dt = last_dt + timedelta(hours=step)
            same_hour_day = series[(series.index.hour == target_dt.hour) & (series.index.dayofweek == target_dt.dayofweek)]
            if len(same_hour_day) > 0:
                val = float(same_hour_day.iloc[-4:].mean())
            else:
                val = float(series[series.index.hour == target_dt.hour].mean())
            forecast_values.append(max(0.0, val))
        forecast_values = np.array(forecast_values)

    # Historical context: last 24 hours of actual data
    last_24h_actual = []
    recent_actual = series.iloc[-24:]
    for dt, val in recent_actual.items():
        last_24h_actual.append({
            "timestamp": dt.strftime("%Y-%m-%d %H:%M"),
            "hour": int(dt.hour),
            "hour_label": dt.strftime("%a %H:%M"),
            "energy_kwh": round(float(val), 2)
        })

    # Forecast timeline
    last_timestamp = series.index[-1]
    forecast_series = []
    
    # Estimate standard error from residuals of recent observations for confidence interval
    residual_std = float(np.std(series.iloc[-168:] - series.iloc[-168:].mean())) * 0.25
    residual_std = max(residual_std, 2.5)

    for i in range(forecast_hours):
        dt = last_timestamp + timedelta(hours=i + 1)
        pred_kwh = round(float(forecast_values[i]), 2)
        lower_bound = max(0.0, round(pred_kwh - 1.645 * residual_std, 2))
        upper_bound = round(pred_kwh + 1.645 * residual_std, 2)

        # Expected port concurrency (assuming ~40 kW average power delivered per active vehicle)
        est_active_vehicles = max(0, round(pred_kwh / 40.0, 1))

        # Congestion classification
        if pred_kwh >= np.percentile(forecast_values, 75):
            congestion = "High Peak"
        elif pred_kwh >= np.percentile(forecast_values, 35):
            congestion = "Moderate"
        else:
            congestion = "Low Off-Peak"

        forecast_series.append({
            "timestamp": dt.strftime("%Y-%m-%d %H:%M"),
            "hour": int(dt.hour),
            "day_name": dt.strftime("%a"),
            "hour_label": dt.strftime("%a %H:%M"),
            "predicted_demand_kwh": pred_kwh,
            "lower_bound_kwh": lower_bound,
            "upper_bound_kwh": upper_bound,
            "estimated_active_vehicles": est_active_vehicles,
            "congestion_status": congestion
        })

    # Key statistics for prediction
    total_predicted_24h_kwh = sum(f["predicted_demand_kwh"] for f in forecast_series[:24])
    peak_forecast_item = max(forecast_series[:24], key=lambda x: x["predicted_demand_kwh"])

    return {
        "station_id": station_id,
        "model_used": model_name,
        "forecast_horizon_hours": forecast_hours,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_predicted_24h_energy_kwh": round(total_predicted_24h_kwh, 1),
        "peak_predicted_hour": {
            "hour_label": peak_forecast_item["hour_label"],
            "demand_kwh": peak_forecast_item["predicted_demand_kwh"],
            "congestion": peak_forecast_item["congestion_status"]
        },
        "last_24h_actual": last_24h_actual,
        "forecast": forecast_series
    }


if __name__ == "__main__":
    res = predict_station_demand("ST-01", forecast_hours=48)
    print("Model:", res["model_used"])
    print(f"24h Forecast Total: {res['total_predicted_24h_energy_kwh']} kWh")
    print(f"Peak Forecast Hour: {res['peak_predicted_hour']}")
