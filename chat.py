"""
Chat Assistant API Router
Handles conversational Q&A about station congestion, pricing strategies, and charging patterns.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

from backend.agent.groq_agent import chat_with_agent
from backend.analysis.pattern_analysis import analyze_station_patterns

router = APIRouter(prefix="/api", tags=["Conversational Agent"])


class ChatMessageRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's question or command")
    station_id: Optional[str] = Field(default="ST-01", description="Current station ID context")
    conversation_history: Optional[List[Dict[str, str]]] = Field(default=[], description="Past conversation history")


@router.post("/chat")
def handle_chat_message(request: ChatMessageRequest):
    """
    Processes a natural language query with live station telemetry injected as grounding context.
    """
    try:
        # Grounding Context: Retrieve live station pattern data if station_id is provided
        context_json = {}
        if request.station_id:
            try:
                analysis = analyze_station_patterns(request.station_id)
                context_json = {
                    "station_id": analysis["station_id"],
                    "station_name": analysis["station_name"],
                    "station_type": analysis["station_type"],
                    "total_ports": analysis["total_ports"],
                    "overall_utilization_pct": analysis["metrics"]["overall_utilization_pct"],
                    "peak_hours": analysis["peak_hours"],
                    "off_peak_hours": analysis["off_peak_hours"],
                    "avg_power_kw": analysis["metrics"]["avg_power_kw"]
                }
            except Exception as e:
                print(f"[CHAT ROUTER] Could not fetch context for {request.station_id}: {e}")

        # Send to agent reasoning layer
        agent_response = chat_with_agent(
            user_message=request.message,
            station_id=request.station_id,
            context_json=context_json,
            conversation_history=request.conversation_history
        )

        return {
            "status": "success",
            "reply": agent_response["reply"],
            "provider": agent_response["provider"],
            "grounding_context": context_json
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing error: {str(e)}")
