const API_BASE_URL = import.meta.env.VITE_API_URL ?? `${window.location.protocol}//${window.location.hostname}:8000`;

export async function createPlan(objective) {
  const response = await fetch(`${API_BASE_URL}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ objective }),
  });

  if (!response.ok) {
    throw new Error(`Planning request failed (${response.status}).`);
  }

  return response.json();
}

export async function triggerDisruption() {
  const response = await fetch(`${API_BASE_URL}/events/bridge-collapse`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Disruption trigger failed (${response.status}).`);
  }

  return response.json();
}

export async function askOperationalQuery(question) {
  const response = await fetch(`${API_BASE_URL}/query`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`Operational query failed (${response.status}).`);
  }

  return response.json();
}

export async function triggerFlood() {
  const response = await fetch(`${API_BASE_URL}/events/flood-surge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Flood surge trigger failed (${response.status}).`);
  }

  return response.json();
}

export async function fetchLiveContext() {
  const response = await fetch(`${API_BASE_URL}/live-context`);

  if (!response.ok) {
    throw new Error(`Failed to fetch live context (${response.status}).`);
  }

  return response.json();
}

export async function startTransit() {
  const response = await fetch(`${API_BASE_URL}/transit/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Failed to start transit (${response.status}).`);
  }

  return response.json();
}

export async function selectRoute(convoyId, label) {
  const response = await fetch(`${API_BASE_URL}/routes/select`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ convoy_id: convoyId, label }),
  });

  if (!response.ok) {
    throw new Error(`Failed to select route (${response.status}).`);
  }

  return response.json();
}
