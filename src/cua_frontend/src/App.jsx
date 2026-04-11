import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import Sidebar from './components/Layout/Sidebar'
import Header from './components/Layout/Header'
import { useConfig } from './hooks/useConfig'
import './App.css'

export default function App() {
  const config = useConfig()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  if (config.error) {
    return (
      <div className="api-error-state">
        <div className="api-error-card surface-card animate-slide-up">
          <h2>Backend Unreachable</h2>
          <p>
            Could not connect to the DeskPilot API. Make sure Docker/backend is running,
            then retry.
          </p>
          <button className="btn btn-primary" onClick={config.reload}>Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className={`app-shell${mobileMenuOpen ? ' menu-open' : ''}`}>
      <Sidebar mobileOpen={mobileMenuOpen} onNavigate={() => setMobileMenuOpen(false)} />
      <div className="app-main">
        <Header onMenuToggle={() => setMobileMenuOpen(v => !v)} />
        <main className="app-content">
          <Outlet context={config} />
        </main>
      </div>
      {mobileMenuOpen && <button className="sidebar-overlay" onClick={() => setMobileMenuOpen(false)} aria-label="Close navigation" />}
    </div>
  )
}
