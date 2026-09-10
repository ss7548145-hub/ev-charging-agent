const API_BASE = 'http://127.0.0.1:8000';

export async function fetchStations() {
  const res = await fetch(`${API_BASE}/api/stations`);
  if (!res.ok) throw new Error('Failed to fetch stations');
  return res.json();
}

export async function fetchStationAnalysis(stationId) {
  const res = await fetch(`${API_BASE}/api/analysis/${stationId}`);
  if (!res.ok) throw new Error('Failed to fetch station analysis');
  return res.json();
}

export async function fetchStationPrediction(stationId, horizonHours = 48) {
  const res = await fetch(`${API_BASE}/api/predict/${stationId}?horizon_hours=${horizonHours}`);
  if (!res.ok) throw new Error('Failed to fetch prediction');
  return res.json();
}

export async function requestScheduleRecommendation(payload) {
  const res = await fetch(`${API_BASE}/api/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error('Failed to generate recommendation');
  return res.json();
}

export async function sendChatMessage(message, stationId, history = []) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, station_id: stationId, conversation_history: history })
  });
  if (!res.ok) throw new Error('Failed to send chat message');
  return res.json();
}
