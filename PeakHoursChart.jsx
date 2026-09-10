import React from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';
import { Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

export default function PeakHoursChart({ analysis }) {
  if (!analysis) return <div className="p-4 text-slate-400">Loading chart telemetry...</div>;

  const labels = analysis.hourly_profile.map((h) => h.hour_label);
  const weekdayKwh = analysis.weekday_vs_weekend.map((w) => w.weekday_kwh);
  const weekendKwh = analysis.weekday_vs_weekend.map((w) => w.weekend_kwh);
  const utilPcts = analysis.hourly_profile.map((h) => h.utilization_pct);

  const data = {
    labels,
    datasets: [
      {
        label: 'Weekday Energy (kWh)',
        data: weekdayKwh,
        backgroundColor: 'rgba(6, 182, 212, 0.7)',
        borderRadius: 4,
        yAxisID: 'y'
      },
      {
        label: 'Weekend Energy (kWh)',
        data: weekendKwh,
        backgroundColor: 'rgba(99, 102, 241, 0.7)',
        borderRadius: 4,
        yAxisID: 'y'
      }
    ]
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { labels: { color: '#94a3b8' } }
    },
    scales: {
      x: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } },
      y: { ticks: { color: '#64748b' }, grid: { color: 'rgba(255,255,255,0.05)' } }
    }
  };

  return (
    <div className="w-full h-72">
      <Bar data={data} options={options} />
    </div>
  );
}
