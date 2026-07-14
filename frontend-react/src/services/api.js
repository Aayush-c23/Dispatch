const API_BASE_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

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
