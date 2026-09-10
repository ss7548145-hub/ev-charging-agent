"""
EV Charging Optimization Agent - FastAPI Main Entrypoint
Full-Stack Agent for Electric Vehicle Charging Optimization, Demand Prediction & TOU Cost Minimization.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from dotenv import load_dotenv

from backend.routers import analytics, predict, recommend, chat
from backend.agent.groq_agent import get_groq_client, DEFAULT_GROQ_MODEL

# Load .env variables
load_dotenv()

app = FastAPI(
    title="VoltIQ - EV Charging Optimization Agent API",
    description="Intelligent AI Agent for EV Charging Pattern Analysis, Demand Forecasting, Schedule Optimization & TOU Cost Reduction.",
    version="1.0.0"
)

# Enable CORS for local development and web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(analytics.router)
app.include_router(predict.router)
app.include_router(recommend.router)
app.include_router(chat.router)


@app.get("/api/health", tags=["System"])
def health_check():
    """
    Health check endpoint reporting API status, dataset availability, and Groq LLM connectivity.
    """
    groq_client = get_groq_client()
    groq_status = "Connected" if groq_client else "Fallback Mode (Set GROQ_API_KEY for live Groq API)"

    data_path = os.path.join(os.path.dirname(__file__), "data", "sample_charging_data.csv")
    data_exists = os.path.exists(data_path)

    return {
        "status": "healthy",
        "system": "VoltIQ EV Charging Agent",
        "groq_status": groq_status,
        "model": DEFAULT_GROQ_MODEL if groq_client else "Deterministic Smart Engine (Groq Fallback)",
        "dataset_loaded": data_exists
    }


# Frontend Static Files Serving
frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/", include_in_schema=False)
    def serve_frontend_root():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": "Frontend index.html not found, please check frontend/ directory."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
