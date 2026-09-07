const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

function toQueryString(filters) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters || {})) {
    if (value) params.set(key, value)
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

async function getJson(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`)
  }
  return res.json()
}

export function fetchHeroStats(filters) {
  return getJson(`/api/hero/stats${toQueryString(filters)}`)
}

export function fetchHeroGraph(filters) {
  return getJson(`/api/hero/graph${toQueryString(filters)}`)
}

export function fetchFilterOptions() {
  return getJson('/api/filters/options')
}

export function fetchHands(filters) {
  return getJson(`/api/hands${toQueryString(filters)}`)
}

export function fetchHandReplay(handId) {
  return getJson(`/api/hands/${handId}/replay`)
}

export function fetchLeaks(filters) {
  return getJson(`/api/leaks${toQueryString(filters)}`)
}
