# ev-charging-agent
An autonomous, full-stack **Electric Vehicle Charging Optimization Agent** powered by FastAPI, Time-Series Modeling (Holt-Winters), Multi-Objective Constraint Optimization, and Groq LLM (`llama-3.3-70b-versatile`).

VoltIQ solves grid congestion, minimizes electricity costs using dynamic Time-of-Use (TOU) tariffs, and delivers explainable natural language recommendations for EV drivers and fleet operators.

---

## 🌟 Key Features

1. **Charging Pattern Analysis**:
   - Ingests 90 days of continuous charging session telemetry across multiple stations.
   - Computes per-station utilization %, peak congestion hours, weekday vs. weekend profiles.
   - Renders a full **7×24 Station Occupancy Heatmap** and hourly load curves.

2. **24–48h Energy Demand Forecasting**:
   - Time-series modeling using **Holt-Winters Exponential Smoothing** (with 24-period daily seasonality and trend).
   - Generates confidence intervals (95% upper/lower bounds) and peak load alerts.

3. **Multi-Objective Schedule Optimizer**:
   - Balances grid congestion, Time-of-Use electricity rates, and user departure deadlines.
   - Computes exact cost savings ($ and %) compared to worst-case peak charging windows.
   - Generates ranked alternatives (Cheapest, Fastest, and Greenest/Lowest Grid Strain).

4. **Groq LLM Reasoning & Conversational Agent**:
   - Powered by Groq's fast inference (`llama-3.3-70b-versatile`).
   - Translates deterministic mathematical optimization into actionable natural-language summaries.
   - Free-form interactive Q&A assistant with live station telemetry context injection.
   - **Zero-Failure Architecture**: Automatic fallback to smart deterministic reasoning if `GROQ_API_KEY` is not provided.

---

## 📂 Project Structure

```
ev-charging-agent/
├── backend/
│   ├── main.py                    # FastAPI application entrypoint & static mounting
│   ├── data/
│   │   ├── generate_data.py       # 90-day realistic session data generator
│   │   └── sample_charging_data.csv
│   ├── analysis/
│   │   ├── pattern_analysis.py    # Utilization, peak hours & 7x24 heatmaps
│   │   ├── demand_prediction.py   # Holt-Winters 24-48h demand forecasting
│   │   ├── cost_optimizer.py      # TOU tariff modeling and savings calculation
│   │   └── schedule_optimizer.py  # Multi-objective constraint scheduler
│   ├── agent/
│   │   └── groq_agent.py          # Groq LLM client with smart fallback
│   ├── routers/
│   │   ├── analytics.py           # GET /api/stations, GET /api/analysis/{station_id}
│   │   ├── predict.py             # GET /api/predict/{station_id}
│   │   ├── recommend.py           # POST /api/recommend
│   │   └── chat.py                # POST /api/chat
│   ├── requirements.txt
│   ├── .env.example
│   └── tests/
│       └── test_pipeline.py       # Automated unit & integration tests
├── frontend/
│   ├── index.html                 # Complete Dark-Mode Glassmorphism Dashboard
│   ├── css/
│   │   └── styles.css
│   ├── js/
│   │   ├── api.js                 # Frontend API client
│   │   └── app.js                 # Charts, heatmap & UI controller
│   ├── src/                       # Modular React + Vite component structure
│   │   ├── components/ (Dashboard, PeakHoursChart, RecommendationPanel, ChatWidget)
│   │   ├── App.jsx
│   │   └── api.js
│   └── package.json
└── README.md
``
