import { useState, useRef, useEffect } from 'react'
import { useOutletContext } from 'react-router-dom'
import TaskInput from '../components/TaskInput/TaskInput'
import StepTimeline from '../components/StepTimeline/StepTimeline'
import ScreenshotViewer from '../components/ScreenshotViewer/ScreenshotViewer'
import VncPreview from '../components/VncPreview/VncPreview'
import { useWebSocket } from '../hooks/useWebSocket'
import './Dashboard.css'

const STATUS_BADGE = {
  connecting: 'badge-muted',
  reconnecting: 'badge-warning',
  running:    'badge-running',
  completed:  'badge-success',
  failed:     'badge-error',
  cancelled:  'badge-warning',
  error:      'badge-error',
}

function ExecutionView({ task, onNewTask }) {
  const { steps, status, finalAnswer, logs, cancel } = useWebSocket(task.taskId)
  const [pinnedStep, setPinnedStep] = useState(null)
  const [viewMode, setViewMode] = useState('screenshot')
  const [showLogs, setShowLogs] = useState(false)
  const logEndRef = useRef(null)

  useEffect(() => {
    if (showLogs) logEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs, showLogs])

  const latestWithShot = steps.filter(s => s.screenshot_available).at(-1)?.step ?? null
  const viewStep = pinnedStep ?? latestWithShot
  const isTerminal = ['completed', 'failed', 'cancelled', 'error'].includes(status)

  return (
    <div className="execution-view">
      <div className="execution-topbar surface-card">
        <div>
          <p className="execution-goal-label">Running task</p>
          <p className="execution-goal">{task.goal}</p>
        </div>
        <div className="execution-topbar-right">
          <span className={`badge ${STATUS_BADGE[status] ?? 'badge-muted'}`}>{status}</span>
          {!isTerminal
            ? <button className="btn btn-danger" onClick={cancel}>Cancel</button>
            : <button className="btn btn-secondary" onClick={onNewTask}>New Task</button>
          }
        </div>
      </div>

      {status === 'completed' && (
        <div className="banner banner-success animate-slide-up">
          ✓ Task complete{finalAnswer ? ` — ${finalAnswer}` : ''}
        </div>
      )}
      {status === 'failed' && (
        <div className="banner banner-error animate-slide-up">
          ✗ Task failed{finalAnswer ? ` — ${finalAnswer}` : ''}
        </div>
      )}
      {status === 'cancelled' && (
        <div className="banner banner-warning animate-slide-up">⊘ Task cancelled</div>
      )}
      {status === 'reconnecting' && (
        <div className="banner banner-warning animate-slide-up">Connection lost. Reconnecting...</div>
      )}

      <div className="execution-panels">
        <div className="execution-timeline">
          <StepTimeline steps={steps} selectedStep={pinnedStep} onSelectStep={setPinnedStep} />
        </div>
        <div className="execution-screenshot">
          <div className="view-toggle">
            <button
              className={`view-toggle-btn${viewMode === 'screenshot' ? ' active' : ''}`}
              onClick={() => setViewMode('screenshot')}
            >Screenshot</button>
            <button
              className={`view-toggle-btn${viewMode === 'vnc' ? ' active' : ''}`}
              onClick={() => setViewMode('vnc')}
            >Live Desktop</button>
          </div>
          {viewMode === 'screenshot'
            ? <ScreenshotViewer taskId={task.taskId} stepNum={viewStep} />
            : <VncPreview />
          }
        </div>
      </div>

      <div className="devlog">
        <button className="devlog-toggle" onClick={() => setShowLogs(v => !v)}>
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/>
          </svg>
          Dev Logs
          <span className="devlog-count">{logs.length}</span>
          <span className="devlog-chevron">{showLogs ? '▴' : '▾'}</span>
        </button>
        {showLogs && (
          <div className="devlog-body">
            {logs.map((l, i) => (
              <div key={i} className={`devlog-line devlog-${l.level}`}>
                <span className="devlog-ts">{l.ts}</span>
                <span className="devlog-msg">{l.msg}</span>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>
        )}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { model, setModel, availableModels, maxSteps, loading } = useOutletContext()
  const [activeTask, setActiveTask] = useState(null)

  if (loading) {
    return (
      <div className="dashboard-input">
        <div className="task-input surface-card" aria-hidden="true">
          <div className="skeleton" style={{ height: 20, width: '48%' }} />
          <div className="skeleton" style={{ height: 120, width: '100%' }} />
          <div className="skeleton" style={{ height: 34, width: '36%' }} />
        </div>
      </div>
    )
  }

  if (activeTask) {
    return <ExecutionView task={activeTask} onNewTask={() => setActiveTask(null)} />
  }

  return (
    <div className="dashboard-input animate-slide-up">
      <div className="dashboard-hero">
        <h1 className="dashboard-title">DeskPilot</h1>
        <p className="dashboard-subtitle">Describe a task and watch the agent execute it on the desktop.</p>
      </div>
      <TaskInput
        model={model}
        setModel={setModel}
        availableModels={availableModels}
        maxSteps={maxSteps}
        onTaskStarted={(taskId, goal) => setActiveTask({ taskId, goal })}
      />
    </div>
  )
}
