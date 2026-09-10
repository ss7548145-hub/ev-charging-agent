import React, { useState } from 'react';
import { requestScheduleRecommendation } from '../api';

export default function RecommendationPanel({ stationId, onRecommendationGenerated }) {
  const [kwh, setKwh] = useState(45);
  const [deadline, setDeadline] = useState(12);
  const [powerKw, setPowerKw] = useState(50);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleOptimize = async () => {
    setLoading(true);
    try {
      const data = await requestScheduleRecommendation({
        station_id: stationId,
        kwh_needed: parseFloat(kwh),
        deadline: parseFloat(deadline),
        power_kw: parseFloat(powerKw)
      });
      setResult(data);
      if (onRecommendationGenerated) onRecommendationGenerated(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/80 border border-slate-800 rounded-2xl p-6 shadow-xl backdrop-blur-md">
      <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
        <span>⚡</span> Optimize Charging Slot
      </h3>

      <div className="space-y-4">
        <div>
          <div className="flex justify-between text-sm text-slate-400 mb-1">
            <span>Energy Needed:</span>
            <span className="text-cyan-400 font-semibold">{kwh} kWh</span>
          </div>
          <input
            type="range"
            min="10"
            max="100"
            step="5"
            value={kwh}
            onChange={(e) => setKwh(e.target.value)}
            className="w-full accent-cyan-400"
          />
        </div>

        <div>
          <div className="flex justify-between text-sm text-slate-400 mb-1">
            <span>Departure Deadline:</span>
            <span className="text-cyan-400 font-semibold">In {deadline} Hours</span>
          </div>
          <input
            type="range"
            min="2"
            max="24"
            step="1"
            value={deadline}
            onChange={(e) => setDeadline(e.target.value)}
            className="w-full accent-cyan-400"
          />
        </div>

        <div>
          <label className="text-sm text-slate-400 block mb-2">Charger Power:</label>
          <div className="grid grid-cols-3 gap-2">
            {[22, 50, 150].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => setPowerKw(p)}
                className={`py-2 rounded-lg text-xs font-semibold border transition ${
                  powerKw === p
                    ? 'bg-cyan-500/20 border-cyan-400 text-cyan-300'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700'
                }`}
              >
                {p} kW
              </button>
            ))}
          </div>
        </div>

        <button
          onClick={handleOptimize}
          disabled={loading}
          className="w-full py-3 bg-gradient-to-r from-cyan-500 to-blue-600 text-white font-bold rounded-xl shadow-lg hover:shadow-cyan-500/30 transition disabled:opacity-50"
        >
          {loading ? 'Optimizing...' : '⚡ Optimize Schedule'}
        </button>
      </div>

      {result && (
        <div className="mt-6 p-4 rounded-xl bg-cyan-950/40 border border-cyan-500/30 space-y-3">
          <div className="flex justify-between items-center">
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-emerald-400 text-black">RECOMMENDED</span>
            <span className="text-xs text-slate-400">{result.optimization.duration_formatted}</span>
          </div>
          <div className="text-xl font-bold text-white">
            {result.optimization.recommended_window.start_formatted} – {result.optimization.recommended_window.end_formatted}
          </div>
          <div className="text-sm text-emerald-400 font-semibold">
            Save ${result.optimization.cost_analysis.projected_savings_usd.toFixed(2)} ({result.optimization.cost_analysis.projected_savings_pct.toFixed(0)}% cheaper)
          </div>
          <p className="text-xs text-slate-300 leading-relaxed bg-black/30 p-3 rounded-lg border border-slate-800">
            {result.llm_reasoning.summary}
          </p>
        </div>
      )}
    </div>
  );
}
