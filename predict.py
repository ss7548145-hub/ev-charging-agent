"""
Demand Prediction API Router
Provides endpoints to forecast charging demand (kWh and port concurrency) for next 24-48 hours.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any

from backend.analysis.demand_prediction import predict_station_demand

router = APIRouter(prefix="/api", tags=["Demand Forecasting"])


@router.get("/predict/{station_id}")
def get_station_prediction(
    station_id: str,
    horizon_hours: int = Query(default=48, ge=6, le=72, description="Forecast horizon in hours (6-72)")
):
    """
    Generates a 24-48 hour demand forecast using Holt-Winters Exponential Smoothing.
    """
    try:
        return predict_station_demand(station_id, forecast_hours=horizon_hours)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forecasting error: {str(e)}")
