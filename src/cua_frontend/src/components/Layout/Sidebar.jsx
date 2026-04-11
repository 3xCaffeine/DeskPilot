import { NavLink } from 'react-router-dom'
import './Sidebar.css'

const NAV = [
  { to: '/', icon: '🏠', label: 'Dashboard' },
  { to: '/history', icon: '📋', label: 'History' },
  { to: '/settings', icon: '⚙️', label: 'Settings' },
]

export default function Sidebar({ mobileOpen = false, onNavigate }) {
  return (
    <aside className={`sidebar${mobileOpen ? ' mobile-open' : ''}`}>
      <div className="sidebar-logo">
        <span className="sidebar-logo-icon">🤖</span>
        <span className="sidebar-logo-text">DeskPilot</span>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
            onClick={onNavigate}
          >
            <span className="sidebar-link-icon">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        <span className="sidebar-status-dot" />
        <span>Container</span>
      </div>
    </aside>
  )
}
