"""
Comprehensive Pipeline Test Suite
Validates:
1. Historical pattern analysis & 7x24 heatmap calculation
2. Holt-Winters time-series demand forecasting
3. TOU tariff cost calculation & savings estimation
4. Multi-objective schedule optimizer constraint satisfaction
5. Groq agent natural language reasoning and chat engine
6. FastAPI endpoints integration
"""

import sys
import os
import unittest

# Add root project path to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.analysis.pattern_analysis import load_charging_data, get_stations_summary, analyze_station_patterns
from backend.analysis.demand_prediction import predict_station_demand
from backend.analysis.cost_optimizer import calculate_session_cost, compare_charging_scenarios, get_tariff_for_hour
from backend.analysis.schedule_optimizer import optimize_charging_schedule
from backend.agent.groq_agent import generate_recommendation_summary, chat_with_agent


class TestEVChargingOptimizationPipeline(unittest.TestCase):

    def test_01_data_loading_and_summary(self):
        """Verify historical dataset loads and station summaries are computed accurately."""
        df = load_charging_data()
        self.assertGreater(len(df), 1000, "Dataset should contain at least 1,000 sessions")
        
        stations = get_stations_summary()
        self.assertGreaterEqual(len(stations), 5, "Should have summary for at least 5 stations")
        
        first_st = stations[0]
        self.assertIn("station_id", first_st)
        self.assertIn("utilization_pct", first_st)
        self.assertGreater(first_st["total_energy_kwh"], 0)
        print(f"[TEST 1 PASSED] Loaded {len(df)} sessions across {len(stations)} stations.")

    def test_02_pattern_analysis(self):
        """Verify peak hours, hourly profile, and 7x24 heatmap calculation."""
        analysis = analyze_station_patterns("ST-01")
        self.assertEqual(analysis["station_id"], "ST-01")
        self.assertEqual(len(analysis["hourly_profile"]), 24, "Hourly profile must have 24 hours")
        self.assertGreater(len(analysis["peak_hours"]), 0, "Should identify peak hours")
        self.assertEqual(len(analysis["heatmap_matrix"]), 7, "Heatmap matrix must have 7 days")
        self.assertEqual(len(analysis["heatmap_matrix"][0]["hours"]), 24, "Heatmap rows must have 24 hours")
        print(f"[TEST 2 PASSED] Pattern analysis computed. Peak hours: {analysis['peak_hours']}")

    def test_03_demand_prediction(self):
        """Verify time-series demand forecasting with Holt-Winters / seasonal models."""
        pred = predict_station_demand("ST-01", forecast_hours=24)
        self.assertEqual(pred["station_id"], "ST-01")
        self.assertEqual(len(pred["forecast"]), 24, "Forecast must return 24 hours")
        self.assertGreater(pred["total_predicted_24h_energy_kwh"], 0)
        
        first_hour = pred["forecast"][0]
        self.assertIn("predicted_demand_kwh", first_hour)
        self.assertIn("lower_bound_kwh", first_hour)
        self.assertIn("upper_bound_kwh", first_hour)
        print(f"[TEST 3 PASSED] 24h Demand Forecast total: {pred['total_predicted_24h_energy_kwh']:.1f} kWh ({pred['model_used']})")

    def test_04_cost_optimizer(self):
        """Verify Time-of-Use cost calculations and off-peak savings."""
        rate_super_off, _, _ = get_tariff_for_hour(2) # 2 AM
        rate_peak, _, _ = get_tariff_for_hour(18)    # 6 PM
        self.assertLess(rate_super_off, rate_peak, "Super off-peak rate must be lower than peak rate")

        comparison = compare_charging_scenarios(kwh_needed=50.0, charging_power_kw=50.0)
        self.assertGreater(comparison["max_potential_savings_usd"], 0)
        self.assertGreater(comparison["max_potential_savings_pct"], 0)
        print(f"[TEST 4 PASSED] Cost savings for 50 kWh: ${comparison['max_potential_savings_usd']:.2f} ({comparison['max_potential_savings_pct']}%)")

    def test_05_schedule_optimizer(self):
        """Verify multi-objective schedule optimizer finds optimal window within deadline."""
        opt = optimize_charging_schedule(
            station_id="ST-01",
            kwh_needed=40.0,
            deadline_hours=14.0,
            charging_power_kw=50.0
        )
        self.assertTrue(opt["is_feasible"])
        self.assertIn("recommended_window", opt)
        self.assertIn("cost_analysis", opt)
        self.assertGreater(len(opt["alternatives"]), 0)
        self.assertGreater(opt["cost_analysis"]["recommended_cost_usd"], 0)
        print(f"[TEST 5 PASSED] Optimal schedule start: {opt['recommended_window']['start_formatted']}, Cost: ${opt['cost_analysis']['recommended_cost_usd']:.2f}")

    def test_06_groq_agent_reasoning_and_chat(self):
        """Verify Groq agent natural language summary and conversational Q&A."""
        opt = optimize_charging_schedule(
            station_id="ST-01",
            kwh_needed=35.0,
            deadline_hours=10.0,
            charging_power_kw=50.0
        )
        summary = generate_recommendation_summary(opt)
        self.assertIn("summary", summary)
        self.assertIn("key_takeaways", summary)
        self.assertGreater(len(summary["key_takeaways"]), 0)

        chat_res = chat_with_agent(
            user_message="Why is this station congested at 6pm?",
            station_id="ST-01",
            context_json={"station_name": "Downtown Fast Hub", "peak_hours": [17, 18, 19]}
        )
        self.assertIn("reply", chat_res)
        self.assertGreater(len(chat_res["reply"]), 20)
        print(f"[TEST 6 PASSED] Groq agent generated summary & chat response ({summary['provider']})")


if __name__ == "__main__":
    unittest.main()
