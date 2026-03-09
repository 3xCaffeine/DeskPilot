import { useNavigate } from 'react-router-dom'
import './RunCard.css'

function timeAgo(iso) {
  if (!iso) return ''
  const diff = Date.now() - new Date(iso).getTime()
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

const STATUS_BADGE = {
  completed: 'badge-success',
  failed:    'badge-error',
  cancelled: 'badge-warning',
  running:   'badge-running',
  queued:    'badge-muted',
}

export default function RunCard({ run }) {
  const navigate = useNavigate()

  return (
    <div className="run-card surface-card" onClick={() => navigate(`/history/${run.task_id}`)}>
      <div className="run-card-top">
        <span className={`badge ${STATUS_BADGE[run.status] ?? 'badge-muted'}`}>{run.status}</span>
        <span className="run-card-time">{timeAgo(run.created_at)}</span>
      </div>
      <p className="run-card-goal">{run.goal}</p>
      <div className="run-card-meta">
        <span>{run.steps_taken ?? 0} steps</span>
        <span className="run-card-model">{run.model?.split('/').at(-1)}</span>
      </div>
    </div>
  )
}
