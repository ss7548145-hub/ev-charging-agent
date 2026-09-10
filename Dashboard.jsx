import React, { useState, useEffect } from 'react';
import { fetchStations, fetchStationAnalysis, fetchStationPrediction } from '../api';
import PeakHoursChart from './PeakHoursChart';
import RecommendationPanel from './RecommendationPanel';
import ChatWidget from './ChatWidget';

export default function Dashboard() {
  const [stations, setStations] = useState([]);
  const [selectedStation, setSelectedStation] = useState('ST-01');
  const [analysis, setAnalysis] = useState(null);
  const [prediction, setPrediction] = useState(null);

  useEffect(() => {
    fetchStations().then((data) => {
      setStations(data);
      if (data.length > 0) setSelectedStation(data[0].station_id);
    });
  }, []);

  useEffect(() => {
    if (!selectedStation) return;
    Promise.all([
      fetchStationAnalysis(selectedStation),
      fetchStationPrediction(selectedStation, 48)
    ]).then(([ana, pred]) => {
      setAnalysis(ana);
      setPrediction(pred);
    });
  }, [selectedStation]);

  return (
    <div className="min-h-screen bg-[#090d16] text-white p-6 space-y-6">
      {/* Header */}
      <header className="flex justify-between items-center bg-slate-900/60 p-4 rounded-2xl border border-slate-800">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center text-xl font-bold shadow-lg shadow-cyan-500/20">
            ⚡
          </div>
          <div>
            <h1 className="text-xl font-bold">VoltIQ Agent</h1>
            <p className="text-xs text-slate-400">Autonomous EV Grid & Cost Optimizer</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={selectedStation}
            onChange={(e) => setSelectedStation(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-sm text-cyan-300 font-semibold focus:outline-none"
          >
            {stations.map((s) => (
              <option key={s.station_id} value={s.station_id}>
                {s.station_id}: {s.station_name}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* KPI Cards */}
      {analysis && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400">TOTAL ENERGY</span>
            <div className="text-2xl font-bold text-cyan-400 mt-1">
              {(analysis.metrics.total_energy_delivered_kwh / 1000).toFixed(1)}k kWh
            </div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400">UTILIZATION</span>
            <div className="text-2xl font-bold text-emerald-400 mt-1">
              {analysis.metrics.overall_utilization_pct}%
            </div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400">PEAK TRAFFIC</span>
            <div className="text-2xl font-bold text-amber-400 mt-1">
              {analysis.peak_hours.slice(0, 2).map((h) => `${h}:00`).join(' & ')}
            </div>
          </div>
          <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-2xl">
            <span className="text-xs text-slate-400">ACTIVE PORTS</span>
            <div className="text-2xl font-bold text-indigo-400 mt-1">
              {analysis.total_ports} Ports
            </div>
          </div>
        </div>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900/80 border border-slate-800 p-6 rounded-2xl">
            <h2 className="text-md font-bold mb-4">📊 Hourly Charging Demand & Utilization</h2>
            <PeakHoursChart analysis={analysis} />
          </div>
        </div>

        <div className="space-y-6">
          <RecommendationPanel stationId={selectedStation} />
          <ChatWidget stationId={selectedStation} />
        </div>
      </div>
    </div>
  );
}
