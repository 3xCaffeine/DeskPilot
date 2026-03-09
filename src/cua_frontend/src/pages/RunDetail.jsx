import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { apiGet, apiPost } from '../api/client'
import StepTimeline from '../components/StepTimeline/StepTimeline'
import ScreenshotViewer from '../components/ScreenshotViewer/ScreenshotViewer'
import './RunDetail.css'

const STATUS_BADGE = {
  completed: 'badge-success',
  failed:    'badge-error',
  cancelled: 'badge-warning',
  running:   'badge-running',
  queued:    'badge-muted',
}

export default function RunDetail() {
  const { runId } = useParams()
  const navigate = useNavigate()
  const [run, setRun] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedStep, setSelectedStep] = useState(null)
  const [rerunning, setRerunning] = useState(false)

  useEffect(() => {
    apiGet(`/tasks/${runId}`)
      .then(data => {
        setRun(data)
        const last = data.steps?.filter(s => s.screenshot_available).at(-1)
        if (last) setSelectedStep(last.step)
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [runId])

  async function handleRerun() {
    setRerunning(true)
    try {
      const data = await apiPost('/tasks', { goal: run.goal, model: run.model, max_steps: run.steps?.length + 5 })
      navigate('/', { state: { taskId: data.task_id, goal: run.goal } })
    } catch (e) {
      console.error(e)
      setRerunning(false)
    }
  }

  if (loading) return <div className="run-detail-page"><p className="text-muted">Loading…</p></div>
  if (error)   return <div className="run-detail-page"><p style={{ color: 'var(--red)' }}>Error: {error}</p></div>
  if (!run)    return null

  return (
    <div className="run-detail-page">
      <div className="run-detail-topbar surface-card">
        <div className="run-detail-topbar-left">
          <Link to="/history" className="back-link">← History</Link>
          <span className="run-detail-separator">/</span>
          <p className="run-detail-goal">{run.goal}</p>
        </div>
        <div className="run-detail-topbar-right">
          <span className={`badge ${STATUS_BADGE[run.status] ?? 'badge-muted'}`}>{run.status}</span>
          <span className="run-detail-steps">{run.steps_taken ?? run.steps?.length ?? 0} steps</span>
          <button
            className="btn btn-secondary"
            onClick={handleRerun}
            disabled={rerunning}
          >
            {rerunning ? 'Starting…' : '↺ Re-run'}
          </button>
        </div>
      </div>

      {run.final_answer && (
        <div className="banner banner-success">{run.final_answer}</div>
      )}
      {run.error && (
        <div className="banner banner-error">{run.error}</div>
      )}

      <div className="run-detail-panels">
        <div className="run-detail-timeline">
          <StepTimeline
            steps={run.steps ?? []}
            selectedStep={selectedStep}
            onSelectStep={setSelectedStep}
          />
        </div>
        <div className="run-detail-screenshot">
          <ScreenshotViewer taskId={runId} stepNum={selectedStep} />
        </div>
      </div>
    </div>
  )
}

