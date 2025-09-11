import { CONFIG } from '../config.js';

export async function loadTermById(id) {
  const res = await fetch(`${CONFIG.API_BASE}/api/term/${id}`);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return res.json();
}