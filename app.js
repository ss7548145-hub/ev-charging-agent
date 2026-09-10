/**
 * VoltIQ - Main Application Controller
 */

import {
  fetchStations,
  fetchStationAnalysis,
  fetchStationPrediction,
  fetchTariffs,
  requestScheduleRecommendation,
  sendChatMessage,
  checkHealth
} from './api.js';

// State
let currentStationId = 'ST-01';
let currentAnalysis = null;
let currentPrediction = null;
let stationsList = [];
let hourlyChartInstance = null;
let forecastChartInstance = null;
let chatHistory = [];
let selectedPowerKw = 50.0;

// DOM Elements
const stationSelect = document.getElementById('station-select');
const kpiEnergy = document.getElementById('kpi-energy');
const kpiUtilization = document.getElementById('kpi-utilization');
const kpiPeak = document.getElementById('kpi-peak');
const kpiPorts = document.getElementById('kpi-ports');
const heatmapContainer = document.getElementById('heatmap-grid');
const formKwhSlider = document.getElementById('slider-kwh');
const formKwhDisplay = document.getElementById('val-kwh');
const formDeadlineSlider = document.getElementById('slider-deadline');
const formDeadlineDisplay = document.getElementById('val-deadline');
const btnOptimize = document.getElementById('btn-optimize');
const optResultContainer = document.getElementById('opt-result-container');
const chatHistoryContainer = document.getElementById('chat-history');
const chatInput = document.getElementById('chat-input');
const btnSendChat = document.getElementById('btn-send-chat');
const healthStatusBadge = document.getElementById('health-status-badge');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  initEventListeners();
  await loadInitialData();
});

function initEventListeners() {
  // Station Selection Change
  stationSelect.addEventListener('change', async (e) => {
    currentStationId = e.target.value;
    await updateStationDashboard(currentStationId);
  });

  // Slider Displays
  formKwhSlider.addEventListener('input', (e) => {
    formKwhDisplay.textContent = `${e.target.value} kWh`;
  });

  formDeadlineSlider.addEventListener('input', (e) => {
    formDeadlineDisplay.textContent = `In ${e.target.value} Hours`;
  });

  // Power Selector Buttons
  document.querySelectorAll('.power-option-btn').forEach((btn) => {
    btn.addEventListener('click', (e) => {
      document.querySelectorAll('.power-option-btn').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      selectedPowerKw = parseFloat(btn.dataset.power);
    });
  });

  // Optimize Button
  btnOptimize.addEventListener('click', handleOptimizeSubmit);

  // Chat Actions
  btnSendChat.addEventListener('click', handleChatSubmit);
  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleChatSubmit();
    }
  });

  // Quick Chips
  document.querySelectorAll('.quick-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      chatInput.value = chip.textContent.replace(/^"|"$/g, '').trim();
      handleChatSubmit();
    });
  });
}

async function loadInitialData() {
  try {
    // Check Health
    const health = await checkHealth();
    if (healthStatusBadge) {
      healthStatusBadge.innerHTML = `<span class="status-dot"></span> ${health.groq_status || 'Online'}`;
    }

    // Load Stations
    stationsList = await fetchStations();
    stationSelect.innerHTML = '';
    stationsList.forEach((st) => {
      const opt = document.createElement('option');
      opt.value = st.station_id;
      opt.textContent = `${st.station_id}: ${st.station_name} (${st.total_ports} Ports)`;
      stationSelect.appendChild(opt);
    });

    if (stationsList.length > 0) {
      currentStationId = stationsList[0].station_id;
      stationSelect.value = currentStationId;
      await updateStationDashboard(currentStationId);
    }
  } catch (err) {
    console.error('Initialization error:', err);
  }
}

async function updateStationDashboard(stationId) {
  try {
    // 1. Fetch Analysis & Prediction in parallel
    const [analysis, prediction] = await Promise.all([
      fetchStationAnalysis(stationId),
      fetchStationPrediction(stationId, 48)
    ]);

    currentAnalysis = analysis;
    currentPrediction = prediction;

    // 2. Render KPIs
    kpiEnergy.textContent = `${(analysis.metrics.total_energy_delivered_kwh / 1000).toFixed(1)}k kWh`;
    kpiUtilization.textContent = `${analysis.metrics.overall_utilization_pct}%`;
    kpiPorts.textContent = `${analysis.total_ports} Active Ports`;
    kpiPeak.textContent = analysis.peak_hours.map((h) => `${h}:00`).slice(0, 2).join(' & ');

    // 3. Render 7x24 Heatmap
    renderHeatmap(analysis.heatmap_matrix);

    // 4. Render Hourly & Forecast Charts
    renderHourlyChart(analysis);
    renderForecastChart(prediction);

    // Trigger an initial optimization automatically
    handleOptimizeSubmit();

  } catch (err) {
    console.error('Failed to update dashboard:', err);
  }
}

function renderHeatmap(matrix) {
  if (!heatmapContainer) return;
  heatmapContainer.innerHTML = '';

  // Header row for hours
  const header = document.createElement('div');
  header.className = 'heatmap-header-hours';
  header.innerHTML = '<div></div>' + Array.from({ length: 24 }, (_, i) => `<div class="heatmap-hour-label">${i}</div>`).join('');
  heatmapContainer.appendChild(header);

  matrix.forEach((row) => {
    const rowEl = document.createElement('div');
    rowEl.className = 'heatmap-row';

    const dayLabel = document.createElement('div');
    dayLabel.className = 'heatmap-day-label';
    dayLabel.textContent = row.day_name.slice(0, 3);
    rowEl.appendChild(dayLabel);

    row.hours.forEach((cell) => {
      const cellEl = document.createElement('div');
      cellEl.className = 'heatmap-cell';
      const util = cell.utilization_pct;
      
      // Color scale: low (dark blue) -> mid (cyan/amber) -> high (rose/red)
      let color;
      if (util < 20) color = 'rgba(30, 41, 59, 0.6)';
      else if (util < 40) color = 'rgba(3, 105, 161, 0.7)';
      else if (util < 65) color = 'rgba(6, 182, 212, 0.85)';
      else if (util < 85) color = 'rgba(245, 158, 11, 0.9)';
      else color = 'rgba(244, 63, 94, 0.95)';

      cellEl.style.backgroundColor = color;
      cellEl.title = `${row.day_name} at ${cell.hour_label} - Utilization: ${util}%`;
      rowEl.appendChild(cellEl);
    });

    heatmapContainer.appendChild(rowEl);
  });
}

function renderHourlyChart(analysis) {
  const ctx = document.getElementById('hourly-chart');
  if (!ctx) return;

  const hours = analysis.hourly_profile.map((h) => h.hour_label);
  const weekdayKwh = analysis.weekday_vs_weekend.map((w) => w.weekday_kwh);
  const weekendKwh = analysis.weekday_vs_weekend.map((w) => w.weekend_kwh);
  const utilPcts = analysis.hourly_profile.map((h) => h.utilization_pct);

  if (hourlyChartInstance) {
    hourlyChartInstance.destroy();
  }

  hourlyChartInstance = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: hours,
      datasets: [
        {
          label: 'Weekday Avg Energy (kWh)',
          data: weekdayKwh,
          backgroundColor: 'rgba(6, 182, 212, 0.7)',
          borderRadius: 4,
          yAxisID: 'y'
        },
        {
          label: 'Weekend Avg Energy (kWh)',
          data: weekendKwh,
          backgroundColor: 'rgba(99, 102, 241, 0.7)',
          borderRadius: 4,
          yAxisID: 'y'
        },
        {
          label: 'Utilization %',
          data: utilPcts,
          type: 'line',
          borderColor: '#f59e0b',
          borderWidth: 2,
          pointRadius: 2,
          tension: 0.3,
          yAxisID: 'y1'
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 } }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#fff',
          bodyColor: '#cbd5e1',
          borderColor: 'rgba(255,255,255,0.1)',
          borderWidth: 1
        }
      },
      scales: {
        x: {
          ticks: { color: '#64748b', maxTicksLimit: 12 },
          grid: { color: 'rgba(255, 255, 255, 0.04)' }
        },
        y: {
          title: { display: true, text: 'Energy (kWh)', color: '#94a3b8' },
          ticks: { color: '#64748b' },
          grid: { color: 'rgba(255, 255, 255, 0.04)' }
        },
        y1: {
          position: 'right',
          title: { display: true, text: 'Utilization %', color: '#f59e0b' },
          min: 0,
          max: 100,
          ticks: { color: '#f59e0b' },
          grid: { display: false }
        }
      }
    }
  });
}

function renderForecastChart(prediction) {
  const ctx = document.getElementById('forecast-chart');
  if (!ctx) return;

  const labels = prediction.forecast.slice(0, 36).map((f) => f.hour_label);
  const predicted = prediction.forecast.slice(0, 36).map((f) => f.predicted_demand_kwh);
  const upper = prediction.forecast.slice(0, 36).map((f) => f.upper_bound_kwh);
  const lower = prediction.forecast.slice(0, 36).map((f) => f.lower_bound_kwh);

  if (forecastChartInstance) {
    forecastChartInstance.destroy();
  }

  forecastChartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Upper Confidence (95%)',
          data: upper,
          borderColor: 'transparent',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: '+1',
          pointRadius: 0
        },
        {
          label: 'Predicted Energy Load (kWh)',
          data: predicted,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.2)',
          borderWidth: 2.5,
          tension: 0.35,
          pointRadius: 3,
          pointBackgroundColor: '#10b981'
        },
        {
          label: 'Lower Confidence (95%)',
          data: lower,
          borderColor: 'transparent',
          backgroundColor: 'transparent',
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: '#94a3b8',
            font: { family: 'Outfit', size: 11 },
            filter: (item) => item.text.includes('Predicted')
          }
        },
        tooltip: {
          mode: 'index',
          intersect: false,
          backgroundColor: 'rgba(15, 23, 42, 0.9)',
          titleColor: '#fff',
          bodyColor: '#cbd5e1'
        }
      },
      scales: {
        x: {
          ticks: { color: '#64748b', maxTicksLimit: 10 },
          grid: { color: 'rgba(255, 255, 255, 0.04)' }
        },
        y: {
          title: { display: true, text: 'Forecast Demand (kWh)', color: '#94a3b8' },
          ticks: { color: '#64748b' },
          grid: { color: 'rgba(255, 255, 255, 0.04)' }
        }
      }
    }
  });
}

async function handleOptimizeSubmit() {
  const kwh = formKwhSlider.value;
  const deadline = formDeadlineSlider.value;

  btnOptimize.disabled = true;
  btnOptimize.innerHTML = '⚡ Optimizing Windows...';

  try {
    const res = await requestScheduleRecommendation(currentStationId, kwh, deadline, selectedPowerKw);
    renderOptimizationResult(res);
  } catch (err) {
    console.error('Optimization error:', err);
    optResultContainer.innerHTML = `<div class="opt-result-panel" style="border-color: var(--accent-rose);">❌ ${err.message}</div>`;
  } finally {
    btnOptimize.disabled = false;
    btnOptimize.innerHTML = '⚡ Optimize Charging Schedule';
  }
}

function renderOptimizationResult(data) {
  const opt = data.optimization;
  const llm = data.llm_reasoning;
  const win = opt.recommended_window;
  const cost = opt.cost_analysis;

  let alternativesHtml = opt.alternatives.map((alt) => `
    <div style="background: rgba(255,255,255,0.03); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 0.6rem 0.75rem; display: flex; justify-content: space-between; align-items: center;">
      <div>
        <div style="font-size: 0.75rem; font-weight: 600; color: var(--accent-cyan);">${alt.tag} <span style="font-size: 0.68rem; color: var(--text-muted); font-weight: 400;">(${alt.badge})</span></div>
        <div style="font-size: 0.85rem; font-weight: 600;">${alt.window.start_formatted}</div>
      </div>
      <div style="text-align: right;">
        <div style="font-size: 0.92rem; font-weight: 700; color: #fff;">$${alt.window.total_cost_usd.toFixed(2)}</div>
        <div style="font-size: 0.7rem; color: var(--text-muted);">${alt.window.congestion_level} Grid</div>
      </div>
    </div>
  `).join('');

  let takeawaysHtml = (llm.key_takeaways || []).map((t) => `<li>${t}</li>`).join('');

  optResultContainer.innerHTML = `
    <div class="opt-result-panel">
      <div class="opt-best-badge">
        <span class="tag-best">⭐ Recommended Window</span>
        <span style="font-size: 0.75rem; color: var(--text-muted);">Duration: ${opt.duration_formatted}</span>
      </div>

      <div class="opt-time-window">${win.start_formatted} – ${win.end_formatted}</div>

      <div class="opt-savings-banner">
        <div>
          <div style="font-size: 0.75rem; color: var(--text-secondary);">Projected Total Cost</div>
          <div style="font-size: 1.25rem; font-weight: 700; color: #fff;">$${cost.recommended_cost_usd.toFixed(2)} <span style="font-size: 0.75rem; color: var(--text-muted);">($${cost.avg_rate_usd_per_kwh.toFixed(2)}/kWh)</span></div>
        </div>
        <div style="text-align: right;">
          <div style="font-size: 0.75rem; color: var(--text-secondary);">Cost Reduction</div>
          <div class="savings-highlight">Save $${cost.projected_savings_usd.toFixed(2)} (${cost.projected_savings_pct.toFixed(0)}%)</div>
        </div>
      </div>

      <!-- LLM Reasoning Box -->
      <div class="llm-box">
        <div class="llm-badge">
          <span>🧠</span> AI Advisor Insights (${llm.provider})
        </div>
        <div class="llm-text">${llm.summary}</div>
        <ul class="llm-bullets">
          ${takeawaysHtml}
        </ul>
      </div>

      <!-- Trade-Off Alternatives -->
      <div>
        <div style="font-size: 0.8rem; font-weight: 600; color: var(--text-secondary); margin-bottom: 0.5rem;">Alternative Schedule Strategies:</div>
        <div style="display: flex; flex-direction: column; gap: 0.5rem;">
          ${alternativesHtml}
        </div>
      </div>
    </div>
  `;
}

async function handleChatSubmit() {
  const text = chatInput.value.trim();
  if (!text) return;

  chatInput.value = '';
  appendChatMessage('user', text);

  // Loading bubble
  const loadId = appendChatMessage('agent', 'Thinking with Groq reasoning engine...');

  try {
    const res = await sendChatMessage(text, currentStationId, chatHistory);
    updateChatMessage(loadId, res.reply);
    chatHistory.push({ role: 'user', content: text });
    chatHistory.push({ role: 'assistant', content: res.reply });
  } catch (err) {
    updateChatMessage(loadId, `Sorry, encountered an issue: ${err.message}`);
  }
}

function appendChatMessage(role, content) {
  const id = 'msg-' + Date.now() + Math.random().toString(36).substr(2, 4);
  const msgEl = document.createElement('div');
  msgEl.className = `chat-msg ${role}`;
  msgEl.id = id;

  const formattedContent = role === 'agent' 
    ? content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br/>')
    : content;

  msgEl.innerHTML = `<div class="msg-bubble">${formattedContent}</div>`;
  chatHistoryContainer.appendChild(msgEl);
  chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;
  return id;
}

function updateChatMessage(id, newContent) {
  const msgEl = document.getElementById(id);
  if (msgEl) {
    const bubble = msgEl.querySelector('.msg-bubble');
    if (bubble) {
      bubble.innerHTML = newContent
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n\n/g, '<br/><br/>')
        .replace(/\n/g, '<br/>');
    }
  }
  chatHistoryContainer.scrollTop = chatHistoryContainer.scrollHeight;
}
