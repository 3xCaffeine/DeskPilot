import { useLocation } from 'react-router-dom'
import './Header.css'

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/history': 'History',
  '/settings': 'Settings',
}

const STATUS_CLASS = {
  idle:      'badge badge-muted',
  running:   'badge badge-running',
  completed: 'badge badge-success',
  failed:    'badge badge-error',
}

export default function Header({ agentStatus = 'idle', onMenuToggle }) {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? 'Run Detail'
  const cls = STATUS_CLASS[agentStatus] ?? 'badge badge-muted'

  return (
    <header className="header">
      <div className="header-left">
        <button className="header-menu-btn" onClick={onMenuToggle} aria-label="Toggle navigation menu">
          <span />
          <span />
          <span />
        </button>
        <h2 className="header-title">{title}</h2>
      </div>
      <span className={cls}>
        {agentStatus === 'running' && <span className="header-status-dot" />}
        {agentStatus.charAt(0).toUpperCase() + agentStatus.slice(1)}
      </span>
    </header>
  )
}
