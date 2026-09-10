"""
Groq LLM Reasoning Layer & Conversational Agent
Provides intelligent natural-language summaries for optimization results and
interactive free-form Q&A powered by Groq (llama-3.3-70b-versatile).
Features robust fallback mechanisms when no API key is set or upon rate limits.
"""

import os
import json
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
FALLBACK_GROQ_MODELS = ["llama-3.1-8b-instant", "llama3-70b-8192", "mixtral-8x7b-32768"]


def get_groq_client():
    """Initializes and returns the Groq client if API key is present."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key or api_key == "your_groq_api_key_here":
        return None

    try:
        from groq import Groq
        return Groq(api_key=api_key)
    except Exception as e:
        print(f"[GROQ AGENT] Failed to initialize Groq client: {e}")
        return None


def generate_recommendation_summary(
    optimization_result: Dict[str, Any],
    station_patterns: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generates a concise, high-impact natural-language summary and actionable rationale
    from structured charging schedule optimization output.
    """
    client = get_groq_client()
    
    rec_win = optimization_result.get("recommended_window", {})
    cost_info = optimization_result.get("cost_analysis", {})
    station_name = optimization_result.get("station_name", "Charging Station")
    kwh = optimization_result.get("kwh_requested", 40.0)
    savings_usd = cost_info.get("projected_savings_usd", 0.0)
    savings_pct = cost_info.get("projected_savings_pct", 0.0)
    start_fmt = rec_win.get("start_formatted", "TBD")
    end_fmt = rec_win.get("end_formatted", "TBD")
    congestion = rec_win.get("congestion_level", "Low")
    avg_rate = cost_info.get("avg_rate_usd_per_kwh", 0.18)

    # 1. Try Groq API if client is available
    if client:
        try:
            system_prompt = (
                "You are an expert Electric Vehicle Energy & Fleet Optimization Advisor. "
                "You analyze deterministic EV charging optimization data and output a concise, "
                "friendly, highly persuasive charging recommendation for the driver or fleet manager. "
                "Format your response as a JSON object with two keys:\n"
                "- 'summary': A 2-3 sentence clear and punchy recommendation with exact times and savings.\n"
                "- 'key_takeaways': An array of 3 bullet points highlighting cost, grid health, and departure readiness.\n"
                "Do NOT hallucinate numbers; use the exact figures provided."
            )

            user_prompt = f"""
Optimization Result Context:
- Station: {station_name}
- Energy Requested: {kwh} kWh
- Recommended Start Window: {start_fmt} to {end_fmt}
- Window Duration: {optimization_result.get('duration_formatted', 'N/A')}
- Projected Total Cost: ${cost_info.get('recommended_cost_usd', 0.0):.2f} (Effective rate: ${avg_rate:.2f}/kWh)
- Projected Savings vs Peak Window: ${savings_usd:.2f} ({savings_pct:.1f}% savings)
- Congestion Level: {congestion} (Score: {rec_win.get('congestion_score', 0):.1f}/100)
- Deadline: {optimization_result.get('deadline_formatted', 'N/A')}

Generate the JSON recommendation.
"""

            response = client.chat.completions.create(
                model=DEFAULT_GROQ_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=350,
                response_format={"type": "json_object"}
            )

            raw_text = response.choices[0].message.content
            parsed = json.loads(raw_text)
            return {
                "summary": parsed.get("summary", ""),
                "key_takeaways": parsed.get("key_takeaways", []),
                "provider": f"Groq ({DEFAULT_GROQ_MODEL})",
                "status": "success"
            }

        except Exception as e:
            print(f"[GROQ AGENT] Groq API call failed ({e}). Utilizing smart fallback engine.")

    # 2. Smart Deterministic Rule-Based Fallback Engine
    summary = (
        f"We recommend scheduling your {kwh:.0f} kWh session at {station_name} between "
        f"{start_fmt} and {end_fmt}. By charging during this low-demand window, you will save "
        f"~${savings_usd:.2f} ({savings_pct:.0f}% cheaper than peak evening rates) while ensuring "
        f"your vehicle is fully charged before your deadline."
    )

    takeaways = [
        f"💰 Financial Savings: Cut your electricity bill by {savings_pct:.1f}% (${savings_usd:.2f} saved vs peak charging).",
        f"⚡ Grid Impact: Minimal congestion ({congestion} load, avoiding grid strain).",
        f"⏱️ Schedule Assurance: Session completes comfortably by {end_fmt}, safely ahead of your departure."
    ]

    return {
        "summary": summary,
        "key_takeaways": takeaways,
        "provider": "Deterministic Smart Energy Engine (Groq Fallback)",
        "status": "fallback"
    }


def chat_with_agent(
    user_message: str,
    station_id: Optional[str] = None,
    context_json: Optional[Dict[str, Any]] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Handles conversational Q&A from the user, answering questions about station demand,
    peak hours, cost minimization, and charging policies.
    """
    client = get_groq_client()
    conversation_history = conversation_history or []

    # 1. If Groq is available, execute LLM completion with rich context
    if client:
        try:
            system_prompt = (
                "You are 'VoltIQ', an AI EV Charging & Grid Optimization Assistant. "
                "You help EV owners, station managers, and fleet operators understand charging patterns, "
                "minimize electricity costs via Time-of-Use tariffs, and avoid station congestion. "
                "Always be direct, helpful, and reference actual numerical insights when provided in context. "
                "Keep responses concise (2 to 4 short paragraphs or bullet points). "
                "Tariff knowledge: Super Off-Peak is 12 AM-6 AM ($0.10/kWh), Off-Peak is 6 AM-2 PM & 9 PM-12 AM ($0.18/kWh), "
                "Mid-Peak is 2 PM-5 PM ($0.28/kWh), On-Peak is 5 PM-9 PM ($0.42/kWh)."
            )

            context_str = json.dumps(context_json or {}, indent=2) if context_json else "No specific station context passed."
            
            messages = [{"role": "system", "content": f"{system_prompt}\n\nCurrent Operational Context:\n{context_str}"}]
            
            # Append past turns (limit to last 6 turns)
            for turn in conversation_history[-6:]:
                messages.append({"role": turn.get("role", "user"), "content": turn.get("content", "")})

            messages.append({"role": "user", "content": user_message})

            response = client.chat.completions.create(
                model=DEFAULT_GROQ_MODEL,
                messages=messages,
                temperature=0.5,
                max_tokens=500
            )

            reply = response.choices[0].message.content
            return {
                "reply": reply,
                "provider": f"Groq ({DEFAULT_GROQ_MODEL})",
                "status": "success"
            }

        except Exception as e:
            print(f"[GROQ AGENT] Chat completion failed ({e}). Using expert knowledge fallback.")

    # 2. Smart Knowledge Fallback Engine
    msg_lower = user_message.lower()
    
    # Extract station info if present
    station_name = context_json.get("station_name", "the selected station") if context_json else "the station"
    peak_hours = context_json.get("peak_hours", [17, 18, 19, 20]) if context_json else [17, 18, 19, 20]
    peak_str = ", ".join([f"{h:02d}:00" for h in peak_hours[:3]])

    if any(k in msg_lower for k in ["why", "full", "crowded", "congestion", "busy", "6pm", "peak"]):
        reply = (
            f"**Why is {station_name} busy during peak hours?**\n\n"
            f"1. **Commuter Surge**: Historical data shows peak occupancy spikes between **{peak_str}** due to drivers returning from commutes.\n"
            f"2. **Tariff Overlap**: On-Peak rates ($0.42/kWh) also coincide with these hours (5:00 PM – 9:00 PM).\n"
            f"3. **Recommendation**: Shift your charging to **after 9:00 PM** (Off-Peak at $0.18/kWh) or **overnight (12 AM - 6 AM at $0.10/kWh)** to avoid queues and cut charging costs by up to **76%**."
        )
    elif any(k in msg_lower for k in ["cheap", "cost", "tariff", "save", "rate", "price", "money"]):
        reply = (
            f"**Cheapest Times to Charge:**\n\n"
            f"• **Super Off-Peak (12:00 AM – 6:00 AM)**: **$0.10/kWh** (Lowest rate, minimal grid strain)\n"
            f"• **Standard Off-Peak (6:00 AM – 2:00 PM & 9:00 PM – 12:00 AM)**: **$0.18/kWh**\n"
            f"• **Mid-Peak (2:00 PM – 5:00 PM)**: **$0.28/kWh**\n"
            f"• **On-Peak (5:00 PM – 9:00 PM)**: **$0.42/kWh** (Most expensive)\n\n"
            f"💡 *Pro-Tip: Charging a 50 kWh battery at 2:00 AM costs **$5.00**, compared to **$21.00** at 6:00 PM — saving you **$16.00** per session!*"
        )
    elif any(k in msg_lower for k in ["weekend", "saturday", "sunday", "weekday"]):
        reply = (
            f"**Weekday vs. Weekend Patterns:**\n\n"
            f"• **Weekdays**: Experience sharp dual peaks — morning commute (8:00–10:00 AM) and evening rush (5:30–8:30 PM).\n"
            f"• **Weekends**: Demand is more evenly distributed across mid-afternoon (12:00 PM – 6:00 PM), especially near shopping and leisure hubs, with significantly lower morning congestion."
        )
    elif any(k in msg_lower for k in ["how does", "algorithm", "optimizer", "work", "model"]):
        reply = (
            f"**How the Optimization Engine Works:**\n\n"
            f"1. **Pattern Mining**: Analyzes 90 days of session telemetry to determine port utilization and congestion curves.\n"
            f"2. **Demand Forecasting**: Runs a Holt-Winters seasonal exponential smoothing model with 24h periodicity to project grid load.\n"
            f"3. **Constraint Optimizer**: Evaluates candidate charging windows before your deadline, minimizing a weighted cost function of TOU tariff rates + grid peak overlap."
        )
    else:
        reply = (
            f"Hello! I am your EV Charging Intelligence Assistant. Here is what I can do for you:\n\n"
            f"• **Find Optimal Windows**: Tell me your battery size and departure time to find the cheapest, lowest-congestion slot.\n"
            f"• **Analyze Congestion**: Ask why specific stations peak at certain hours.\n"
            f"• **Tariff Guidance**: Learn how dynamic TOU rates can save you up to 70%+ on charging expenses.\n\n"
            f"*Try asking: 'When is the best time to charge 45 kWh before 8 AM tomorrow?' or 'Why is Station 1 full at 6pm?'*"
        )

    return {
        "reply": reply,
        "provider": "Deterministic Smart Energy Engine (Groq Fallback)",
        "status": "fallback"
    }
