import { BrowserRouter, Link, NavLink, Route, Routes } from 'react-router-dom'
import DashboardPage from './pages/DashboardPage.jsx'
import HandsPage from './pages/HandsPage.jsx'
import ReplayerPage from './pages/ReplayerPage.jsx'
import LeaksPage from './pages/LeaksPage.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-950">
        <nav className="border-b border-slate-800 px-6 py-3 flex items-center gap-6">
          <Link to="/" className="text-sm font-semibold text-slate-100">
            Poker Hand Tracker
          </Link>
          <NavTab to="/">Dashboard</NavTab>
          <NavTab to="/hands">Hands</NavTab>
          <NavTab to="/leaks">Leaks</NavTab>
        </nav>
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/hands" element={<HandsPage />} />
          <Route path="/hands/:handId" element={<ReplayerPage />} />
          <Route path="/leaks" element={<LeaksPage />} />
        </Routes>
      </div>
    </BrowserRouter>
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
