import { createContext, useCallback, useContext, useEffect, useState } from 'react'

const AuthContext = createContext(null)
const STORAGE_KEY = 'poker_hud_token'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8001'

async function postJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.detail || `${path} failed: ${res.status}`)
  }
  return data
}

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY))
  const [email, setEmail] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!token) {
      setLoading(false)
      return
    }
    fetch(`${API_BASE}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then((res) => (res.ok ? res.json() : Promise.reject()))
      .then((data) => setEmail(data.email))
      .catch(() => {
        localStorage.removeItem(STORAGE_KEY)
        setToken(null)
      })
      .finally(() => setLoading(false))
  }, [token])

  const login = useCallback(async (emailInput, password) => {
    const data = await postJson('/api/auth/login', { email: emailInput, password })
    localStorage.setItem(STORAGE_KEY, data.token)
    setToken(data.token)
    setEmail(data.email)
  }, [])

  const signup = useCallback(async (emailInput, password) => {
    const data = await postJson('/api/auth/signup', { email: emailInput, password })
    localStorage.setItem(STORAGE_KEY, data.token)
    setToken(data.token)
    setEmail(data.email)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setToken(null)
    setEmail(null)
  }, [])

  return (
    <AuthContext.Provider value={{ token, email, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}

export function getToken() {
  return localStorage.getItem(STORAGE_KEY)
}
