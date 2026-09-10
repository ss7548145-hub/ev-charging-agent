"""
Schedule Recommendation API Router
Receives charging requests and returns multi-objective optimized start windows,
cost savings analysis, and LLM-powered natural language reasoning.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

from backend.analysis.schedule_optimizer import optimize_charging_schedule
from backend.agent.groq_agent import generate_recommendation_summary

router = APIRouter(prefix="/api", tags=["Optimization & Recommendations"])


class ChargingRequest(BaseModel):
    station_id: str = Field(..., description="Target charging station ID (e.g., 'ST-01')")
    kwh_needed: float = Field(..., gt=0, le=200, description="Desired energy in kWh (e.g., 45.0)")
    deadline: float = Field(..., gt=0, le=48, description="Departure deadline in hours from now (e.g., 12.0)")
    power_kw: Optional[float] = Field(default=50.0, gt=0, le=350, description="Charger power rating in kW")


@router.post("/recommend")
def get_charging_recommendation(request: ChargingRequest):
    """
    Optimizes the EV charging schedule to minimize costs and grid strain,
    and enriches the result with Groq LLM natural language insights.
    """
    try:
        # 1. Deterministic Multi-Objective Optimization
        opt_result = optimize_charging_schedule(
            station_id=request.station_id,
            kwh_needed=request.kwh_needed,
            deadline_hours=request.deadline,
            charging_power_kw=request.power_kw or 50.0
        )

        # 2. LLM Reasoning Layer
        llm_insights = generate_recommendation_summary(opt_result)

        return {
            "status": "success",
            "optimization": opt_result,
            "llm_reasoning": llm_insights
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Optimization failed: {str(e)}")
