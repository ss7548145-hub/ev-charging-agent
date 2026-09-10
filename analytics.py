"""
Analytics API Router
Provides endpoints for retrieving station metadata, historical charging patterns,
utilization statistics, 7x24 heatmaps, and tariff tables.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional

from backend.analysis.pattern_analysis import get_stations_summary, analyze_station_patterns
from backend.analysis.cost_optimizer import get_tariff_schedule_summary

router = APIRouter(prefix="/api", tags=["Analytics & Patterns"])


@router.get("/stations", response_model=List[Dict[str, Any]])
def list_stations():
    """
    Returns list of all EV charging stations with aggregate performance KPIs.
    """
    try:
        return get_stations_summary()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load station list: {str(e)}")


@router.get("/analysis/{station_id}")
def get_station_analysis(station_id: str):
    """
    Returns comprehensive charging pattern analysis for a specific station,
    including peak hours, hourly utilization, weekday/weekend comparison, and 7x24 heatmap.
    """
    try:
        return analyze_station_patterns(station_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis computation error: {str(e)}")


@router.get("/tariffs")
def get_tariffs():
    """
    Returns the dynamic Time-of-Use (TOU) electricity tariff schedule.
    """
    return get_tariff_schedule_summary()
