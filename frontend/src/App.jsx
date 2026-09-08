import { BrowserRouter, Link, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage.jsx'
import HandsPage from './pages/HandsPage.jsx'
import ReplayerPage from './pages/ReplayerPage.jsx'
import LeaksPage from './pages/LeaksPage.jsx'
import LoginPage from './pages/LoginPage.jsx'
import SignupPage from './pages/SignupPage.jsx'
import ImportPage from './pages/ImportPage.jsx'
import { AuthProvider, useAuth } from './lib/auth.jsx'

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-950">
          <NavBar />
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/" element={<RequireAuth><DashboardPage /></RequireAuth>} />
            <Route path="/hands" element={<RequireAuth><HandsPage /></RequireAuth>} />
            <Route path="/hands/:handId" element={<RequireAuth><ReplayerPage /></RequireAuth>} />
            <Route path="/leaks" element={<RequireAuth><LeaksPage /></RequireAuth>} />
            <Route path="/import" element={<RequireAuth><ImportPage /></RequireAuth>} />
          </Routes>
        </div>
      </BrowserRouter>
    </AuthProvider>
  )
}

function RequireAuth({ children }) {
  const { token, loading } = useAuth()
  if (loading) {
    return <div className="max-w-6xl mx-auto mt-16 text-center text-slate-500">Loading…</div>
  }
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return children
}

function NavBar() {
  const { token, email, logout } = useAuth()

  return (
    <nav className="border-b border-slate-800 px-6 py-3 flex items-center gap-6">
      <Link to="/" className="text-sm font-semibold text-slate-100">
        Poker Hand Tracker
      </Link>
      {token && (
        <>
          <NavTab to="/">Dashboard</NavTab>
          <NavTab to="/hands">Hands</NavTab>
          <NavTab to="/leaks">Leaks</NavTab>
          <NavTab to="/import">Import</NavTab>
        </>
      )}
      <div className="ml-auto flex items-center gap-4">
        {token ? (
          <>
            <span className="text-sm text-slate-500">{email}</span>
            <button onClick={logout} className="text-sm text-slate-400 hover:text-slate-200">
              Log out
            </button>
          </>
        ) : (
          <>
            <NavTab to="/login">Log in</NavTab>
            <NavTab to="/signup">Sign up</NavTab>
          </>
        )}
      </div>
    </nav>
  )
}

function NavTab({ to, children }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      className={({ isActive }) =>
        `text-sm ${isActive ? 'text-cyan-400' : 'text-slate-400 hover:text-slate-200'}`
      }
    >
      {children}
    </NavLink>
  )
}
