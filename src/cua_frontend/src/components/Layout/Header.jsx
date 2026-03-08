import { useLocation } from 'react-router-dom'
import './Header.css'

const PAGE_TITLES = {
  '/': 'Dashboard',
  '/history': 'History',
  '/settings': 'Settings',
}

const STATUS_CLASS = {
  idle:      'badge-muted',
  running:   'badge-running',
  completed: 'badge-success',
  failed:    'badge-error',
}

export default function Header({ agentStatus = 'idle', config = {} }) {
  const { pathname } = useLocation()
  const title = PAGE_TITLES[pathname] ?? 'Run Detail'
  const badgeClass = STATUS_CLASS[agentStatus] ?? 'badge-muted'
  const { model, setModel, availableModels = [] } = config

  return (
    <header className="header">
      <h2 className="header-title">{title}</h2>

      <div className="header-right">
        <span className={`badge ${badgeClass}`}>
          {agentStatus === 'running' && <span className="header-status-dot" />}
          {agentStatus.charAt(0).toUpperCase() + agentStatus.slice(1)}
        </span>

        {availableModels.length > 0 && (
          <div className="model-selector">
            <span className="model-selector-label">Model</span>
            <select
              className="model-select"
              value={model}
              onChange={e => setModel(e.target.value)}
            >
              {availableModels.map(m => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        )}
      </div>
    </header>
  )
}
