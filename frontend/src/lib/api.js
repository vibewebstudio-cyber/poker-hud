import { getToken } from './auth.jsx'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

function toQueryString(filters) {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(filters || {})) {
    if (value) params.set(key, value)
  }
  const qs = params.toString()
  return qs ? `?${qs}` : ''
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function getJson(path) {
  const res = await fetch(`${API_BASE}${path}`, { headers: authHeaders() })
  if (!res.ok) {
    throw new Error(`${path} failed: ${res.status}`)
  }
  return res.json()
}

async function postForm(path, formData) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: authHeaders(),
    body: formData,
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.detail || `${path} failed: ${res.status}`)
  }
  return data
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

export function uploadHandHistories(files) {
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  return postForm('/api/import', formData)
}
